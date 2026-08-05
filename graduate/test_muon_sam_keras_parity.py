"""Stage 3 of the TensorFlow port: KerasMuonSAM must equal muon_sam.MuonSAM.

same shape as test_muon_keras_parity.py -- one model built twice, PyTorch's weights
copied into Keras, identical batches, every weight compared -- but run long enough that
several 2-pass SAM steps fire and the stored LoosSAM correction is actually reused.

Checks, in order:
  1. all three momentum_mode values against the PyTorch reference;
  2. the guradrail from test_muon_sam.py: with rho held at 0, momentum_mode="pre_ns5"
     must reduce to plain KerasMuon. That is the property the whole 2x2 ablation rests
     on -- if it breaks, "MuonSAM beats Muon" stops being a controlled comparison.

Eager on purpose: this pins the algorithm. Graph-mode speed is a separate concern, and
the Python-side branch in should_sam() is what makes it possible at all.
"""
import sys

import numpy as np
import torch
import torch.nn as nn

# torch.optim.Optimizer lazily imports torch._dynamo on first construction, and that
# imports segfaults if TensorFlow is already loaded in the process. Pull it in here,
# before keras/TF, and the two frameworks coexist fine.
import torch._dynamo  # noqa: F401

import keras
import tensorflow as tf
from keras import layers, ops

from muon_sam import MuonSAM
from muon_keras import KerasMuon, split_variables
from muon_sam_keras import KerasMuonSAM

ATOL = 1e-4
STEPS=12
SAM_PERIOD = 3
LR_MUON, LR_AUX, WD = 0.02, 1e-3, 5e-4
RHO_MUON, RHO_AUX = 0.05, 0.01
BN_EPS = 1e-5          # Keras defaults to 1e-3; PyTorch to 1e-5. This changes gradients.

class TorchNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(8, eps=BN_EPS)
        self.hidden = nn.Linear(8, 16, bias=False)
        self.fc = nn.Linear(16, 10)

    def forward(self, x):
        h = torch.relu(self.bn(self.conv(x)))
        h = torch.relu(self.hidden(h.mean(dim=(2, 3))))
        return self.fc(h)

