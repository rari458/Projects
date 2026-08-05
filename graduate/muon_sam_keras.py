"""Keras 3 port of muon_sam.py -- MuonSAM, the project's novel contribution.

The algorithm is unchanged from the PyTorch reference: a spectral SAM perturbation
e = rho * O(g), a LookSAM correction refreshed every sam_period steps and reused in
between, and a dynamic rho schedule. What changes is who drives it.

A Keras optimizer only ever sees gradients somebody else already computed
(update_step(gradient, variable, ...)), so it cannot run SAM's second forward-backward
pass by itself. PyTorch's MuonSAM.step(closure) owns both passes; here the training loop
owns them and calls these three phases explicitly:

    sam_first_step(grads, vars)   perturb w -> w+e, stash u/g and e   (2-pass step, 1/2)
    sam_second_step(grads, vars)  restore w, update, refresh u_v/g_v  (2-pass step, 2/2)
    looksam_update(grads, vars)   1-pass update reusing the correction

WHICH phase runs is decided in Python, by should_sam(), and that is not a style choice.
Keras traces train_step into a tf.function (backend/tensorflow/trainer.py), so a
`t % sam_period == 0` test written inside the traces region is evaluated once and frozen
-- LookSAM's periodicity would silently disappear while training still looked healthy.
Keeping the branch in Python and letting the caller compile the two paths separately is
what keeps it both correct and fast.

The step counter is deliberately split for the same reason:
  * self._t, a Python int, drives branch selection only.
  * self._step, a variable, drives the rho schedule and Adam bias correction. Those
    change every step, so reading them from Python would retrace the graph every step.
"""
import keras
from keras import ops

from muon_tf import zeropower_via_newtonschulz5, muon_scale
from muon_keras import to_muon_matrix, from_muon_matrix

def muon_matrix_shape(shape):
    """Shape that to_muon_matrix() produces for a variable of this Keras shape.

    Needed because u_v and the post_ns5 momentum buffer live in the orthogonalized 2D
    space, not in the variable's own shape -- for conv they are not even the same rank.
    """
    if len(shape) == 4:
        kh, kw, c_in, c_out = shape
        return (c_out, kh * kw * c_in)
    if len(shape) == 2:
        return (shape[1], shape[0])
    return tuple(shape)

