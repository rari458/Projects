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
`t % sam_period == 0` test written inside the traced region is evaluated once and frozen
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
        correction_mode: "looksam" | "gsam". Which published decomposition the stored
                        correction follows. Both act inside span{O(g), O(g_s)} and differ
                        only in projection target and sign -- see _store_correction().
        adaptive_muon / adaptive_aux: ASAM (kwon21b). PyTorch's per-group `adaptive`
                        splits in two here for the same reason rho did. The aux flag is
                        ASAM as published (elementwise |w|); the Muon flag scales the
                        spectral perturbation by ||W||_F. benchmark_cifar10.py's
                        muonsam_asam sets both at once.
    """

    def __init__(self, muon_variables, total_steps,
                 learning_rate=0.02, aux_learning_rate=1e-3,
                 rho_muon=0.05, rho_aux=0.01, rho_warmup_frac=0.0,
                 sam_period=5, ns_steps=5, looksam_alpha=0.7, reorthogonalize=True,
                 momentum_mode="pre_ns5", correction_mode="looksam", 
                 momentum=0.95, nesterov=True, 
                 adaptive_muon=False, adaptive_aux = False,
                 weight_decay=0.0, adam_betas=(0.9, 0.95), adam_eps=1e-10,
                 name="keras_muon_sam", **kwargs):
        assert momentum_mode in ("none", "pre_ns5", "post_ns5"), momentum_mode
        assert correction_mode in ("looksam", "gsam"), correction_mode
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
        self.correction_mode = correction_mode
        self.momentum = momentum
        self.nesterov = nesterov
        self.adaptive_muon = adaptive_muon
        self.adaptive_aux = adaptive_aux
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
        # zero tensor the size of every variable several times over.
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
        frac = self._t / max(1, self.total_steps)
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
        """Whether a LookSAM correction has ever been stored. Pass this to a traced
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
    
    def _correct(self, base, corr):
        """Blend a stored correction into a base direction, in whichever geometry `base`
        lives in. The two modes differ only in sign, because they store opposite
        projections -- see _store_correction()."""
        ratio = ops.norm(base) / (ops.norm(corr) + 1e-12)
        sign = -1.0 if self.correction_mode == "gsam" else 1.0
        return base + sign * self.alpha * ratio * corr
    
    def _store_correction(self, clean, perturbed):
        """The slowly-varying vector that intermediate steps reuse.

        LookSAM (2203.02714) keeps the part of the PERTURBED gradient orthogonal to the
        clean one, and adds it: it points along the flat direction SAM discovered.
        GSAM (2203.08065) keeps the part of the CLEAN gradient orthogonal to the perturbed
        one, and descends the surrogate gap by subtracting it. Both live in the same
        2D plane span{clean, perturbed}; only the projection target and the sign differ.

        Note this is a periodic variant of GSAM -- the published version re-derives the
        decomposition every step. The sam_period amortization is ours.
        """
        if self.correction_mode == "gsam":
            coef = ops.sum(perturbed * clean) / (ops.sum(ops.square(perturbed)) + 1e-12)
            return clean - coef * perturbed
        coef = ops.sum(clean * perturbed) / (ops.sum(ops.square(clean)) + 1e-12)
        return perturbed - coef * clean

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
            ops.norm((ops.abs(v) if self.adaptive_aux else 1.0) * g)
            for g, v, m in zip(grads, variables, self._is_muon) if not m
        ]
        return ops.norm(ops.stack(parts))

    # ---------- phase 1 of a 2-pass step ----------
    def sam_first_step(self, grads, variables):
        """Perturb w -> w+e along the clean gradient and stash what phase 2 needs.

        The perturbation follows the *current* gradient, not the momentum average, and
        this exploratory pass deliberately leaves every momentum buffer untouched.
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
                # ASAM (kwon21b) in Muon's geometry: without this the perturbation has a
                # fixed size regardless of how large the layer's weights are. Scaling by
                # ||W||_F makes W -> cW give e -> ce, which is exactly ASAM's property,
                # expressed in Frobenius rather than elementwise geometry. u_vanilla stays
                # unscaled -- the projection coefficient is scale-invariant, so leaving it
                # raw keeps the two modes comparable. Both norms are Frobenius and layout-
                # invariant, so v's Keras shape and u's Muon-matrix shape are comparable.
                scale = 1.0
                if self.adaptive_muon:
                    # keras.ops.norm() cannot take v: the TF backend implements only vector
                    # and matrix norms, and v is a 4D conv kernel. PyTorch's p.norm()
                    # flattens first, so sum-of-square is both the faithful port and the
                    # only form that works at any rank. u is already the 2D Muon matrix.
                    scale = ops.sqrt(ops.sum(ops.square(v))) / (ops.norm(u) + 1e-12)
                coef = ops.cast(rho_scale, v.dtype) * self.rho_muon * scale
                e = from_muon_matrix(coef * u, v.shape)
            else:
                self.assign(self._g0[i], g)
                scale = ops.square(v) if self.adaptive_aux else 1.0
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
                u_s = self._ortho(to_muon_matrix(g))            # O(g_s)
                u_v = self._store_correction(self._u0[i], u_s)  # O(g) is still in _u0
                self.assign(self._uv[i], u_v)
                if self.momentum_mode == "pre_ns5":
                    # O(m) differs from O(g_s), so this costs one extra NS5 -- but only
                    # on the 1-in-k SAM steps.
                    d = self._ortho(to_muon_matrix(self._muon_grad(i, g)))
                else:
                    d = self._muon_dir(i, u_s)
                if self.correction_mode == "gsam":
                    # GSAM's defining update applies the correction on the 2-pass step
                    # itself; LookSAM's does not, because for LookSAM this step IS the
                    # full SAM step it is amortizing. Use the local u_v rather than
                    # re-reading self._uv[i], so this does not depend on assign ordering.
                    d = self._correct(d, u_v)
                    if self.reorthogonalize:
                        d = self._ortho(d)
                self._apply_muon(v, i, d)
            else:
                g_v = self._store_correction(self._g0[i], g)
                self.assign(self._gv[i], g_v)
                upd = self._correct(g, g_v) if self.correction_mode == "gsam" else g
                self._apply_adam(v, i, upd)
        self._uv_ready = True

    # ---------- 1-pass step ----------
    def looksam_update(self, grads, variables, use_correction=None):
        """Reuse the stored correction instead of paying for a second pass.

        use_correction is a Python bool on purpose: passed as an argument to a traced
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
                    d = self._correct(u_t, self._uv[i])
                    if self.reorthogonalize:
                        d = self._ortho(d)      # D2: keep it orthogonal
                else:
                    d = u_t                     # warmup: plain Muon
                self._apply_muon(v, i, self._muon_dir(i, d))
            else:
                if use_correction:
                    g = self._correct(g, self._gv[i])
                self._apply_adam(v, i, g)

    def get_config(self):
        config = super().get_config()
        config.update(dict(
            total_steps=self.total_steps, aux_learning_rate=self.aux_learning_rate,
            rho_muon=self.rho_muon, rho_aux=self.rho_aux,
            rho_warmup_frac=self.rho_warmup_frac, sam_period=self.sam_period,
            ns_steps=self.ns_steps, looksam_alpha=self.alpha,
            reorthogonalize=self.reorthogonalize, momentum_mode=self.momentum_mode,
            correction_mode=self.correction_mode,
            momentum=self.momentum, nesterov=self.nesterov,
            adaptive_muon=self.adaptive_muon, adaptive_aux=self.adaptive_aux,
            weight_decay=self.muon_weight_decay, adam_betas=self.adam_betas, adam_eps=self.adam_eps
        ))
        return config