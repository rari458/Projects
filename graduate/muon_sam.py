import torch
from muon import zeropower_via_newtonschulz5, adam_update

class MuonSAM(torch.optim.Optimizer):
    """Muon + SAM with LookSAM-style periodic perturbation, lifted into Muon's spectral geometry.

    Muon group (2D hidden weights):
      - spectral perturbation  e = rho * O(g),  O(.) = NS5(.) ~ U V^T   (Step 1 decision)
      - every `sam_period` (= LookSAM frequency k) steps: full 2-pass SAM, then store the
        orthogonalized correction  u_v = u_s - <u,u_s>/||u||_F^2 * u   (Frobenius-space LookSAM)
      - intermediate steps: 1-pass, reuse u_v:  d = u_t + alpha*(||u_t||_F/||u_v||_F)*u_v,
        optionally re-orthogonalized (D2).
    Aux group (embed/head/scalar -> AdamW): standard L2 SAM perturbation + original (Euclidean)
    LookSAM correction g_v, applied per-parameter.

    DESIGN NOTE (flagged in the Step-1/Step-4 math): this prototype DROPS Muon's internal
    momentum on the Muon group -- the orthogonalized direction is used directly as the update,
    to keep the LookSAM logic readable. Reintroducing momentum (momentum-before-NS5 as in
    muon.py, or momentum-on-direction) is a documented fork to evaluate on GPU. Expect the
    Muon-group behaviour here to differ from the earlier momentum-having MuonSAM.
    """
    def __init__(self, param_groups, total_steps, rho_max=0.05, rho_warmup_frac=0.0,
                 sam_period=5, ns_steps=5, looksam_alpha=0.7, reorthogonalize=True):
        for group in param_groups:
            assert "use_muon" in group
            group.setdefault("rho", rho_max)
            group.setdefault("adaptive", False)
            if group["use_muon"]:
                group.setdefault("lr", 0.02)
                group.setdefault("weight_decay", 0.0)
            else:
                group.setdefault("lr", 3e-4)
                group.setdefault("betas", (0.9, 0.95))
                group.setdefault("eps", 1e-10)
                group.setdefault("weight_decay", 0.0)
        super().__init__(param_groups, dict())
        self.total_steps = total_steps
        self.rho_max = rho_max
        self.rho_warmup_frac = rho_warmup_frac
        self.sam_period = sam_period          # = LookSAM update frequency k
        self.ns_steps = ns_steps
        self.alpha = looksam_alpha
        self.reorthogonalize = reorthogonalize
        self._t = 0

    # ---------- helpers ----------
    def _rho_scale(self):
        frac = self._t / max(1, self.total_steps)
        if frac < self.rho_warmup_frac: return 0.0
        span = 1.0 - self.rho_warmup_frac
        return min(1.0, (frac - self.rho_warmup_frac) / max(1e-8, span))

    def _ortho(self, grad):
        """O(.) = NS5 with conv reshape + sqrt(fan) scaling. Returns a 2D matrix.
        NS5 normalizes spectral norm internally, so calling this on an already-scaled
        matrix (re-orthogonalization) does not double-apply the sqrt(fan) factor."""
        g = grad
        if g.ndim == 4: g = g.view(len(g), -1)
        o = zeropower_via_newtonschulz5(g, steps=self.ns_steps)
        o *= max(1, o.size(-2) / o.size(-1)) ** 0.5
        return o

    def _aux_grad_norm(self, group):
        return torch.norm(torch.stack([
            ((p.abs() if group["adaptive"] else 1.0) * p.grad).norm(2)
            for p in group["params"] if p.grad is not None
        ]), 2)

    def _apply_muon(self, p, group, direction_2d):
        p.mul_(1 - group["lr"] * group["weight_decay"])
        p.add_(direction_2d.reshape(p.shape), alpha=-group["lr"])

    def _apply_adam(self, p, group, grad):
        st = self.state[p]
        if "exp_avg" not in st:
            st["exp_avg"] = torch.zeros_like(p)
            st["exp_avg_sq"] = torch.zeros_like(p)
            st["step"] = 0
        st["step"] += 1
        upd = adam_update(grad, st["exp_avg"], st["exp_avg_sq"],
                          st["step"], group["betas"], group["eps"])
        p.mul_(1 - group["lr"] * group["weight_decay"])
        p.add_(upd, alpha=-group["lr"])
    
    # ---------- SAM step (every k): 2-pass, refresh correction ----------
    @torch.no_grad()
    def _sam_first_step(self, rho_scale):
        """Perturb w -> w+e using the clean gradient g; stash quantities for the projection."""
        for group in self.param_groups:
            rho = group["rho"] * rho_scale
            if group["use_muon"]:
                for p in group["params"]:
                    if p.grad is None: continue
                    u = self._ortho(p.grad)
                    self.state[p]["u_vanilla"] = u
                    e = (rho * u).reshape(p.shape)
                    self.state[p]["e"] = e
                    p.add_(e)
            else:
                gn = self._aux_grad_norm(group)
                for p in group["params"]:
                    if p.grad is None: continue
                    self.state[p]["g_vanilla"] = p.grad.detach().clone()
                    e = (p.pow(2) if group["adaptive"] else 1.0) * p.grad * (rho / (gn + 1e-12))
                    self.state[p]["e"] = e
                    p.add_(e)

    @torch.no_grad()
    def _sam_second_step(self):
        """Restore w; update with the SAM gradient; store the (slowly-varying) correction."""
        for group in self.param_groups:               # restore w first
            for p in group["params"]:
                if "e" in self.state[p]:
                    p.sub_(self.state[p]["e"])
        for group in self.param_groups:               # then update + store correction
            if group["use_muon"]:
                for p in group["params"]:
                    if p.grad is None: continue
                    u_s = self._ortho(p.grad)           # O(g_s)
                    u = self.state[p]["u_vanilla"]
                    coef = (u * u_s).sum() / (u.pow(2).sum() + 1e-12)   # <u,u_s>/||u||_F^2
                    self.state[p]["u_v"] = u_s - coef * u               # orthogonal component
                    self._apply_muon(p, group, u_s)
            else:
                for p in group["params"]:
                    if p.grad is None: continue
                    g_s = p.grad
                    g = self.state[p]["g_vanilla"]
                    coef = (g * g_s).sum() / (g.pow(2).sum() + 1e-12)
                    self.state[p]["g_v"] = g_s - coef * g
                    self._apply_adam(p, group, g_s)

    # ---------- intermediate step: 1-pass, reuse correction ----------
    @torch.no_grad()
    def _looksam_update(self):
        for group in self.param_groups:
            if group["use_muon"]:
                for p in group["params"]:
                    if p.grad is None: continue
                    u_t = self._ortho(p.grad)
                    st  = self.state[p]
                    if "u_v" in st:                                     # reuse stored correction
                        u_v = st["u_v"]
                        ratio = u_t.norm() / (u_v.norm() + 1e-12)
                        d = u_t + self.alpha * ratio * u_v
                        if self.reorthogonalize: d = self._ortho(d)     # D2: keep it orthogonal
                    else: d = u_t                                       # warmup: plain Muon
                    self._apply_muon(p, group, d)
            else:
                for p in group["params"]:
                    if p.grad is None: continue
                    g_t = p.grad
                    st = self.state[p]
                    if "g_v" in st:
                        g_v = st["g_v"]
                        ratio = g_t.norm() / (g_v.norm() + 1e-12)
                        g = g_t + self.alpha * ratio * g_v
                    else: g = g_t
                    self._apply_adam(p, group, g)

    # ---------- orchestration ----------
    @torch.no_grad()
    def step(self, closure):
        assert closure is not None, "MuonSAM requires a closure (full forward-backward)."
        closure = torch.enable_grad()(closure)

        with torch.enable_grad(): loss = closure()  # 1st pass @ w -> clean grad g
        self._t += 1

        rho_scale = self._rho_scale()
        do_sam = (rho_scale > 0.0) and (self._t % self.sam_period == 0)

        if do_sam:
            self._sam_first_step(rho_scale)       # stash u/g, perturb to w+e
            self.zero_grad()
            with torch.enable_grad(): closure()   # 2nd pass @ w+e -> g_s
            self._sam_second_step()               # restore, update, refresh u_v/g_v
        else: self._looksam_update()              # reuse stored correction (1 pass)

        self.zero_grad()
        return loss