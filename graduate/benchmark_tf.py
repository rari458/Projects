"""CIFAR-10 benchmark for the TensorFlow port -- the mirror of benchmark_cifar10.py.

Same claim, same shape of evidence: convergence speed (train loss per epoch AND wall-clock)
and generalization (test accuracy), with identical weight init and identical batch order
across every optimizer. The runlog is written in the SAME 6-column format the PyTorch harness
uses, so analyze.py reads a TF run with no changes.

Three things differ from benchmark_cifar10.py, all forced:
  1. No `sam` arm. sam.py has no Keras port, and writing one is an optimizer port rather
     than harness work. The 2x2 momentum x SAM ablation is complete without it; the davda54-SAM
     baseline is the piece a TF-vs-PyTorch table has to omit.
  2. Checkpoints are OFF by default (SAVE_CKPT=1 to enable). sharpness.py is PyTorch-only,
     so nothing reads them yet -- writing ~45 MB per arm into /kaggle/working for no
     consumer is not a default worth having.
  3. The muonsam arms are driven by train_tf.make_train_step, not by opt.apply_gradients.
     A Keras optimizer only ever sees gradients someone else computed, so it cannot run
     SAM's second pass; the loop owns both passes. See muon_sam_keras.py.
Model parity with the PyTorch ResNet-18 needs three corrections to Keras defaults, and all
three change gradients rather than raising:
  * BatchNormalization(momentum=0.9): PyTorch's momentum=0.1 is the weight on the New Batch,
    Keras's is the weight on the RUNNING stat. The default 0.99 is a 10x slower running average.
  * BatchNormalization(epsilon=1e-5): Keras defaults to 1e-3.
  * padding: "same" is NOT symmetric at stride 2. For 32x32 input, 3x3 kernel, stride 2,
    TF pads (0 top, 1 bottom) while PyTorch pads 1 on both sides, so the two sample
    different pixels. Stride-2 convs therefore pad explicitly and use "valid".
Conv kernels also use He fan-out normal, matching torchvision's kaiming_normal_; Keras
defaults to glorot_uniform. The Dense head keeps Keras's init -- it is routed to the Adam
group either way, and chasing full init parity is a separate task from the harness.
The CPU QUICK path's test_acc is NOT readable for the momentum arms, and the failure looks
exactily like a brokent optimizer. 3 epochs x 2k samples is 45 steps, which never gives
BatchNormalization's moving averages time to track weights that momentum is still moving
fast: `muon` scored 23.00% under the moving statistics while scoring 44.30% under batch
statistics, and a 30-batch forward-only recalibration lifted it to 44.60%. Nothing was
wrong. Judge a QUICK run by train_loss, or evaluate with training=True; the accuracy
column only becomes meaningful once the schedule is long enough for the EMA to converge.
"""
import os
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")   # must precede the TF import

import keras
import numpy as np
import tensorflow as tf
from keras import layers

from muonsam.keras import KerasMuon, KerasMuonSAM, split_variables
from muonsam.keras.train_tf import make_train_step

# ---------------- config ----------------
DEVICE = "gpu" if tf.config.list_physical_devices("GPU") else "cpu"
# Same trap as the PyTorch harness: a CPU cloud session otherwise writes a 3-epoch log that
# looks valid and is incomparable to every GPU run.
if os.environ.get("REQUIRE_GPU") == "1" and DEVICE != "gpu":
    raise RuntimeError(f"REQUIRE_GPU=1 but TensorFlow reports no GPU (tf {tf.__version__})")
