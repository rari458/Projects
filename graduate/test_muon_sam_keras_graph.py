"""Stage 3b: the compiled driver must compute the same step as the eager loop.

test_muon_sam_keras_parity.py pins the algorithm against PyTorch; this pins the
compilation strategy against that algorithm. The failure it is really hunting is the
frozen branch -- if `t % sam_period == 0` ever migrates inside a traced function, every
step takes the same path, nothing raises, and the training log still looks healthy.

Why it re-syncs state every step: NS5 is ill-conditioned in its small-singular-value
subspace. Where a gradient matrix is near-rank-deficient the output directions are
essentially arbitrary, so an O(1e-8) difference -- which is all that separates eager from
graph, since oneDNN fuses and reorders float32 ops -- is amplified by roughly 10x per
step. Free-running trajectories therefore separate no matter how correct both are; the
run_free() figure below measures exactly that, and it is the same mechanism behind the
0.077pp same-config rerun noise floor. Comparing ONE step from identical state is the
question that actually has a right answer.
"""
import sys
import time

import numpy as np
import keras
import tensorflow as tf
from keras import layers, ops

from muon_keras import split_variables
from muon_sam_keras import KerasMuonSAM
from train_tf import make_train_step

# Pass criterion is relative to the size of the step itself: "the two implementations
# agree to within RTOL of one step's worth of weight change". An absolute tolerance is
# the wrong instrument here, because a single NS5 call on a near-rank-deficient 64x576
# gradient is float32-sensitive at the 1e-5 level regardless of who is right. The real
# bugs this catches are not subtle -- the g/d mix-up found in sam_second_step showed up
# as a free-running drift of 7e-2, four orders of magnitude above this floor.
RTOL = 1e-2
STEPS = 24
SAM_PERIOD = 5
LR_MUON, LR_AUX, WD = 0.02, 1e-3, 5e-4
BN_EPS = 1e-5

def build_net(seed):
    """Wide enough that NS5 dominates the step, so the timing below means something."""
    init = keras.initializers.GlorotUniform(seed=seed)
    inp = keras.Input((16, 16, 3))
    x = inp
    for i, ch in enumerate((32, 64, 64)):
        x = layers.Conv2D(ch, 3, 1, "same", use_bias=False, kernel_initializer=init, name=f"conv{i}")(x)
        x = layers.BatchNormalization(epsilon=BN_EPS, name=f"bn{i}")(x)
        x = layers.ReLU()(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, use_bias=False, kernel_initializer=init, name="hidden")(x)
    x = layers.ReLU()(x)
    out = layers.Dense(10, kernel_initializer=init, name="fc")(x)
    return keras.Model(inp, out)

def make_opt(model, mode):
    opt = KerasMuonSAM(split_variables(model)[0], total_steps=STEPS,
                       learning_rate=LR_MUON, aux_learning_rate=LR_AUX,
                       rho_warmup_frac=0.0, sam_period=SAM_PERIOD,
                       momentum_mode=mode, weight_decay=WD)
    opt.build(model.trainable_variables)
    return opt

def batches(n):
    rng = np.random.default_rng(7)
    for _ in range(n):
        yield(tf.constant(rng.standard_normal((32, 16, 16, 3)).astype(np.float32)),
              tf.constant(rng.integers(0, 10, 32).astype(np.int64)))

def snapshot(model, opt):
    """Everything that carries state across a step, including the two Python-side fields
    that drive branch selection."""
    return (
        [ops.convert_to_numpy(w) for w in model.weights],
        [ops.convert_to_numpy(v) for v in opt.variables],
        opt._t, opt._uv_ready
    )

def restore(model, opt, snap):
    weights, opt_vars, t, uv_ready = snap
    for w, a in zip(model.weights, weights):
        w.assign(a)
    for v, a in zip(opt.variables, opt_vars):
        v.assign(a)
    opt._t, opt._uv_ready = t, uv_ready

def diff(a_model, b_model):
    return max(
        float(np.abs(ops.convert_to_numpy(a) - ops.convert_to_numpy(b)).max())
        for a, b in zip(a_model.weights, b_model.weights)
    )

def step_size(model, pre_weights):
    """How much this step moved the weights -- the scale the disagreement is judged against."""
    return max(
        float(np.abs(ops.convert_to_numpy(w) - a).max())
        for w, a in zip(model.weights, pre_weights)
    )

