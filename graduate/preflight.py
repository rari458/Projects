"""Pre-flight for benchmark_cifar10.py: every KIND must build with the right config and
step through train_epoch's dispatch.

Run this before every cloud run. A misrouted kind or a silently wrong config otherwise
surfaces hours into a multi-hour job -- `momentum_mode="nonw"` once sat five optimizers
deep in KINDS, which is ~4 h into a T4 run.

Uses a tiny model so NS5 stays cheap: this checks wiring and config, not numerics.
"""
import sys
import torch
import torch.nn as nn

import benchmark_cifar10 as B
from muon_sam import MuonSAM


class Tiny(nn.Module):
    """Mirrors what split_params has to route: a 4D conv, 1D BN params, and an "fc" head."""
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)   # 4D    -> Muon group
        self.bn = nn.BatchNorm2d(8)                 # 1D    -> aux group
        self.fc = nn.Linear(8 * 4 * 4, 10)          # "fc"  -> aux group

    def forward(self, x):
        return self.fc(torch.relu(self.bn(self.conv(x))).flatten(1))


def check_cfg(kind, opt):
    """What each kind must actually be, beyond "it ran without raising"."""
    if kind == "muon_nomom":
        # This ablation cell only means anything if SAM is off for the whole run and Muon's
        # momentum is disabled. Sharing muonsam's config silently turns it into a duplicate
        # of muonsam_nomom -- which still trains, and still looks fine in the log.
        assert isinstance(opt, MuonSAM)
        assert opt.momentum_mode == "none", opt.momentum_mode
        opt._t = opt.total_steps                    # worst case: the very end of training
        assert opt._rho_scale() == 0.0, f"rho is live ({opt._rho_scale()}) -- SAM is not off"
    elif kind == "muonsam_nomom":
        assert opt.momentum_mode == "none" and opt.rho_max > 0
        assert opt.correction_mode == "looksam", opt.correction_mode
    elif kind == "muonsam":
        assert opt.momentum_mode == "pre_ns5" and opt.rho_max > 0
        assert opt.correction_mode == "looksam", opt.correction_mode
        assert opt.rho_warmup_frac > 0, "the default arm must keep its warm-start"
        assert not any(g["adaptive"] for g in opt.param_groups)
    elif kind == "muonsam_gsam":
        # Must differ from muonsam in exactly one axis, or the comparison measures nothing.
        assert opt.correction_mode == "gsam", opt.correction_mode
        assert opt.momentum_mode == "pre_ns5" and opt.rho_warmup_frac > 0
        assert not any(g["adaptive"] for g in opt.param_groups)
    elif kind == "muonsam_nowarm":
        # The point of this arm is that rho is live from step; if the warm-start survives
        # it is just a slower copy of muonsam.
        assert opt.rho_warmup_frac == 0.0, opt.rho_warmup_frac
        opt._t = 1
        assert opt._rho_scale() > 0.0, "rho is still zero at step 1 -- no ablation here"
        assert opt.correction_mode == "looksam" and opt.momentum_mode == "pre_ns5"


def main():
    criterion = nn.CrossEntropyLoss()
    batches = [(torch.randn(8, 3, 4, 4), torch.randint(0, 10, (8,))) for _ in range(6)]
    B.DEVICE = "cpu"

    # Check everything build_optimizer knows, not just today's KINDS. The variants outside
    # KINDS are the dangerous ones: they are selected by overriding B.KINDS in a notebook,
    # so nothing has ever built them before the cloud run does.
    all_kinds = list(dict.fromkeys(list(B.KINDS) + list(B.CLOSURE_KINDS)))
    print(f"KINDS         = {B.KINDS}")
    print(f"CLOSURE_KINDS = {B.CLOSURE_KINDS}\n")
    print(f"checking      = {all_kinds}\n")
    failed = 0
    for kind in all_kinds:
        torch.manual_seed(0)
        model = Tiny()
        try:
            opt = B.build_optimizer(kind, model, total_steps=6)
            check_cfg(kind, opt)
            if isinstance(opt, MuonSAM):
                opt._t = 0                          # undo the probe in check_cfg
            before = model.conv.weight.detach().clone()
            loss = B.train_epoch(kind, model, opt, batches, criterion)
            moved = not torch.equal(before, model.conv.weight)
            ok = moved and torch.isfinite(torch.tensor(loss))
            failed += not ok
            print(f"  {kind:16} {type(opt).__name__:28} loss={loss:.4f} "
                  f"conv_updated={moved} {'OK' if ok else 'FAIL'}")
        except Exception as e:
            failed += 1
            print(f"  {kind:16} FAIL: {type(e).__name__}: {e}")

    print("\n" + ("all kinds OK" if not failed else f"{failed} kind(s) FAILED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