QUICK = (DEVICE == "cpu")
EPOCHS = 3 if QUICK else 50
TRAIN_SUBSET = 2000 if QUICK else None
TEST_SUBSET = 1000 if QUICK else None
BATCH = 128
SEED = 0
LR_ADAMW = 1e-3
LR_MUON = 0.02
LR_AUX = 1e-3
WEIGHT_DECAY = 5e-4
RHO_MAX = 0.05
RHO_AUX = 0.01
KINDS = ["adamw", "muon", "muon_nomom", "muonsam_nomom", "muonsam"]
# Every KerasMuonSAM-backed variant: these need the explicit 3-phase driver, not
# apply_gradients. A kind in KINDS but missing here gets a plain step and silently trains
# without SAM -- add new variants to BOTH.
CLOSURE_KINDS = ("muonsam", "muonsam_nomom", "muon_nomom")
SAVE_CKPT = os.environ.get("SAVE_CKPT", "0") != "0"
JIT = os.environ.get("JIT") == "1"      # XLA; see make_train_step's note before enabling
OUTDIR = os.environ.get("OUTDIR", ".")
os.makedirs(OUTDIR, exist_ok=True)
# Deliberately not runlog.csv: a session that runs both harnesses must not have one
# overwrite the other's log.
LOGFILE = os.path.join(OUTDIR, "runlog_tf.csv")

BN = dict(momentum=0.9, epsilon=1e-5)
CONV_INIT = keras.initializers.VarianceScaling(scale=2.0, mode="fan_out", distribution="untruncated_normal")

