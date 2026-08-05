"""Stage 2 of the TensorFlow port: KerasMuon must equal SingleDeviceMuonWithAuxAdam.

Builds the same tiny conv net in both frameworks, copies PyTorch's weights into Keras
(with the layout conversions), then runs identical batches through both optimizers and
compares every weight. This is the TF analogue of the rho-off regression in
test_muon_sam.py, which is what made the PyTorch results trustworthy.

Tolerance is 1e-4: NS5 in float32 already differs by ~3e-6 per call (see
test_ns5_parity.py) and that compounds over steps.
"""
import sys

import numpy as np
import torch
import torch.nn as nn

# torch.optim.Optimizer lazily imports torch._dynamo on first construction, and that
# import segfaults if TensorFlow is already loaded in the process. Pull it in here,
# before keras/TF, and the two frameworks coexist fine.
import torch._dynamo  # noqa: F401

import keras
import tensorflow as tf
from keras import layers, ops

from muon import SingleDeviceMuonWithAuxAdam
from muon_keras import KerasMuon, split_variables

ATOL = 1e-4
STEPS = 5
LR_MUON, LR_AUX, WD = 0.02, 1e-3, 5e-4
BN_EPS = 1e-5          # Keras defaults to 1e-3; PyTorch to 1e-5. This changes gradients.

class TorchNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(8, eps=BN_EPS)
        # A 2D hidden weight, so the Muon group holds one conv AND one Dense. Without it
        # to_muon_matrix()'s 2D branch never runs, and the Keras (in, out) vs PyTorch
        # (out, in) transpose goes untested -- the one layout error that silently changes
        # muon_scale (sqrt(2) vs 1.0 here) instead of raising.
        self.hidden = nn.Linear(8, 16, bias=False)
        self.fc = nn.Linear(16, 10)

    def forward(self, x):
        h = torch.relu(self.bn(self.conv(x)))
        h = torch.relu(self.hidden(h.mean(dim=(2,3))))
        return self.fc(h)

def build_keras_net():
    inp = keras.Input((8, 8, 3))
    x = layers.Conv2D(8, 3, 1, "same", use_bias=False, name="conv")(inp)
    x = layers.BatchNormalization(epsilon=BN_EPS, name="bn")(x)
    x = layers.ReLU()(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(16, use_bias=False, name="hidden")(x)
    x = layers.ReLU()(x)
    out = layers.Dense(10, name="fc")(x)
    return keras.Model(inp, out)

def copy_torch_to_keras(tm, km):
    """PyTorch layouts -> Keras layouts, variable by variable.
    
    Layers are addressed by name, not by index: inserting a layer shifts every index
    after it, and the result is a silent wrong-weights copy rather than an error.
    """
    sd = tm.state_dict()
    km.get_layer("conv").set_weights([sd["conv.weight"].numpy().transpose(2, 3, 1, 0)])
    km.get_layer("bn").set_weights([sd["bn.weight"].numpy(), sd["bn.bias"].numpy(),
                                    sd["bn.running_mean"].numpy(), sd["bn.running_var"].numpy()])
    km.get_layer("hidden").set_weights([sd["hidden.weight"].numpy().T])
    km.get_layer("fc").set_weights([sd["fc.weight"].numpy().T, sd["fc.bias"].numpy()])

def main():
    torch.manual_seed(0)
    tm = TorchNet()
    km = build_keras_net()
    copy_torch_to_keras(tm, km)

    t_muon = [p for n, p in tm.named_parameters() if p.ndim >= 2 and "fc" not in n]
    t_aux = [p for n, p in tm.named_parameters() if not (p.ndim >= 2 and "fc" not in n)]
    t_opt = SingleDeviceMuonWithAuxAdam([
        dict(params=t_muon, use_muon=True, lr=LR_MUON, weight_decay=WD),
        dict(params=t_aux, use_muon=False, lr=LR_AUX, weight_decay=WD)
    ])
    k_muon, _ = split_variables(km)
    k_opt = KerasMuon(k_muon, learning_rate=LR_MUON, aux_learning_rate=LR_AUX, weight_decay=WD)
    print(f"muon vars: torch {len(t_muon)} | keras {len(k_muon)}")
    assert len(t_muon) == len(k_muon)

    crit = nn.CrossEntropyLoss()
    k_loss = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    rng = np.random.default_rng(1)

    for step in range(1, STEPS + 1):
        xb = rng.standard_normal((16, 3, 8, 8)).astype(np.float32)
        yb = rng.integers(0, 10, 16).astype(np.int64)

        t_opt.zero_grad()
        lt = crit(tm(torch.from_numpy(xb)), torch.from_numpy(yb))
        lt.backward()
        t_opt.step()

        xk = tf.constant(xb.transpose(0, 2, 3, 1))
        with tf.GradientTape() as tape:
            lk = k_loss(tf.constant(yb), km(xk, training=True))
        grads = tape.gradient(lk, km.trainable_variables)
        k_opt.apply(grads, km.trainable_variables)
        print(f"  step {step}: torch loss {lt.item():.6f} | keras loss {float(lk):.6f}"
              f" | dloss {abs(lt.item() - float(lk)):.2e}")

    sd = tm.state_dict()
    pairs = [
        ("conv.weight",   km.get_layer("conv").weights[0],   lambda a: a.transpose(2, 3, 1, 0)),
        ("bn.weight",     km.get_layer("bn").weights[0],     lambda a: a),
        ("bn.bias",       km.get_layer("bn").weights[1],     lambda a: a),
        ("hidden.weight", km.get_layer("hidden").weights[0], lambda a: a.T),
        ("fc.weight",     km.get_layer("fc").weights[0],     lambda a: a.T),
        ("fc.bias",       km.get_layer("fc").weights[1],     lambda a: a)
    ]
    print(f"\n{'weight':16}{'shape':>18}{'max|diff|':>12}")
    worst, fails = 0.0, []
    for name, kvar, conv in pairs:
        t = conv(sd[name].numpy())
        k = ops.convert_to_numpy(kvar)
        d = np.abs(t - k).max()
        worst = max(worst, d)
        if d > ATOL:
            fails.append((name, d))
        print(f"  {name:14}{str(t.shape):>18}{d:12.2e}")

    print(f"\nworst max|diff| = {worst:.2e}  (atol {ATOL:.0e})")
    if fails:
        print(f"FAILED: {fails}")
        return 1
    print("PARITY OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())