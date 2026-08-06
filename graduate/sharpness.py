"""Measure how flat the minimum is -- the mechanism the accuracy numbers only imply.

The project's claim is Muon's convergence speed plus SAM's generalization, and so far the
only evidence for the second half is test accuracy. This closes that gap with two
measurements, both post-hoc on a saved checkpoint, neither requiring retraining:

  adaptive_sharpness()  a scalar: how much the loss can rise inside a scale-invariant
                        ball around the minimum. ASAM's definition (kwon21b), not SAM's.
  loss_profile()        a curve: the loss along a filter-normalized random direction,
                        the standard picture from Li et al., NeurIPS 2018.

Both are normalized for a reason that is easy to get wrong. Raw sharpness -- Hessian
eigenvalues, or the loss rise inside a fixed-radius L2 ball -- is meaningless for a
BN network. Li et al.: "The scaling of weights in these networks is irrelevant because
batch normalization re-scales the outputs to have unit variance. However, small weights
still appear more sensitive to perturbations, and produce sharper looking minimizers."
ASAM proves the same thing formally and shows the scale-invariant version correlates
better with the generalization gap. A comparison built on the unnormalized quantity
measures weight scale, not flatness, and would be rejected on sight.

Usage:
    python sharpness.py ckpt_muonsam_seed0.pt ckpt_muon_seed0.pt ...
"""
import os
import sys

import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as T
from torch.utils.data import DataLoader, Subset

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EVAL_BATCHES = int(os.environ.get("EVAL_BATCHES", 8))   # subset size; sharpness is a ratio
RHO = float(os.environ.get("SHARP_RHO", 0.5))           # ASAM's radius, in relative units
ASCENT_STEPS = int(os.environ.get("ASCENT_STEPS", 5))
ALPHAS = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]

def make_resnet18():
    """Must match benchmark_cifar10.py exactly or the checkpoint will not load."""
    m = torchvision.models.resnet18(num_classes=10)
    m.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    m.maxpool = nn.Identity()
    return m

def get_eval_loader(batch=128):
    mean, std = (0.4914, 0.4822, 0.4465), (0.2470. 0.2435, 0.2616)
    tf = T.Compose([T.ToTensor(), T.Normalize(mean, std)])
    test = torchvision.datasets.CIFAR10("./data", train=False, download=True, transform=tf)
    return DataLoader(Subset(test, range(EVAL_BATCHES * batch)), batch, shuffle=False)

def mean_loss(model,loader, criterion):
    model.eval()
    total, n = 0.0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            total += criterion(model(x), y).item() * x.size(0)
            n += x.size(0)
    return total / n

# ---------------- ASAM-style adaptive sharpness ----------------

def _is_normalizable(p):
    """ASAM's T_w is defined on the weights whose scale actually is free. BN affine
    parameters and biases are excluded -- perturbing them is not scale-equivariant with
    the layer they follow, and Li et al. exclude them from the direction for the same
    reason."""
    return p.ndim >= 2

def adaptive_sharpness(model, loader, criterion, rho=RHO, steps=ASCENT_STEPS):
    """max over ||T_w^-1 e||  <= rho of L(w+e) - L(w), with T_w = diag(|w|).

    Estimated by projected gradient ascent, which gives a lower bound on the max -- so it
    is a fair comparison between optimizers only because every arm gets the same number
    of ascent steps. Reported in loss units.
    """
    params = [p for p in model.parameters() if _is_normalizable(p)]
    base = mean_loss(model, loader, criterion)
    original = [p.detach().clone() for p in params]
    eps = [torch.zeros_like(p) for p in params]

    model.eval()
    for _ in range(steps):
        model.zero_grad(set_to_none=True)
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            (criterion(model(x), y) / len(loader)).backward()
        with torch.no_grad():
            # One ASAM ascent step: e < -e + lr * T^2 g / ||T g||, then project back into
            # the T-ball. T^2 g is ASAM's ascent direction; the T-norm is what makes the
            # constraint scale-invariant.
            tg = [w.abs() * p.grad for w, p in zip(original, params)]
            norm = torch.norm(torch.stack([t.norm() for t in tg])) + 1e-12
            for e, w, p in zip(eps, original, params):
                e.add_(w.abs() * w.abs() * p.grad / norm, alpha=rho / steps)
            tnorm = torch.norm(torch.stack([(e / (w.abs() + 1e-12)).norm() for e, w in zip(eps, original)]))

            if tnorm > rho:
                for e in eps:
                    e.mul_(rho / tnorm)
            for p, w, e in zip(params, original, eps):
                p.copy_(w + e)

    peak = mean_loss(model, loader, criterion)
    with torch.no_grad():
        for p, w in zip(params, original):
            p.copy_(w)
    return peak - base, base