# ---------------- model ----------------
def conv(x, filters, k, stride):
    """3x3/1x1 conv with PyTorch's padding, not Keras's.
    "same" agrees with PyTorch for odd kernels at stride 1, and for 1x1 at any stride, but
    not for 3x3 at stride 2 -- see the module docstring.
    """
    if stride > 1 and k > 1:
        x = layers.ZeroPadding2D(k // 2)(x)
        pad = "valid"
    else:
        pad = "same"
    return layers.Conv2D(filters, k, strides=stride, padding=pad, use_bias=False,
                         kernel_initializer=CONV_INIT)(x)
    
def basic_block(x, filters, stride):
    """torchvision BasicBlock: conv-bn-relu-conv-bn, + projected shortcut, then relu."""
    shortcut = x
    y = layers.ReLU()(layers.BatchNormalization(**BN)(conv(x, filters, 3, stride)))
    y = layers.BatchNormalization(**BN)(conv(y, filters, 3, 1))
    if stride != 1 or x.shape[-1] != filters:
        shortcut = layers.BatchNormalization(**BN)(conv(x, filters, 1, stride))
    return layers.ReLU()(layers.Add()([y, shortcut]))

def make_resnet18():
    """The CIFAR adaptation make_resnet18() builds in the PyTorch harness: 3x3 stem,
    stride 1, no maxpool, then [2,2,2,2] BasicBlocks at 64/128/256/512."""
    inp = keras.Input((32, 32, 3))
    x = layers.ReLU()(layers.BatchNormalization(**BN)(conv(inp, 64, 3, 1)))
    for filters, stride in ((64, 1), (128, 2), (256, 2), (512, 2)):
        x = basic_block(x, filters, stride)
        x = basic_block(x, filters, 1)
    x = layers.GlobalAveragePooling2D()(x)
    return keras.Model(inp, layers.Dense(10, name="head")(x), name="cifar_resnet18")

# ---------------- data ----------------
def get_data():
    mean = np.array([0.4914, 0.4822, 0.4465], "float32")
    std = np.array([0.2470, 0.2435, 0.2616], "float32")
    (xtr, ytr), (xte, yte) = keras.datasets.cifar10.load_data()
    if TRAIN_SUBSET:
        xtr, ytr = xtr[:TRAIN_SUBSET], ytr[:TRAIN_SUBSET]
    if TEST_SUBSET:
        xte, yte = xte[:TEST_SUBSET], yte[:TEST_SUBSET]
    norm = lambda a: (a.astype("float32") / 255.0 - mean) / std
    return (
        norm(xtr), ytr.squeeze(-1).astype("int32"),
        norm(xte), yte.squeeze(-1).astype("int32")
    )
    
def _augment(i, xy):
    """RandomCrop(32, padding=4) + RandomHorizontalFlip, keyed by global step index.
    Stateless ops rather than tf.image.random_*: the fairness claim needs every arm to see
    the same augmentations in the same order, and a stateful op depends on how many other
    ops have drawn from the global generator. `i` counts run (the datasetrepeats before enumerate), 
    so no two epochs share a draw.
    """
    x, y = xy
    i = tf.cast(i, tf.int32)
    x = tf.image.stateless_random_flip_left_right(x, tf.stack([i, SEED]))
    x = tf.pad(x, [[4, 4], [4, 4], [0, 0]])          # zero fill, as torchvision defaults
    x = tf.image.stateless_random_crop(x, (32, 32, 3), tf.stack([i, SEED + 1]))
    return x, y

def make_train_ds(x, y):
    """Rebuilt per arm. Every source of order here is explicitly seeded, so arm N sees
    byte-identical batches to arm 1 -- the TF half of "identical batch order"."""
    ds = tf.data.Dataset.from_tensor_slices((x, y))
    ds = ds.shuffle(len(x), seed=SEED, reshuffle_each_iteration=True).repeat()
    ds = ds.enumerate().map(_augment, num_parallel_calls=tf.data.AUTOTUNE)
    return ds.batch(BATCH, drop_remainder=True).prefetch(tf.data.AUTOTUNE)

# ---------------- optimizers ----------------
def primary_lr(kind):
    """The LR that identifies an arm in the runlog; mirrors benchmark_cifar10.primary_lr."""
    return LR_ADAMW if kind == "adamw" else LR_MUON

def build_optimizer(kind, model, total_steps):
    muon_vars, _ = split_variables(model)
    if kind == "adamw":
        return keras.optimizers.AdamW(learning_rate=LR_ADAMW, weight_decay=WEIGHT_DECAY)
    if kind == "muon":
        return KerasMuon(muon_vars, learning_rate=LR_MUON, aux_learning_rate=LR_AUX, weight_decay=WEIGHT_DECAY)
    if kind == "muon_nomom":
        # Fourth cell of the momentum x SAM ablation. rho_warmup_frac=1.0 holds the rho
        # schedule at 0 for the whole run, so the SAM branch never fires and no correction
        # is ever stored; with momentum_mode="none" that is Muon minus its momentum buffer.
        return KerasMuonSAM(muon_vars, total_steps=total_steps, learning_rate=LR_MUON,
                            aux_learning_rate=LR_AUX, rho_muon=0.0, rho_aux=0.0,
                            rho_warmup_frac=1.0, momentum_mode="none", weight_decay=WEIGHT_DECAY)
    if kind.startswith("muonsam"):
        mode = "none" if kind.endswith("_nomom") else "pre_ns5"
        return KerasMuonSAM(muon_vars, total_steps=total_steps, learning_rate=LR_MUON,
                            aux_learning_rate=LR_AUX, rho_muon=RHO_MAX, rho_aux=RHO_AUX,
                            rho_warmup_frac=0.3, sam_period=5, momentum_mode=mode, weight_decay=WEIGHT_DECAY)
    raise ValueError(kind)

# ---------------- train / eval ----------------
def make_step(kind, model, loss_fn, opt):
    if kind in CLOSURE_KINDS:
        return make_train_step(model, loss_fn, opt, jit_compile=JIT)
    tv = model.trainable_variables
    
    @tf.function(reduce_retracing=True, jit_compile=JIT)
    def step(x, y):
        with tf.GradientTape() as tape:
            loss = loss_fn(y, model(x, training=True))
        opt.apply_gradients(zip(tape.gradient(loss, tv), tv))
        return loss
    
    return step

def make_eval(model):
    @tf.function(reduce_retracing=True)
    def batch_correct(x, y):
        pred = tf.argmax(model(x, training=False), axis=-1, output_type=tf.int32)
        return tf.reduce_sum(tf.cast(pred == y, tf.int32))
    
    def evaluate(ds):
        correct = n = 0
        for x, y in ds:
            correct += int(batch_correct(x, y))
            n += int(x.shape[0])
        return correct / n
    
    return evaluate

def maybe_plot(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for kind, hist in results.items():
        axes[0].plot([h[0] for h in hist], [h[2] * 100 for h in hist], marker="o", label=kind)
        axes[1].plot([h[3] for h in hist], [h[2] * 100 for h in hist], marker="o", label=kind)
    axes[0].set(xlabel="epoch", ylabel="test acc (%)", title="acc vs epoch")
    axes[1].set(xlabel="wall-clock (s)", ylabel="test acc (%)", title="acc vs compute budget")
    for ax in axes:
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    png = os.path.join(OUTDIR, "benchmark_tf.png")
    fig.savefig(png, dpi=120)
    print(f"saved {png}")
    
def main():
    print(f"device={DEVICE} | QUICK={QUICK} | epochs={EPOCHS} "
          f"| train_subset={TRAIN_SUBSET} | test_subset={TEST_SUBSET} "
          f"| keras {keras.__version__} | tf {tf.__version__}")
    xtr, ytr, xte, yte = get_data()
    steps_per_epoch = len(xtr) // BATCH
    total_steps = steps_per_epoch * EPOCHS
    test_ds = tf.data.Dataset.from_tensor_slices((xte, yte)).batch(BATCH).prefetch(tf.data.AUTOTUNE)
    loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    
    log = open(LOGFILE, "w", newline="")
    log.write("optimizer,epoch,train_loss,test_acc,time_s,lr\n")
    
    results = {}
    for kind in KINDS:
        keras.utils.set_random_seed(SEED)        # identical weight init
        model = make_resnet18()
        opt = build_optimizer(kind, model, total_steps)
        step = make_step(kind, model, loss_fn, opt)
        evaluate = make_eval(model)
        batches = iter(make_train_ds(xtr, ytr))  # identical batch order
        lr = primary_lr(kind)
        print(f"\n=== {kind} (lr={lr}) ===")
        hist, t0 = [], time.time()
        for ep in range(1, EPOCHS + 1):
            # drop_remainder=True makes every batch the same size, so an unweighted mean
            # equals the PyTorch harness's per-sample weighting.
            total = sum(float(step(*next(batches))) for _ in range(steps_per_epoch))
            tr = total / steps_per_epoch
            acc = evaluate(test_ds)
            elapsed = time.time() - t0
            hist.append((ep, tr, acc, elapsed))
            print(f"  epoch {ep}: train_loss={tr:.4f} test_acc={acc * 100:.2f}% time={elapsed:.1f}s")
            log.write(f"{kind},{ep},{tr:.4f},{acc * 100:.2f},{elapsed:.1f},{lr}\n")
            log.flush()
        results[kind] = hist
        if SAVE_CKPT:
            ckpt = os.path.join(OUTDIR, f"ckpt_tf_{kind}_seed{SEED}.weights.h5")
            model.save_weights(ckpt)
            print(f"  saved {ckpt}")
        if DEVICE == "gpu":
            peak = tf.config.experimental.get_memory_info("GPU:0")["peak"]
            print(f"  peak GPU mem: {peak / 1024 ** 2:.0f} MB")
            tf.config.experimental.reset_memory_stats("GPU:0")

    log.close()
    print(f"\n saved {LOGFILE}")
    
    print("\n==== final summary ====")
    print(f"{'optimizer':<16}{'test_acc':>10}{'time(s)':>10}")
    for kind, hist in results.items():
        _, _, acc, t = hist[-1]
        print(f"{kind:<16}{acc * 100:>9.2f}%{t:>10.1f}")
    maybe_plot(results)
    
if __name__ == "__main__":
    main()