def build_keras_net():
    inp = keras.Input((8, 8, 3))
    x = layers.Conv2D(8, 3, 1, "same", use_bias=False, name="conv")(inp)
    x = layers.BatchNormalization(epsilon=BN_EPS, name="bn")(x)
    x = layers.ReLU()(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(16, use_bias=False, name="hidden")(x)
    x = layers.ReLU()(x)
    out = layers.Dense(10, name="fc")(x)
    return keras.Model(inp, out)

def copy_torch_to_keras(tm, km):
    """PyTorch layouts -> Keras layouts, by layer name (indices shift silently)."""
    sd = tm.state_dict()
    km.get_layer("conv").set_weights([sd["conv.weight"].numpy().transpose(2, 3, 1, 0)])
    km.get_layer("bn").set_weights([sd["bn.weight"].numpy(), sd["bn.bias"].numpy(),
                                    sd["bn.running_mean"].numpy(), sd["bn.running_var"].numpy()])
    km.get_layer("hidden").set_weights([sd["hidden.weight"].numpy().T])
    km.get_layer("fc").set_weights([sd["fc.weight"].numpy().T, sd["fc.bias"].numpy()])

def fresh_torch_net():
    """Same weights every call. Both frameworks must start from identical values, and
    reseeding here rather than at the call sites keeps that independent of how much
    other RNG the caller happens to consume in between."""
    torch.manual_seed(0)
    return TorchNet()

PAIRS = [
    ("conv.weight",     "conv",     0, lambda a: a.transpose(2, 3, 1, 0)),
    ("bn.weight",       "bn",       0, lambda a: a),
    ("bn.bias",         "bn",       1, lambda a: a),
    ("hidden.weight",   "hidden",   0, lambda a: a.T),
    ("fc.weight",       "fc",       0, lambda a: a.T),
    ("fc.bias",         "fc",       1, lambda a: a)
]

def compare(tm, km, label):
    sd = tm.state_dict()
    worst, fails = 0.0, []
    for name, layer, idx, conv in PAIRS:
        t = conv(sd[name].detach().numpy())
        k = ops.convert_to_numpy(km.get_layer(layer).weights[idx])
        d = float(np.abs(t - k).max())
        worst = max(worst, d)
        if d > ATOL:
            fails.append((name, d))
    status = "OK  " if not fails else "FAIL"
    print(f"  {status} {label:34} worst {worst:.2e}" + (f"  {fails}" if fails else ""))
    return not fails

def batches(n):
    rng = np.random.default_rng(1)
    for _ in range(n):
        yield (
            rng.standard_normal((16, 3, 8, 8)).astype(np.float32),
            rng.integers(0, 10, 16).astype(np.int64)
        )

def run_torch(mode, rho_warmup_frac):
    tm = fresh_torch_net()
    muon = [p for n, p in tm.named_parameters() if p.ndim >= 2 and "fc" not in n]
    aux = [p for n, p in tm.named_parameters() if not (p.ndim >= 2 and "fc" not in n)]
    opt = MuonSAM([dict(params=muon, use_muon=True, lr=LR_MUON, rho=RHO_MUON, weight_decay=WD),
                   dict(params=aux, use_muon=False, lr=LR_AUX, rho=RHO_AUX, weight_decay=WD)],
                   total_steps=STEPS, rho_max=RHO_MUON, rho_warmup_frac=rho_warmup_frac,
                   sam_period=SAM_PERIOD, momentum_mode=mode)
    crit = nn.CrossEntropyLoss()
    sam_steps = 0
    for xb, yb in batches(STEPS):
        x, y = torch.from_numpy(xb), torch.from_numpy(yb)

        def closure():
            opt.zero_grad()
            loss = crit(tm(x), y)
            loss.backward()
            return loss

        before = opt._t
        opt.step(closure)
        sam_steps += int(opt._rho_scale() > 0 and (before + 1) % SAM_PERIOD == 0)
    return tm, sam_steps

def run_keras(km, opt):
    """The explicit two-pass loop. This is the reference for what a train_step override
    has to do -- note that the SAM branch is chosen in Python, before any tracing."""
    k_loss = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    tv = km.trainable_variables
    for xb, yb in batches(STEPS):
        xk, yk = tf.constant(xb.transpose(0, 2, 3, 1)), tf.constant(yb)
        opt.begin_step()
        with tf.GradientTape() as tape:
            loss = k_loss(yk, km(xk, training=True))
        grads = tape.gradient(loss, tv)
        if opt.should_sam():
            opt.sam_first_step(grads, tv)
            with tf.GradientTape() as tape2:
                loss2 = k_loss(yk, km(xk, training=True))
            opt.sam_second_step(tape2.gradient(loss2, tv), tv)
        else:
            opt.looksam_update(grads, tv)

def check_mode(mode, rho_warmup_frac=0.0):
    tm, sam_steps = run_torch(mode, rho_warmup_frac)
    km = build_keras_net()
    copy_torch_to_keras(fresh_torch_net(), km)   # tm's starting weights, not its final one
    k_muon, _ = split_variables(km)
    opt = KerasMuonSAM(k_muon, total_steps=STEPS, learning_rate=LR_MUON,
                       aux_learning_rate=LR_AUX, rho_muon=RHO_MUON, rho_aux=RHO_AUX,
                       rho_warmup_frac=rho_warmup_frac, sam_period=SAM_PERIOD,
                       momentum_mode=mode, weight_decay=WD)
    run_keras(km, opt)
    return compare(tm, km, f"momentum_mode={mode!r} ({sam_steps} SAM steps)")

def check_rho_off_reduces_to_muon():
    """MuonSAM with rho pinned to 0 must be plain Muon -- muon_sam.py's core invariant."""
    ref = build_keras_net()
    sam = build_keras_net()
    sam.set_weights(ref.get_weights())
    ref_opt = KerasMuon(split_variables(ref)[0], learning_rate=LR_MUON,
                        aux_learning_rate=LR_AUX, weight_decay=WD)
    # rho_warm_frac=1.0 holds _rho_scale() at 0 for the entire run, so the SAM branch
    # never fires -- the same trick benchmark_cifar10.py uses for muon_nomom.
    sam_opt = KerasMuonSAM(split_variables(sam)[0], total_steps=STEPS,
                           learning_rate=LR_MUON, aux_learning_rate=LR_AUX,
                           rho_warmup_frac=1.0, sam_period=SAM_PERIOD,
                           momentum_mode="pre_ns5", weight_decay=WD)
    k_loss = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    for xb, yb in batches(STEPS):
        xk, yk = tf.constant(xb.transpose(0, 2, 3, 1)), tf.constant(yb)
        with tf.GradientTape() as tape:
            loss = k_loss(yk, ref(xk, training=True))
        ref_opt.apply(tape.gradient(loss, ref.trainable_variables), ref.trainable_variables)
        sam_opt.begin_step()
        with tf.GradientTape() as tape:
            loss = k_loss(yk, sam(xk, training=True))
        assert not sam_opt.should_sam(), "rho is live -- SAM is not off"
        sam_opt.looksam_update(tape.gradient(loss, sam.trainable_variables), sam.trainable_variables)
    worst = max(float(np.abs(ops.convert_to_numpy(a) - ops.convert_to_numpy(b)).max())
                for a, b in zip(ref.weights, sam.weights))
    ok = worst <= ATOL
    print(f"  {'OK  ' if ok else 'FAIL'} rho=0 reduces to KerasMuon         worst {worst:.2e}")
    return ok

def main():
    print(f"KerasMuonSAM vs MuonSAM  |  {STEPS} steps, sam_period={SAM_PERIOD}, atol {ATOL:.0e}")
    ok = all([check_mode("pre_ns5"), check_mode("post_ns5"), check_mode("none"), check_rho_off_reduces_to_muon()])
    print("\nPARITY OK" if ok else "\nFAILED")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())