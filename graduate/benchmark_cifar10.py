"""CIFAR-10 benchmark: AdamW vs SAM vs Muon vs MuonSAM on a CIFAR-adapted ResNet-18.

  Measures two things the proposal cares about:
    - convergence speed: train loss per epoch AND wall-clock time
    - generalization:     test accuracy

  Fairness: identical weight init and identical batch order across all optimizers.

  Caveats (read before trusting numbers):
    1. Hyperparameters below are NOT tuned. A fair optimizer comparison REQUIRES
       per-optimizer LR/rho tuning; defaults can mislead. Treat QUICK runs as a
       harness check, not a verdict.
    2. SAM-type optimizers run 2 forward-backward passes/step, so BN running stats
       update twice on SAM steps (the disable_running_stats refinement is omitted
       for simplicity; it affects SAM and MuonSAM equally, so the comparison stays
       internally consistent).
    3. CPU auto-selects a small QUICK config. Real CIFAR-10 numbers need a GPU run
       (set QUICK=False).
"""
import time
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as T
from torch.utils.data import DataLoader, Subset

from sam import SAM
from muon import SingleDeviceMuonWithAuxAdam
from muon_sam import MuonSAM

# ---------------- config ----------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
QUICK = (DEVICE == "cpu")              # CPU -> fast sanity run; GPU -> full run
EPOCHS = 3 if QUICK else 50
TRAIN_SUBSET = 2000 if QUICK else None  # None = full 50k
TEST_SUBSET  = 1000 if QUICK else None
BATCH = 128
SEED = 0
KINDS = ["adamw", "sam", "muon", "muonsam"]

def make_resnet18():
    """torchvision ResNet-18 adapted for 32x32 CIFAR (3x3 stem, no maxpool)."""
    m = torchvision.models.resnet18(num_classes=10)
    m.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    m.maxpool = nn.Identity()
    return m

def split_params(model):
    """Hidden weights with ndim>=2 (conv) -> Muon; head (fc) + all 1D (BN/bias) -> Adam."""
    muon, aux = [], []
    for name, p in model.named_parameters():
        if p.ndim >= 2 and "fc" not in name:
            muon.append(p)
        else: aux.append(p)
    return muon, aux

def build_optimizer(kind, model, total_steps):
    muon, aux = split_params(model)
    if kind == "adamw":
        return torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=5e-4)
    if kind == "sam":
        return SAM(model.parameters(), torch.optim.SGD,
                   rho=0.05, lr=0.05, momentum=0.9, weight_decay=5e-4)
    if kind == "muon":
        groups = [
            dict(params=muon, use_muon=True, lr=0.02, weight_decay=5e-4),
            dict(params=aux, use_muon=False, lr=1e-3, weight_decay=5e-4)
        ]
        return SingleDeviceMuonWithAuxAdam(groups)
    if kind == "muonsam":
        groups = [
            dict(params=muon, use_muon=True, lr=0.02, rho=0.05, weight_decay=5e-4),
            dict(params=aux, use_muon=False, lr=1e-3, rho=0.01, weight_decay=5e-4)
        ]
        return MuonSAM(groups, total_steps=total_steps, rho_max=0.05, rho_warmup_frac=0.3, sam_period=5)
    raise ValueError(kind)

def train_epoch(kind, model, opt, loader, criterion):
    model.train()
    total, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        if kind in ("adamw", "muon"):
            opt.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            opt.step()
        elif kind == "sam":
            loss = criterion(model(x), y)       # 1st pass @ w
            loss.backward()
            opt.first_step(zero_grad=True)
            criterion(model(x), y).backward()   # 2nd pass @ w+e
            opt.second_step(zero_grad=True)
        elif kind == "muonsam":
            def closure():
                opt.zero_grad()
                l = criterion(model(x), y)
                l.backward()
                return l
            loss = opt.step(closure)
        total += loss.item() * x.size(0)
        n += x.size(0)
    return total / n

@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    correct, n = 0, 0
    for x, y in loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        correct += (model(x).argmax(1) == y).sum().item()
        n += x.size(0)
    return correct / n

def get_loaders(train_g):
    mean, std = (0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)
    train_tf = T.Compose([T.RandomCrop(32, padding=4), T.RandomHorizontalFlip(),
                          T.ToTensor(), T.Normalize(mean, std)])
    test_tf = T.Compose([T.ToTensor(), T.Normalize(mean, std)])
    train = torchvision.datasets.CIFAR10("./data", train=True, download=True, transform=train_tf)
    test = torchvision.datasets.CIFAR10("./data", train=False, download=True, transform=test_tf)
    if TRAIN_SUBSET: train = Subset(train, range(TRAIN_SUBSET))
    if TEST_SUBSET: test = Subset(test, range(TEST_SUBSET))
    train_loader = DataLoader(train, BATCH, shuffle=True, generator=train_g, num_workers=2)
    test_loader = DataLoader(test, BATCH, shuffle=False, num_workers=2)
    return train_loader, test_loader

def maybe_plot(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError: return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for kind, hist in results.items():
        eps = [h[0] for h in  hist]
        accs = [h[2] * 100 for h in hist]
        ts = [h[3] for h in hist]
        axes[0].plot(eps, accs, marker="o", label=kind)
        axes[1].plot(ts, accs, marker="o", label=kind)
    axes[0].set(xlabel="epoch", ylabel="test acc (%)", title="acc vs epoch")
    axes[1].set(xlabel="wall-clock (s)", ylabel="test acc (%)", title="acc vs compute budget")
    for ax in axes:
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("benchmark.png", dpi=120)
    print("saved benchmark.png")

def main():
    print(f"device={DEVICE} | QUICK={QUICK} | epochs={EPOCHS} "
          f"| train_subset={TRAIN_SUBSET} | test_subset={TEST_SUBSET}")
    train_g = torch.Generator().manual_seed(SEED)
    train_loader, test_loader = get_loaders(train_g)
    total_steps = len(train_loader) * EPOCHS
    criterion = nn.CrossEntropyLoss()

    results = {}
    for kind in KINDS:
        torch.manual_seed(SEED)          # identical weight init
        train_g.manual_seed(SEED)        # identical batch order
        model = make_resnet18().to(DEVICE)
        opt = build_optimizer(kind, model, total_steps)
        print(f"\n=== {kind} ===")
        hist, t0 = [], time.time()
        for ep in range(1, EPOCHS + 1):
            tr = train_epoch(kind, model, opt, train_loader, criterion)
            acc = evaluate(model, test_loader)
            elapsed = time.time() - t0
            hist.append((ep, tr, acc, elapsed))
            print(f"  epoch {ep}: train_loss={tr:.4f} test_acc={acc * 100:.2f}% time={elapsed:.1f}s")
        results[kind] = hist

    print("\n==== final summary ====")
    print(f"{'optimizer':<10}{'test_acc':>10}{'time(s)':>10}")
    for kind, hist in results.items():
        _, _, acc, t = hist[-1]
        print(f"{kind:<10}{acc * 100:>9.2f}%{t:>10.1f}")
    maybe_plot(results)

if __name__ == "__main__":
    main()