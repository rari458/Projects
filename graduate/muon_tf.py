"""Muon primitives on Keras 3 ops -- the TensorFlow port of muon.py.

Written against keras.ops rather than tf.* so the same code runs on the TensorFlow,
JAX, and PyTorch backends. The proposal asks for a TensorFlow port; KERAS_BACKEND
=tensorflow delivers that, and the others come free.

Layout note: Keras stores conv kernels as (kh, kw, C_in, C_out) and Dense kernels as
(in, out), both transposed relative to PyTorch. Callers must hand this module matrices
already in PyTorch orientation -- see to_muon_matrix() in the optimizer. The scale
factor below is orientation-dependent, so getting that wrong changes the update by a
large constant rather than failing loudly.
"""
from keras import ops

def zeropower_via_newtonschulz5(G, steps: int = 5):
    """Newton-Schulz quintic orthogonalization. Mirrors muon.py line for line.

    G must be at least 2D and already in PyTorch orientation (rows = output dim).
    Returns a matrix of the same shape, approximately U V^T.
    """
    a, b, c = (3.4445, -4.7750, 2.0315)
    # muon.py uses bfloat16 on CUDA and fp32 on CPU for the same reason (no bf16
    # hardware on this machine); keras.ops has no device predicate, so the caller
    # picks the dtype and this function honours it.
    X = G
    transposed = X.shape[-2] > X.shape[-1]
    if transposed:
        X = ops.swapaxes(X, -1, -2)

    # Ensure spectral norm is at most 1
    X = X / (ops.norm(X, axis=(-2, -1), keepdims=True) + 1e-7)
    for _ in range(steps):
        A = ops.matmul(X, ops.swapaxes(X, -1, -2))
        B = b * A + c * ops.matmul(A, A)
        X = a * X + ops.matmul(B, X)

    if transposed:
        X = ops.swapaxes(X, -1, -2)
    return X

def muon_scale(update):
    """The sqrt(fan) factor from muon_update(). Orientation-dependent on purpose:
    max(1, rows/cols) is not max(1, cols/rows), so a transposed Keras kernel would
    get a wildly different factor (e.g. 1.0 vs 7.16 for a 512->10 head)."""
    return max(1.0, update.shape[-2] / update.shape[-1]) ** 0.5