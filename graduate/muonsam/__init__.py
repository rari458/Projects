"""MuonSAM -- SAM's perturbation in Muon's spectral geometry.
    
    from muonsam import MuonSAM
    
    opt = MuonSAM(param_groups, total_steps=len(loader) * epochs)
    def closure():
        opt.zero_grad(); loss = criterion(model(x), y); loss.backward(); return loss
    loss = opt.step(closure)
    
Three things this API will not warn you about, because each produces a healthy-looking
run rather than an error -- see the README:
  - step() requires the closure; it does the zero_grad/forward/backward itself.
  - Do NOT wrap step() in your own zero_grad(); MuonSAM clears grads internally.
  - total_steps is required. The rho schedule runs off an internal counter, not the
    LR scheduler, so a wrong value silently changes the optimizer.
    
The Keras port is a separate opt-in import (`from muonsam.keras import KerasMuonSAM`);
importing it here would drag Keras into every torch-only install.
"""
from .muon import (
    zeropower_via_newtonschulz5,
    muon_update,
    adam_update,
    MuonWithAuxAdam,
    Muon,
    SingleDeviceMuon,
    SingleDeviceMuonWithAuxAdam,
)
from .muon_sam import MuonSAM
from .sam import SAM

__version__ = "0.1.0"
__all__ = [
    "MuonSAM", "SAM",
    "Muon", "SingleDeviceMuon", "MuonWithAuxAdam", "SingleDeviceMuonWithAuxAdam",
    "zeropower_via_newtonschulz5", "muon_update", "adam_update",
]
