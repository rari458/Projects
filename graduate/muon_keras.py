"""Keras 3 port of muon.py's SingleDeviceMuonWithAuxAdam.

Mirrors the PyTorch reference exactly: Muon (momentum -> NS5 -> sqrt(fan) scale) for the
variables the caller routes to it, AdamW for everything else, decoupled weight decay on
both. With the same init and the same batches it reproduces the PyTorch optimizer to
float32 noise -- test_muon_keras_parity.py pins that.

Two layout facts drive the adapters below.
    - Keras conv kernels are (kh, kw, C_in, C_out); PyTorch is (C_out, C_in, kh, kw). The
      flattened column ORDER therefore differs, which is harmless: NS5 depends on X X^T,
      so O(GP) = O(G)P for any column permutation P. It only has to be undone consistently.
    - Keras Dense kernels are (in, out); PyTorch Linear is (out, in). This one is NOT
      harmless, because muon_scale() uses max(1, rows/cols) and that is not symmetric --
      a 512->10 head would take 7.16 instead of 1.0. ResNet-18 routes its only Dense to
      the Adam group so the benchmark never hits it, but any model with 2D hidden weights
      would, which is exactly the  "import into existing training code" case.
"""
import keras
from keras import ops

from muon_tf import zeropower_via_newtonschulz5, muon_scale

def to_muon_matrix(g):
    """Keras-layout gradient -> muon.py's 2D matrix with rows = output dim."""
    if len(g.shape) == 4:
        c_out = g.shape[3]
        return ops.reshape(ops.transpose(g, (3, 0, 1, 2)), (c_out, -1))
    if len(g.shape) == 2:
        return ops.swapaxes(g, -1, -2)
    return g

def from_muon_matrix(u, shape):
    """Inverse of to_muon_matrix, for a variable of the given Keras shape."""
    if len(shape) == 4:
        kh, kw, c_in, c_out = shape
        return ops.transpose(ops.reshape(u, (c_out, kh, kw, c_in)), (1, 2, 3, 0))
    if len(shape) == 2:
        return ops.swapaxes(u, -1, -2)
    return u

def split_variables(model, head_layer=None):
    """Muon takes hidden weights with ndim >= 2; the head and all 1D go to Adam.

    Mirrors split_params() in benchmark_cifar10.py. The head is identified by layer
    rather than by a name substring: Keras auto-names layers ("dense", "dense_1", ...),
    so matching on the string breaks as soon as a model has more than one Dense.
    """
    head = set()
    if head_layer is None:
        for layer in reversed(model.layers):
            if layer.trainable_weights:
                head_layer = layer
                break
    if head_layer is not None:
        head = {id(v) for v in head_layer.trainable_weights}
    muon, aux = [], []
    for v in model.trainable_variables:
        (muon if len(v.shape) >= 2 and id(v) not in head else aux).append(v)
    return muon, aux

class KerasMuon(keras.optimizers.Optimizer):
    """Muon + auxiliary AdamW, routed per variable.

    Args:
        muon_variables: the variables Muon owns. Everything else built into this
        optimizer is updated by the internal AdamW.
        learning_rate: Muon lr, in units of spectral norm per update.
        aux_learning_rate: AdamW lr for the non-Muon variables.
    """

    def __init__(self, muon_variables, learning_rate=0.02, aux_learning_rate=1e-3,
                 momentum=0.95, nesterov=True, weight_decay=0.0, ns_steps=5,
                 adam_betas=(0.9, 0.95), adam_eps=1e-10, name="keras_muon", **kwargs):
        # weight_decay is applied by hand below (decoupled, as in muon.py), so the base
        # class must not also apply its own.
        super().__init__(learning_rate=learning_rate, weight_decay=None, name=name, **kwargs)
        self._muon_ids = {id(v) for v in muon_variables}
        self.aux_learning_rate = aux_learning_rate
        self.momentum = momentum
        self.nesterov = nesterov
        self.muon_weight_decay = weight_decay
        self.ns_steps = ns_steps
        self.adam_betas = adam_betas
        self.adam_eps = adam_eps

    def build(self, var_list):
        if self.built:
            return
        super().build(var_list)
        self._is_muon = [id(v) in self._muon_ids for v in var_list]
        # One slot list per role. Unused entries stay None rather than allocating a
        # zero tensor the size of every variable twice over.
        self._momentum_buffers, self._exp_avgs, self._exp_avg_sqs = [], [], []
        for v in var_list:
            if id(v) in self._muon_ids:
                self._momentum_buffers.append(self.add_variable_from_reference(v, "momentum_buffer"))
                self._exp_avgs.append(None)
                self._exp_avg_sqs.append(None)
            else:
                self._momentum_buffers.append(None)
                self._exp_avgs.append(self.add_variable_from_reference(v, "exp_avg"))
                self._exp_avg_sqs.append(self.add_variable_from_reference(v, "exp_avg_sq"))

    def update_step(self, gradient, variable, learning_rate):
        i = self._get_variable_index(variable)
        g = ops.cast(gradient, variable.dtype)
        if self._is_muon[i]:
            self._muon_step(g, variable, i)
        else:
            self._adam_step(g, variable, i)

    def _muon_step(self, g, variable, i):
        """muon_update() from muon.py: momentum on the raw gradient, then NS5."""
        buf = self._momentum_buffers[i]
        # buf.lerp_(grad, 1 - beta)
        self.assign(buf, buf + (1 - self.momentum) * (g - buf))
        # grad.lerp_(momentum, beta) if nesterov else momentum
        update = g + self.momentum * (buf - g) if self.nesterov else buf

        mat = to_muon_matrix(update)
        o = zeropower_via_newtonschulz5(mat, steps=self.ns_steps) * muon_scale(mat)

        lr = ops.cast(self.learning_rate, variable.dtype)
        if self.muon_weight_decay:
            self.assign(variable, variable * (1 - lr * self.muon_weight_decay))
        self.assign_sub(variable, lr * from_muon_matrix(o, variable.shape))

    def _adam_step(self, g, variable, i):
        """adam_update() from muon.py -- note the bias correction divedes, it does not
        use the fused sqrt form, so it must be written the same way to stay in parity."""
        b1, b2 = self.adam_betas
        m, v = self._exp_avgs[i], self._exp_avg_sqs[i]
        self.assign(m, m + (1 - b1) * (g - m))
        self.assign(v, v + (1 - b2) * (ops.square(g) - v))

        t = ops.cast(self.iterations + 1, variable.dtype)
        mc = m / (1 - ops.power(ops.cast(b1, variable.dtype), t))
        vc = v / (1 - ops.power(ops.cast(b2, variable.dtype), t))
        update = mc / (ops.sqrt(vc) + self.adam_eps)

        lr = ops.cast(self.aux_learning_rate, variable.dtype)
        if self.muon_weight_decay:
            self.assign(variable, variable * (1 - lr * self.muon_weight_decay))
        self.assign_sub(variable, lr * update)

    def get_config(self):
        config = super().get_config()
        config.update(dict(aux_learning_rate=self.aux_learning_rate,
                           momentum=self.momentum, nesterov=self.neesterov,
                           weight_decay=self.muon_weight_decay, ns_steps=self.ns_steps,
                           adam_betas=self.adam_betas, adam_eps=self.adam_eps))
        return config