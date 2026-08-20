"""Graph-mode driver for KerasMuonSAM (TensorFlow backend).

The phases in muon_sam_keras.py are correct but slow when called from an eager Python
loop: every NS5 iteration round-trips through the interpreter. tf.function fixes that,
but only if the LookSAM branch stays OUTSIDE the traced region -- a `t % sam_period == 0`
test inside a traced function is evaluated once and frozen, which silently disables
LookSAM's periodicity. Hence two separately compiled step functions and a Python
dispatcher that picks between them.

This module is TensorFlow-specific on purpose. muon_tf.py / muon_keras.py /
muon_sam_keras.py are written against keras.ops and run on any Keras backend; tf.function
has no backend-agnostic equivalent, so the compilation strategy lives here.
"""
import tensorflow as tf

def make_train_step(model, loss_fn, optimizer, jit_compile=False):
    """Compile KerasMuonSAM's two paths and return a plain train_step(x, y) -> loss.

    Total traces for a whole run: one for the 2-pass path, two for the 1-pass path (once
    before any LookSAM correction exists, once after). Nothing retraces per step, which
    is the entire point of keeping the step counter split -- see KerasMuonSAM.

    Args:
        jit_compile: hand the steps to XLA as well. Off by default, but not because it is
            slower -- two runs on this CPU disagreed on the sign (graph 6.42x / XLA 5.79x,
            then graph 5.29x / XLA 7.04x), so the difference is inside the run-to-run
            noise here and no winner is measurable. It stays off because it pays a long
            compile for NS5's fixed-iteration matmul chain and is the first thing to blame
            if a benchmark behaves oddly. Measure it on the T4 before a real run; that is
            where it may actually matter.
    """
    tv = model.trainable_variables
    # Build eagerly. tf.function allows variable creation only on the first trace, so the
    # optimizer's slots would otherwise be created inside whichever path happened to run
    # first -- and the other path would then trace against variables it did not create.
    if not optimizer.built:
        optimizer.build(tv)

    @tf.function(reduce_retracing=True, jit_compile=jit_compile)
    def sam_step(x, y):
        """The 1-in-sam_period full 2-pass SAM step. Returns the loss at w, not at w+e,
        matching what MuonSAM.step(closure) returns in PyTorch."""
        with tf.GradientTape() as tape:
            loss = loss_fn(y, model(x, training=True))
        optimizer.sam_first_step(tape.gradient(loss, tv), tv)
        with tf.GradientTape() as tape:
            perturbed = loss_fn(y, model(x, training=True))
        optimizer.sam_second_step(tape.gradient(perturbed, tv), tv)
        return loss

    @tf.function(reduce_retracing=True, jit_compile=jit_compile)
    def look_step(x, y, use_correction):
        """The 1-pass step. use_correction is a Python bool, so tf.function traces it once
        per value rather than baking in whatever it was the first time round."""
        with tf.GradientTape() as tape:
            loss = loss_fn(y, model(x, training=True))
        optimizer.looksam_update(tape.gradient(loss, tv), tv, use_correction=use_correction)
        return loss

    def train_step(x, y):
        optimizer.begin_step()
        if optimizer.should_sam():
            # sam_second_step flips optimizer._uv_ready, and it does so at trace time --
            # which is the same moment as the first real execution, so the flag is set
            # exactly when the first correction actually lands.
            return sam_step(x, y)
        return look_step(x, y, optimizer.uv_ready)

    return train_step