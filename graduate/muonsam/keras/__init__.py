"""Keras 3 port, pinned to the PyTorch implementations by the four parity tests.

Written against `keras.ops`, so the TensorFlow, JAX and PyTorch Keras backends all work --
with one exception: `train_tf.make_train_step` imports `tensorflow` directly and is 
therefore NOT re-exported here. Import it explicitly when you want it:

    from muonsam.keras.train_tf import make_train_step
    
`KerasMuonSAM.update_step` raises. A Keras optimizer only receives gradients someone else
computed, so it cannot run SAM's second forward-backward pass; the training loop calls
sam_first_step / sam_second_step / looksam_update itself. See the README.

Note this subpackage is named `keras` and shadows nothing: absolute imports mean `import
keras` inside these modules still resolves to Keras itself.
"""
from .muon_tf import zeropower_via_newtonschulz5, muon_scale
from .muon_keras import KerasMuon, to_muon_matrix, from_muon_matrix, split_variables
from .muon_sam_keras import KerasMuonSAM, muon_matrix_shape

__all__ = [
    "KerasMuonSAM", "KerasMuon",
    "split_variables", "to_muon_matrix", "from_muon_matrix", "muon_matrix_shape",
    "zeropower_via_newtonschulz5", "muon_scale",
]