def eager_step(model, opt, loss_fn, x, y):
    """The reference loop from test_muon_sam_keras_parity.py, one step of it."""
    tv = model.trainable_variables
    opt.begin_step()
    with tf.GradientTape() as tape:
        loss = loss_fn(y, model(x, training=True))
    grads = tape.gradient(loss, tv)
    if opt.should_sam():
        opt.sam_first_step(grads, tv)
        with tf.GradientTape() as tape:
            perturbed = loss_fn(y, model(x, training=True))
        opt.sam_second_step(tape.gradient(perturbed, tv), tv)
    else:
        opt.looksam_update(grads, tv)
    return loss

def check(mode):
    """One compiled step must equal one eager step, from identical state, every step."""
    loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    eager, graph = build_net(0), build_net(0)
    graph.set_weights(eager.get_weights())
    oe, og = make_opt(eager, mode), make_opt(graph, mode)
    step_graph = make_train_step(graph, loss_fn, og)

    worst_rel, worst_abs, worst_at = 0.0, 0.0, 0
    for i, (x, y) in enumerate(batches(STEPS), 1):
        snap = snapshot(eager, oe)          # the pre-step state, before eager consumes it
        eager_step(eager, oe, loss_fn, x, y)
        restore(graph, og, snap)            # put graph on that same pre-step state
        step_graph(x, y)
        d = diff(eager, graph)
        rel = d / (step_size(eager, snap[0]) + 1e-30)
        if rel > worst_rel:
            worst_rel, worst_abs, worst_at = rel, d, i
    ok = worst_rel <= RTOL
    print(f"  {'OK  ' if ok else 'FAIL'} {mode:9} per-step worst {worst_rel:.2e} of a step"
          f"  (abs {worst_abs:.2e}, step {worst_at})")
    return ok

def run_free(mode):
    """No re-syncing: how far two mathematically identical runs drift apart on their own.
    Informational -- this is a property of NS5, not of the port, and it is the mechanism
    behind the same-config rerun noise floor."""
    loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    eager, graph = build_net(0), build_net(0)
    graph.set_weights(eager.get_weights())
    oe, og = make_opt(eager, mode), make_opt(graph, mode)
    step_graph = make_train_step(graph, loss_fn, og)
    for x, y in batches(STEPS):
        eager_step(eager, oe, loss_fn, x, y)
    for x, y in batches(STEPS):
        step_graph(x, y)
    print(f"       {mode:9} free-running drift {diff(eager, graph):.2e} after {STEPS} steps")

def report_speed(steps=40, warmup=6):
    """Why this module exists. Timed separately from the checks above, and after a warm-up,
    because tracing is a one-off cost that swamps a short run -- measured over 24 cold
    steps tf.function looks like a 1.0x wash, which is purely an artefact of counting the trace.
    """
    loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    
    def timed(label, make_runner):
        model = build_net(0)
        run = make_runner(model, make_opt(model, "pre_ns5"))
        for x, y in batches(warmup):
            run(x, y)
        t0 = time.time()
        for x, y in batches(steps):
            run(x, y)
        dt = time.time() - t0
        print(f"       {label:20} {dt / steps * 1000:6.1f} ms/step")
        return dt

    e = timed("eager", lambda m, o: lambda x, y: eager_step(m, o, loss_fn, x, y))
    g = timed("tf.function", lambda m, o: make_train_step(m, loss_fn, o))
    j = timed("tf.function + XLA", lambda m, o: make_train_step(m, loss_fn, o, jit_compile=True))
    print(f"       -> graph {e / g:.2f}x over eager, XLA {e / j:.2f}x")

def check_branch_actually_alternates():
    """Guard the one bug this whole design exists to prevent. A frozen branch still
    trains and still looks healthy in a log; only the step counts give it away."""
    model = build_net(0)
    opt = make_opt(model, "pre_ns5")
    loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    step = make_train_step(model, loss_fn, opt)
    sam = 0
    for x, y in batches(STEPS):
        before = opt._t
        step(x, y)
        sam += (before + 1) % SAM_PERIOD == 0
    want = STEPS // SAM_PERIOD
    ok = sam == want
    print(f"  {'OK  ' if ok else 'FAIL'} branch     {sam} SAM / {STEPS - sam} LookSAM steps"
          f"   (expected {want} / {STEPS - want})")
    return ok

def main():
    print(f"graph vs eager  |  {STEPS} steps, sam_period={SAM_PERIOD}, rtol {RTOL:.0e} of one step")
    ok = all([check("pre_ns5"), check("post_ns5"), check("none"),
              check_branch_actually_alternates()])
    print()
    for mode in ("pre_ns5", "post_ns5", "none"):
        run_free(mode)
    print()
    report_speed()
    print("\nGRAPH PARITY OK" if ok else "\nFAILED")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())