"""Gate for any change to muon_sam.py: the working tree must move the weights exactly as 
the reference revision does, or every reported CIFAR-10 number needs re-running.

    python check_bitidentical.py [ref]      # ref defaults to HEAD

Neither test_muon_sam.py nor preflight.py can see a broken SAM step. The former's only
exactness assertion is the rho=0 reduction, which never enters that code; the latter only
checks that the loss is finite and the weights moved. A misapplied edit that deleted the
aux perturbation and stopped restoring w passed both.
"""
import os
import subprocess
import sys
import tempfile
import torch
import torch.nn as nn

REF = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
# `<rev>:./path` resolves relative to the cwd, so this works from anywhere in the repo and
# in any clone. The reference goes under a distinct module name so that `muon_sam` still
# resolves to the working tree's copy.
_ref_src = subprocess.check_output(["git", "show", f"{REF}:./muon_sam.py"])
_ref_dir = tempfile.mkdtemp(prefix="muon_sam_ref_")
with open(os.path.join(_ref_dir, "muon_sam_ref.py"), "wb") as f:
    f.write(_ref_src)
if _ref_src == open("muon_sam.py", "rb").read():
    print(f"note: muon_sam.py is identical to {REF}, so this run proves nothing. "
          f"Compare against the pre-change revision instead, e.g. {REF}~1.\n")
sys.path.insert(0, ".")          # muon.py, muon_sam.py -- the working tree
sys.path.insert(0, _ref_dir)     # muon_sam_ref.py -- the reference revision

from muon_sam import MuonSAM
from muon_sam_ref import MuonSAM as MuonSAMRef

class Tiny(nn.Module):
    """Both param groups, so the Muon branch (e_coef) and the aux branch (e) both run."""
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.bn = nn.BatchNorm2d(8)
        self.fc = nn.Linear(8 * 4 * 4, 10)

    def forward(self, x):
        return self.fc(torch.relu(self.bn(self.conv(x))).flatten(1))

def run(cls, adaptive, steps=15):
    torch.manual_seed(0)
    model = Tiny()
    is_muon = lambda n, p: p.ndim >= 2 and "fc" not in n
    muon = [p for n, p in model.named_parameters() if is_muon(n, p)]        
    aux = [p for n, p in model.named_parameters() if not is_muon(n, p)]
    opt = cls(
        [dict(params=muon, use_muon=True, lr=0.02, rho=0.05, weight_decay=5e-4, adaptive=adaptive),
         dict(params=aux, use_muon=False, lr=1e-3, rho=0.01, weight_decay=5e-4, adaptive=adaptive)],
         total_steps=steps, rho_max=0.05, rho_warmup_frac=0.3, sam_period=5, momentum_mode="pre_ns5"
    )   # rho goes live at step 5; SAM fires at 5, 10, 15
    crit, g = nn.CrossEntropyLoss(), torch.Generator().manual_seed(1)
    for _ in range(steps):
        x = torch.randn(8, 3, 4, 4, generator=g)
        y = torch.randint(0, 10, (8,), generator=g)

        def closure():
            opt.zero_grad()
            loss = crit(model(x), y)
            loss.backward()
            return loss

        opt.step(closure)
    return [p.detach().clone() for p in model.parameters()]

ok = True
for adaptive in (False, True):     # adaptive=True is the one where coef is a tensor
    d = max((a - b).abs().max().item() for a, b in zip(run(MuonSAM, adaptive), run(MuonSAMRef, adaptive)))
    ok &= d ==0.0
    print(f"adaptive={str(adaptive):5}  max |diff| = {d:.2e}  {'OK' if d == 0.0 else 'CHANGED'}")

print("\n" + ("bit-identical -- every existing CIFAR-10 result stands" if ok else "NOT bit-identical -- revert the change"))