# ---------------- filter-normalized loss profile ----------------

def filter_normalized_direction(model, generator=None):
    """A random direction scaled so each filter's step is proportional to that filter's
    own norm -- Li et al.'s fix for the fact that a plain random direction makes
    small-weight layers look sharp. Biases and BN parameters get a zero direction, as in
    the paper."""
    direction = []
    for p in model.parameters():
        if not _is_normalizable(p):
            direction.append(torch.zeros_like(p))
            continue
        d = torch.randn(p.shape, generator=generator, device=p.device, dtype=p.dtype)
        flat_d, flat_p = d.reshape(len(d), -1), p.reshape(len(p), -1)
        scale = flat_p.norm(dim=1, keepdim=True) / (flat_d.norm(dim=1, keepdim=True) + 1e-12)
        direction.append((flat_d * scale).reshape(p.shape))
    return direction

def loss_profile(model, loader, criterion, direction, alphas=ALPHAS):
    original = [p.detach().clone for p in model.parameters()]
    out = []
    for a in alphas:
        with torch.no_grad():
            for p, w, d in zip(model.parameters(), original, direction):
                p.copy_(w + a * d)
        out.append(mean_loss(model, loader, criterion))
    with torch.no_grad():
        for p, w in zip(model.parameters(), original):
            p.copy_(w)
    return out

# ---------------- driver ----------------

def analyze(path, loader, criterion):
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    model = make_resnet18().to(DEVICE)
    model.load_state_dict(ckpt["state_dict"])
    sharp, base = adaptive_sharpness(model, loader, criterion)
    # Same generator seed for every checkpoint: the direction is random, so comparing
    # optimizers along *different* random directions would confound the two.
    gen = torch.Generator(device=DEVICE).manual_seed(0)
    profile = loss_profile(model, loader, criterion, filter_normalized_direction(model, gen))

    return dict(kind=ckpt.get("kind", os.path.basename(path)),
                acc=ckpt.get("test_acc"), base=base, sharp=sharp, profile=profile)

def maybe_plot(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for r in results:
        ax.plot(ALPHAS, r["profile"], marker="o", label=r["kind"])
    ax.set(xlabel="alpha (filter-normalized direction)", ylabel="test loss",
           title="Loss landscape around each minimum")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("sharpness.png", dpi=120)
    print("saved sharpness.png")

def main(paths):
    criterion = nn.CrossEntropyLoss()
    loader = get_eval_loader()
    print(f"device={DEVICE} | eval on {EVAL_BATCHES} batches | rho={RHO} "
          f"| {ASCENT_STEPS} ascent steps")
    results = [analyze(p, loader, criterion) for p in paths]
    results.sort(key=lambda r: r["sharp"])
    print(f"\n{'optimizer':<16}{'test_acc':>10}{'loss':>9}{'sharpness':>12}{'rise@a=1':>11}")
    for r in results:
        rise = r["profile"][-1] - r["profile"][len(ALPHAS) // 2]
        acc = f"{r['acc']:.2f}%" if r["acc"] is not None else "-"
        print(f"{r['kind']:<16}{acc:>10}{r['base']:>9.4f}{r['sharp']:>12.4f}{rise:>11.4f}")
    print("\nLower sharpness = flatter minimum. Compare against test_acc: the claim this "
          "file exists to test is that they move together.")
    maybe_plot(results)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])