class KerasMuonSAM(keras.optimizers.Optimizer):
    """MuonSAM: Muon + LookSAM-periodic SAM in Muon's spectral geometry.

    Args mirror muon_sam.py. The per-group rho of the PyTorch version becomes
    rho_muon / rho_aux here, since Keras optimizers have no param_groups.

    Args:
        muon_variables: variables Muon owns; everything else goes to the internal AdamW.
        total_steps: drives the rho schedule. Required, as in the PyTorch version -- the
                     schedule follows this optimizer's own counter, not the LR scheduler.
        momentum_mode: "pre_ns5" | "post_ns5" | "none", the config axis from muon_sam.py.
                       With rho=0, "pre_ns5" reduces to plain Muon exactly.
    """

    def __init__(self, muon_variables, total_steps,
                 learning_rate=0.02, aux_learning_rate=1e-3,
                 rho_muon=0.05, rho_aux=0.01, rho_warmup_frac=0.0,
                 sam_period=5, ns_steps=5, looksam_alpha=0.7, reorthogonalize=True,
                 momentum_mode="pre_ns5", momentum=0.95, nesterov=True, adaptive=False,
                 weight_decay=0.0, adam_betas=(0.9, 0.95), adam_eps=1e-10,
                 name="keras_muon_sam", **kwargs):
        assert momentum_mode in ("none", "pre_ns5", "post_ns5"), momentum_mode
        # Decoupled weight decay is applied by hand below, exactly as muon_sam.py does it,
        # so the base class must not also apply its own.
        super().__init__(learning_rate=learning_rate, weight_decay=None, name=name, **kwargs)
        self._muon_ids = {id(v) for v in muon_variables}
        self.total_steps = total_steps
        self.aux_learning_rate = aux_learning_rate
        self.rho_muon = rho_muon
        self.rho_aux = rho_aux
        self.rho_warmup_frac = rho_warmup_frac
        self.sam_period = sam_period
        self.ns_steps = ns_steps
        self.alpha = looksam_alpha
        self.reorthogonalize = reorthogonalize
        self.momentum_mode = momentum_mode
        self.momentum = momentum
        self.nesterov = nesterov
        self.adaptive = adaptive
        self.muon_weight_decay = weight_decay
        self.adam_betas = adam_betas
        self.adam_eps = adam_eps
        self._t = 0             # Python-side counter; branch selection only
        self._uv_ready = False  # no correction stored yet -> warmup behaves as plain Muon

    # ---------- setup ----------
    def build(self, var_list):
        if self.built:
            return
        super().build(var_list)
        self._is_muon = [id(v) in self._muon_ids for v in var_list]
        self._step = self.add_variable(shape=(), initializer="zeros", dtype="float32",
                                       name="muonsam_step")
        # One slot list per role; unused entries stay None instead of allocating a
        # zero tensor the size of every variable several time over.
        self._eps = []                       # the SAM perturbation, undone in phase 2
        self._mom, self._dir, self._uv, self._u0 = [], [], [], []
        self._m, self._v, self._gv, self._g0 = [], [], [], []
        for i, v in enumerate(var_list):
            self._eps.append(self.add_variable_from_reference(v, "sam_eps"))
            if self._is_muon[i]:
                mshape = muon_matrix_shape(v.shape)
                self._mom.append(self.add_variable_from_reference(v, "momentum_buffer")
                                 if self.momentum_mode == "pre_ns5" else None)
                self._dir.append(self.add_variable(shape=mshape, dtype=v.dtype, name=f"dir_buffer_{i}")
                                 if self.momentum_mode == "post_ns5" else None)
                self._uv.append(self.add_variable(shape=mshape, dtype=v.dtype, name=f"u_v_{i}"))
                self._u0.append(self.add_variable(shape=mshape, dtype=v.dtype, name=f"u_vanilla_{i}"))
                self._m.append(None)
                self._v.append(None)
                self._gv.append(None)
                self._g0.append(None)
            else:
                self._mom.append(None)
                self._dir.append(None)
                self._uv.append(None)
                self._u0.append(None)
                self._m.append(self.add_variable_from_reference(v, "exp_avg"))
                self._v.append(self.add_variable_from_reference(v, "exp_avg_sq"))
                self._gv.append(self.add_variable_from_reference(v, "g_v"))
                self._g0.append(self.add_variable_from_reference(v, "g_vanilla"))

    def _ensure_built(self, variables):
        if not self.built:
            self.build(list(variables))

    def update_step(self, gradient, variable, learning_rate):
        raise NotImplementedError(
            "KerasMuonSAM is driven by sam_first_step/sam_second_step/looksam_update, "
            "not by apply(). SAM needs two forward-backward passes, which update_step "
            "cannot request. Use an explicit training loop or a train_step override."
        )

    # ---------- schedule ----------
    def _rho_scale(self):
        """Tensor version of muonsam.py's _rho_scale(): 0 until rho_warmup_frac of
        training, then a linear ramp to 1. Clipping reproduces the two-branch original
        because frac < rho_warmup_frac makes the ratio negative."""
        frac = self._step / float(max(1, self.total_steps))
        span = max(1e-8, 1.0 - self.rho_warmup_frac)
        return ops.clip((frac - self.rho_warmup_frac) / span, 0.0, 1.0)

    def _rho_scale_py(self):
        """The same value from the Python counter, for branch selection only."""
        frac =self._t / max(1, self.total_steps)
        if frac < self.rho_warmup_frac:
            return 0.0
        span = 1.0 - self.rho_warmup_frac
        return min(1.0, (frac - self.rho_warmup_frac) / max(1e-8, span))

    def should_sam(self):
        """True on the steps that run a full 2-pass SAM. Call AFTER begin_step()."""
        return self._rho_scale_py() > 0.0 and self._t % self.sam_period == 0

    def begin_step(self):
        """Advance the Python counter. The caller must call this once per training step,
        before should_sam(); the variable counter advances inside the phases."""
        self._t += 1

    @property
    def uv_ready(self):
        """Whether a LookSAM correction has ever been stored. Pass this to a traces
        1-pass step as a Python argument so it traces once per value, rather than
        reading it inside the graph where it would be frozen at the first trace."""
        return self._uv_ready

    # ---------- primitives ----------
    def _ortho(self, mat):
        """O(.) = NS5 + sqrt(fan) scaling, on an already-2D matrix. NS5 normalizes the
        spectral norm internally, so re-orthogonalizing an already-scaled matrix does not
        double-apply the scale."""
        return zeropower_via_newtonschulz5(mat, steps=self.ns_steps) * muon_scale(mat)

    def _muon_grad(self, i, g):
        """momentum_mode='pre_ns5': smooth the raw gradient before orthogonalizing.
        Mirrors muon_update(), which is what makes the rho=0 case reduce to plain Muon.
        Advances the buffer, so it must be called exactly once per step."""
        if self.momentum_mode != "pre_ns5":
            return g
        buf = self._mom[i]
        self.assign(buf, buf + (1 - self.momentum) * (g - buf))
        return g + self.momentum * (buf - g) if self.nesterov else buf

    def _muon_dir(self, i, d):
        """momentum_mode='post_ns5': smooth the orthogonalized direction instead."""
        if self.momentum_mode != "post_ns5":
            return d
        buf = self._dir[i]
        self.assign(buf, buf + (1 - self.momentum) * (d - buf))
        return self._ortho(buf) if self.reorthogonalize else buf

    def _apply_muon(self, v, i, d2):
        lr = ops.cast(self.learning_rate, v.dtype)
        if self.muon_weight_decay:
            self.assign(v, v * (1 - lr * self.muon_weight_decay))
        self.assign_sub(v, lr * from_muon_matrix(d2, v.shape))

    def _apply_adam(self, v, i, g):
        b1, b2 = self.adam_betas
        m, s = self._m[i], self._v[i]
        self.assign(m, m + (1 - b1) * (g - m))
        self.assign(s, s + (1 - b2) * (ops.square(g) - s))
        t = ops.cast(self._step, v.dtype)
        mc = m / (1 - ops.power(ops.cast(b1, v.dtype), t))
        vc = s / (1 - ops.power(ops.cast(b2, v.dtype), t))
        lr = ops.cast(self.aux_learning_rate, v.dtype)
        if self.muon_weight_decay:
            self.assign(v, v * (1 - lr * self.muon_weight_decay))
        self.assign_sub(v, lr * (mc / (ops.sqrt(vc) + self.adam_eps)))

    def _aux_grad_norm(self, grads, variables):
        parts = [
            ops.norm((ops.abs(v) if self.adaptive else 1.0) * g)
            for g, v, m in zip(grads, variables, self._is_muon) if not m
        ]
        return ops.norm(ops.stack(parts))

    # ---------- phase 1 of a 2-pass step ----------
    def sam_first_step(self, grads, variables):
        """Perturb w -> w+e along the clean gradient and stash what phase 2 needs.

        The perturbation follows the *current* gradient, not the momentum average, and
        this exploratory pass deliverately leaves every momrntum buffer untouched.
        """
        self._ensure_built(variables)
        self.assign_add(self._step, 1.0)
        rho_scale = self._rho_scale()
        gn = self._aux_grad_norm(grads, variables)
        for i, (g, v) in enumerate(zip(grads, variables)):
            g = ops.cast(g, v.dtype)
            if self._is_muon[i]:
                u = self._ortho(to_muon_matrix(g))
                self.assign(self._u0[i], u)
                e = from_muon_matrix(ops.cast(rho_scale, v.dtype) * self.rho_muon * u, v.shape)
            else:
                self.assign(self._g0[i], g)
                scale = ops.square(v) if self.adaptive else 1.0
                e = scale * g * (ops.cast(rho_scale, v.dtype) * self.rho_aux / (ops.cast(gn, v.dtype) + 1e-12))
            self.assign(self._eps[i], e)
            self.assign_add(v, e)

    # ---------- phase 2 of a 2-pass step ----------
    def sam_second_step(self, grads, variables):
        """Restore w, update with the perturbed gradient, refresh the LookSAM correction."""
        for i, v in enumerate(variables):
            self.assign_sub(v, self._eps[i])
        for i, (g, v) in enumerate(zip(grads, variables)):
            g = ops.cast(g, v.dtype)
            if self._is_muon[i]:
                u_s = self._ortho(to_muon_matrix(g))
                u = self._u0[i]
                coef = ops.sum(u * u_s) / (ops.sum(ops.square(u)) + 1e-12)
                self.assign(self._uv[i], u_s - coef * u)      # orthogonal component
                if self.momentum_mode == "pre_ns5":
                    # O(m) differs from O(g_s), so this costs one extra NS5 -- but only
                    # on the 1-in-k SAM steps.
                    d = self._ortho(to_muon_matrix(self._muon_grad(i, g)))
                else:
                    d = self._muon_dir(i, u_s)
                self._apply_muon(v, i, d)
            else:
                g0 = self._g0[i]
                coef = ops.sum(g0 * g) / (ops.sum(ops.square(g0)) + 1e-12)
                self.assign(self._gv[i], g - coef * g0)
                self._apply_adam(v, i, g)
        self._uv_ready = True

    # ---------- 1-pass step ----------
    def looksam_update(self, grads, variables, use_correction=None):
        """Reuse the stored correction instead of paying for a second pass.

        use correction is a Python bool on purpose: passed as an argument to a traced
        step function it costs one extra trace, whereas reading self._uv_ready inside
        the graph would freeze it at whatever it was during the first trace.
        """
        self._ensure_built(variables)
        if use_correction is None:
            use_correction = self._uv_ready
        self.assign_add(self._step, 1.0)
        for i, (g, v) in enumerate(zip(grads, variables)):
            g = ops.cast(g, v.dtype)
            if self._is_muon[i]:
                u_t = self._ortho(to_muon_matrix(self._muon_grad(i, g)))
                if use_correction:
                    u_v = self._uv[i]
                    ratio = ops.norm(u_t) / (ops.norm(u_v) + 1e-12)
                    d = u_t + self.alpha * ratio * u_v
                    if self.reorthogonalize:
                        d = self._ortho(d)
                else:
                    d = u_t
                self._apply_muon(v, i, self._muon_dir(i, d))
            else:
                if use_correction:
                    g_v = self._gv[i]
                    ratio = ops.norm(g) / (ops.norm(g_v) + 1e-12)
                    g = g + self.alpha * ratio * g_v
                self._apply_adam(v, i, g)

    def get_config(self):
        config = super().get_config()
        config.update(dict(
            total_steps=self.total_steps, aux_learning_rate=self.aux_learning_rate,
            rho_muon=self.rho_muon, rho_aux=self.rho_aux,
            rho_warmup_frac=self.rho_warmup_frac, sam_period=self.sam_period,
            ns_steps=self.ns_steps, looksam_alpha=self.alpha,
            reorthogonalize=self.reorthogonalize, momentum_mode=self.momentum_mode,
            momentum=self.momentum, nesterov=self.nesterov, adaptive=self.adaptive,
            weight_decay=self.muon_weight_decay, adam_betas=self.adam_betas, adam_eps=self.adam_eps
        ))
        return config