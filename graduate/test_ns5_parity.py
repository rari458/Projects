"""Stage 1 of the TensorFlow port: the Keras NS5 must match the PyTorch NS5.

Runs both frameworks in one process on the real ResNet-18 Muon-group shapes, so the 
comparison is against the matrices muon_update() actually sees rather than toy inputs.
Everything downstream -- the Keras Muon optimizer, MuonSAM, the TF benchmark -- is
meaningless if this drifts, so run it before touching any of them.

Tolerance is 1e-5 absolute. Residual differences are float32 accumulation over the 5
NS5 iterations plus a different matmul order in oneDNN vs ATen; they grow with matrix
size and are not an algorithmic difference.
"""
import sys

import numpy as np
import torch
import torch.nn as nn
import torchvision
from keras import ops

from muon import zeropower_via_newtonschulz5 as ns5_torch
from muon_tf import zeropower_via_newtonschulz5 as ns5_keras, muon_scale

ATOL = 1e-5

def muon_group_shapes():
    """The 2D shapes muon_update() sees for benchmark_cifar10.py's ResNet-18.

    Mirrors split_params(): ndim >= 2 and not the head, then the ndim == 4 ->
    (len(g), -1) collapse that muon_update / MuonSAM._ortho apply internally.
    """
    m = torchvision.models.resnet18(num_classes=10)
    m.conv1 = nn.Conv2d(3, 64, 3, 1, 1, bias=False)
    m.maxpool = nn.Identity()
    shapes = []
    for name, p in m.named_parameters():
        if p.ndim >= 2 and "fc" not in name:
            shapes.append((name, (p.shape[0], int(np.prod(p.shape[1:])))))
    return shapes

def main():
    rng = np.random.default_rng(0)
    worst = 0.0
    failures = []

    print(f"{'param':28}{'2D shape':>14}{'max|diff|':>12}{'rel':>10}")
    for name, shape in muon_group_shapes():
        g = rng.standard_normal(shape).astype(np.float32)

        # fp32 on both sides: muon.py's bf16 branch is CUDA-only and this machine is CPU.
        # A GPU parity check would have to compare bf16 and loosen ATOL to ~1e-2.
        t = ns5_torch(torch.from_numpy(g), steps=5).float().numpy()
        k = ops.convert_to_numpy(ns5_keras(ops.convert_to_tensor(g), steps=5))

        diff = np.abs(t - k).max()
        rel = diff / (np.abs(t).max() + 1e-12)
        worst = max(worst, diff)
        if diff > ATOL:
            failures.append((name, diff))
        print(f"  {name:26}{str(shape):>14}{diff:12.2e}{rel:10.2e}")

    # The sqrt(fan) factor is orientation-dependent, and a transposed Keras kernel
    # would take it silently -- 1.0 for a PyTorch (10, 512) head vs 7.16 for the
    # Keras (512, 10) one. Pin it here so the port cannot regress on that axis.
    head = ops.convert_to_tensor(rng.standard_normal((10, 512)).astype(np.float32))
    assert abs(muon_scale(head) - max(1.0, 10 / 512) ** 0.5) < 1e-12
    wide = ops.convert_to_tensor(rng.standard_normal((512, 10)).astype(np.float32))
    assert abs(muon_scale(wide) - max(1.0, 512 / 10) ** 0.5) < 1e-12

    print(f"\nworst max|diff| = {worst:.2e}  (atol {ATOL:.0e})")
    if failures:
        print(f"FAILED on {len(failures)} shapes: {failures}")
        return 1
    print("PARITY OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())