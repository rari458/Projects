"""CIFAR-10/100 benchmark: AdamW vs SAM vs Muon vs MuonSAM on a CIFAR-adapted ResNet-18.

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
    3. CPU auto-selects a small QUICK config. Real CIFAR-10/100 numbers need a GPU run
       (set QUICK=False).
"""
import time
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as T
import os
from torch.utils.data import DataLoader, Subset

from sam import SAM
from muon import SingleDeviceMuonWithAuxAdam
from muon_sam import MuonSAM

# ---------------- config ----------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# QUICK silently shrinks the run to 3 epochs / 2k samples. That is the right default for
# local CPU debugging, but on a cloud CPU session it yields a runlog.csv that looks valid
# while being incomparable to every GPU run. REQUIRE_GPU=1 turns the fallback into a hard
# failure so a misconfigured Kaggle/Colab session fails instead of producing junk.
if os.environ.get("REQUIRE_GPU") == "1" and DEVICE != "cuda":
    raise RuntimeError(f"REQUIRE_GPU=1 but torch reports no CUDA (torch {torch.__version__})")
QUICK = (DEVICE == "cpu")              # CPU -> fast sanity run; GPU -> full run
EPOCHS = 3 if QUICK else 50
TRAIN_SUBSET = 2000 if QUICK else None  # None = full 50k
TEST_SUBSET  = 1000 if QUICK else None
BATCH = 128
SEED = 0
# The dataset is a config axis like KINDS and the LRs. The five facts that must move
# together -- the torchvision class, the head width, the input resolution, the constructor's
# split convention, and the normalization stats -- arevbound in one record on purpose: 
# picking CIFAR-100 with CIFAR-10's statistics trains normally and only costs accuracy, 
# which is the silent-config failure preflight.py exists for. A record no one can half-set 
# is a cheaper guard than a check. Note `px` is this harness's input resolution and is NOT
# Imagenette's `size=` kwarg, which selects an archive variant == hence the separate names.
DATASETS = {
    "cifar10": dict(
        cls=torchvision.datasets.CIFAR10, classes=10, px=32, resize=False,
        class_sorted=False, train_kw=dict(train=True), test_kw=dict(train=False),
        mean=(0.4914, 0.4822, 0.4465), std=(0.2470, 0.2435, 0.2616)
    ),
    "cifar100": dict(
        cls=torchvision.datasets.CIFAR100, classes=100, px=32, resize=False,
        class_sorted=False, train_kw=dict(train=True), test_kw=dict(train=False),
        mean=(0.5071, 0.4865, 0.4409), std=(0.2673, 0.2564, 0.2762)
    ),
    # 10 ImageNet classes, 9469 train / 3925 val, variable-size JPEGs. This is the honest
    # substitute for the proposal's ImageNet rung on a machine with no lab GPU: report it as
    # Imagenette at 64x64, never as ImageNet. Normalization is ImageNet's published mean/std
    # rather than a measured one, which is correct here because Imagenette is a subset of
    # ImageNet -- and it keeps the number citable instead of resting on our own arithmetic.
    "imagenette": dict(
        cls=torchvision.datasets.Imagenette, classes=10, px=64, resize=True,
        class_sorted=True, train_kw=dict(split="train", size="160px"),
        test_kw=dict(split="val", size="160px"),
        mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
    ),
}
DATASET = os.environ.get("DATASET", "cifar10")
if DATASET not in DATASETS:
    raise ValueError(f"DATASET={DATASET!r}, expected one of {sorted(DATASETS)}")
# Per-optimizer learning rates, module-level so a notebook can sweep them the same way it
# overrides KINDS / SEED / LOGFILE. build_optimizer used to hardcode these, which made the
# LR the one config axis this harness could not vary -- and untuned baselines are the
# largest standing objection to the reported MuonSAM-vs-Muon gap.
LR_ADAMW = 1e-3        # adamw, all parameters
LR_SAM = 0.05          # sam's inner SGD
LR_MUON = 0.02         # Muon group (conv weights); every muon* / muonsam* variant
LR_AUX = 1e-3          # aux Adam group (fc + BN + biases); held fixed during an LR sweep
WEIGHT_DECAY = 5e-4
RHO_MAX = 0.05         # MuonSAM's peak rho, Muon group; also the per-group rho default
RHO_AUX = 0.01         # aux group's Euclidean rho
# The six the reported CIFAR-10 results were produced with. build_optimizer also knows
# muonsam_gsam / muonsam_asam / muonsam_nowarm; they are left out of the default run
# because six kinds already cost ~7h on a T4. Select them by overriding B.KINDS.
KINDS = ["adamw", "sam", "muon", "muon_nomom", "muonsam_nomom", "muonsam"]
# Every MuonSAM-backed variant, including the ones not in KINDS above: these take a
# closure instead of a plain step(). A kind listed here but not in KINDS simply does not
# run; a kind in KINDS but missing here falls through train_epoch's dispatch to an
# undefined `loss`, so add new variants to BOTH.
CLOSURE_KINDS = ("muonsam", "muonsam_nomom", "muon_nomom", "muonsam_gsam", "muonsam_asam", "muonsam_nowarm")
# Final weights per optimizer, for sharpness.py. ~45MB each; SAVE_CKPT=0 turns it off.
SAVE_CKPT = os.environ.get("SAVE_CKPT", "1") != "0"
# Artifacts land in OUTDIR, not the cwd. On Kaggle the repo is usually cloned somewhere
# outside /kaggle/working and the notebook cd's into it, so a relative path silently
# writes the results where nothing collects them. Pass OUTDIR=/kaggle/working there.
OUTDIR = os.environ.get("OUTDIR", ".")
os.makedirs(OUTDIR, exist_ok=True)
LOGFILE = os.path.join(OUTDIR, "runlog.csv")

def make_resnet18():
    """torchvision ResNet-18 adapted for 32x32 CIFAR (3x3 stem, no maxpool)."""
    m = torchvision.models.resnet18(num_classes=DATASETS[DATASET]["classes"])
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

def primary_lr(kind):
    """The LR that identifies an arm in the runlog.

    A sweep runs the same `kind` several times, so without this column three rows of the
    CSV are indistinguishable and the sweep cannot be read back. The aux LR is deliberately
    not recorded: it is held fixed, and recording a constant invites the reader to think it
    was varied.
    """
    if kind == "adamw":
        return LR_ADAMW
    if kind == "sam":
        return LR_SAM
    return LR_MUON

def build_optimizer(kind, model, total_steps):
    muon, aux = split_params(model)
    if kind == "adamw":
        return torch.optim.AdamW(model.parameters(), lr=LR_ADAMW, weight_decay=WEIGHT_DECAY)
    if kind == "sam":
        return SAM(model.parameters(), torch.optim.SGD,
                   rho=0.05, lr=LR_SAM, momentum=0.9, weight_decay=WEIGHT_DECAY)
    if kind == "muon":
        groups = [
            dict(params=muon, use_muon=True, lr=LR_MUON, weight_decay=WEIGHT_DECAY),
            dict(params=aux, use_muon=False, lr=LR_AUX, weight_decay=WEIGHT_DECAY)
        ]
        return SingleDeviceMuonWithAuxAdam(groups)
    if kind == "muon_nomom":
        # Fourth cell of the momentum x SAM ablation ; the other three are muon /
        # muonsam_nomom / muonsam. rho_warmup_frac=1.0 pins _rho_scale() to 0 for the whole
        # run, so the SAM branch never fired and no LookSAM correction is ever stored --
        # with momentum_mode="none" that reduces to Muon with its momentum buffer disabled.
        groups = [
            dict(params=muon, use_muon=True, lr=LR_MUON, weight_decay=WEIGHT_DECAY),
            dict(params=aux, use_muon=False, lr=LR_AUX, weight_decay=WEIGHT_DECAY)
        ]
        return MuonSAM(groups, total_steps=total_steps, rho_max=0.0, rho_warmup_frac=1.0,  momentum_mode="none")

    if kind.startswith("muonsam"):
        # Config axes, not separate code paths. Each variant below overrides one keyword
        # of the default and nothing else, which is what the proposal means by "the
        # combination axes are config dimensions, not hardcoded strategies".
        mode = "none" if kind.endswith("_nomom") else "pre_ns5"
        adaptive = kind.endswith("_asam")     # ASAM scale-invariant perturbation, both groups
        opts = dict(rho_max=RHO_MAX, rho_warmup_frac=0.3, sam_period=5, momentum_mode=mode)
        if kind.endswith("_gsam"):
            opts["correction_mode"] = "gsam"  # 2203.08065 instead of LookSAM's projection
        if kind.endswith("_nowarm"):
            # The ablation 2509.21818 asks for: that paper shows SAM can converge to
            # "hallucinated minimizers" and that a warm-start before enabling SAM is the
            # safeguard. rho_warmup_frac=0.3 was chosen for speed; this measures whether
            # it is also doing the job the paper predicts.
            opts["rho_warmup_frac"] = 0.0
        groups = [
            dict(params=muon, use_muon=True, lr=LR_MUON, rho=RHO_MAX, weight_decay=WEIGHT_DECAY, adaptive=adaptive),
            dict(params=aux, use_muon=False, lr=LR_AUX, rho=RHO_AUX, weight_decay=WEIGHT_DECAY, adaptive=adaptive)
        ]
        return MuonSAM(groups, total_steps=total_steps, **opts)
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
        elif kind in CLOSURE_KINDS:
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

def subset_indices(ds, n, spec):
    """The first n samples, except where that would be a class-ordered slice.
    ImageFolder-style sets are stored sorted by class directory, so range(2000) of a
    9469-image 10-class Imagenette is {963, 955, 82} over three classes: the run trains,
    converges, and reports a low loss and a high accuracy for a problem it was never
    given. CIFAR's archives are already shuffled, so range(n) is kept there and every
    reported CIFAR number stays byte-identical. The permutation seed is fixed at 0 rather
    than SEED because the subset must be the same sample of the data in every arm and
    every seed -- it selects the measurement, not the experiment.
    """
    if not spec["class_sorted"]:
        return range(n)
    return torch.randperm(len(ds), generator=torch.Generator().manual_seed(0))[:n].tolist()

def get_loaders(train_g):
    spec = DATASETS[DATASET]
    px, norm = spec["px"], T.Normalize(spec["mean"], spec["std"])
    if spec["resize"]:
        # Variable-size JPEGs: the scale-crop is both the resize and the augmentation.
        # scale=(0.35, 1.0) rather than RandomResizedCrop's (0.08, 1.0) default, which is
        # tuned for 1.2M images and is too aggressive for 9.5k over 50 epochs.
        train_pre = [T.RandomResizedCrop(px, scale=(0.35, 1.0)), T.RandomHorizontalFlip()]
        test_pre = [T.Resize(px * 8 // 7), T.CenterCrop(px)]
    else:
        # CIFAR is already px x px. This pair is byte-identical to what every reported
        # CIFAR-10 and CIFAR-100 number was produced with -- do not "unify" it with the
        # branch above, or the records in results/ stop being reproducible.
        train_pre = [T.RandomCrop(px, padding=4), T.RandomHorizontalFlip()]
        test_pre = []
    train_tf = T.Compose(train_pre + [T.ToTensor(), norm])
    test_tf = T.Compose(test_pre + [T.ToTensor(), norm])
    train = spec["cls"]("./data", download=True, transform=train_tf, **spec["train_kw"])
    test = spec["cls"]("./data", download=True, transform=test_tf, **spec["test_kw"])
    if TRAIN_SUBSET: train = Subset(train, subset_indices(train, TRAIN_SUBSET, spec))
    if TEST_SUBSET: test = Subset(test, subset_indices(test, TEST_SUBSET, spec))
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
    png = os.path.join(OUTDIR, "benchmark.png")
    fig.savefig(png, dpi=120)
    print(f"saved {png}")

def main():
    print(f"device={DEVICE} | QUICK={QUICK} | epochs={EPOCHS} "
          f"| train_subset={TRAIN_SUBSET} | test_subset={TEST_SUBSET}")
    train_g = torch.Generator().manual_seed(SEED)
    train_loader, test_loader = get_loaders(train_g)
    # preflight can check the DATASETS record, but not that get_loaders actually read it:
    # a stale second definition of get_loaders shadows the new one and trains a healthy,
    # plausible, wrong experiment. The loader object is where the choice becomes real, so
    # assert on that.
    base = train_loader.dataset
    base = base.dataset if isinstance(base, Subset) else base
    assert type(base) is DATASETS[DATASET]["cls"], f"DATASET={DATASET} but the loader holds {type(base).__name__}"
    # Same reasoning one level down: the record can say px=64 while the transform that
    # actually resizes sits in the other branch. Only a real batch settles it. Safe to
    # consume one here -- train_g is re-seeded per optimizer before each run below.
    got = next(iter(train_loader))[0].shape[-1]
    assert got == DATASETS[DATASET]["px"], f"loader yields {got}x{got}, {DATASET} record says px={DATASETS[DATASET]['px']}"
    total_steps = len(train_loader) * EPOCHS
    criterion = nn.CrossEntropyLoss()

    log = open(LOGFILE, "w", newline="")
    # analyze.py:47 keeps '#' lines as notes and prints them, so provenance rides with the
    # numbers instead of living in a filename someone has to trust. The column layout is
    # unchanged -- benchmark_tf.py writes the same six.
    log.write(
        f"# dataset={DATASET} px={DATASETS[DATASET]['px']} epochs={EPOCHS} seed={SEED} batch={BATCH} "
        f"wd={WEIGHT_DECAY} rho_max={RHO_MAX} rho_aux={RHO_AUX} "
        f"torch={torch.__version__}\n"
    )
    log.write("optimizer,epoch,train_loss,test_acc,time_s,lr\n")

    results = {}
    for kind in KINDS:
        torch.manual_seed(SEED)          # identical weight init
        train_g.manual_seed(SEED)        # identical batch order
        model = make_resnet18().to(DEVICE)
        opt = build_optimizer(kind, model, total_steps)
        lr = primary_lr(kind)
        print(f"\n=== {kind} (lr={lr}) ===")
        hist, t0 = [], time.time()
        for ep in range(1, EPOCHS + 1):
            tr = train_epoch(kind, model, opt, train_loader, criterion)
            acc = evaluate(model, test_loader)
            elapsed = time.time() - t0
            hist.append((ep, tr, acc, elapsed))
            print(f"  epoch {ep}: train_loss={tr:.4f} test_acc={acc * 100:.2f}% time={elapsed:.1f}s")
            log.write(f"{kind},{ep},{tr:.4f},{acc * 100:.2f},{elapsed:.1f},{lr}\n")
            log.flush()
        results[kind] = hist
        if SAVE_CKPT:
            # sharpness.py reads these. Saved per kind rather than per epoch: the claim
            # under test is about the minimum each optimizer converges to.
            ckpt = os.path.join(OUTDIR, f"ckpt_{kind}_seed{SEED}.pt")
            torch.save(dict(kind=kind, seed=SEED, epoch=EPOCHS, test_acc=acc * 100,
                            state_dict=model.state_dict()), ckpt)
            print(f"  saved {ckpt}")
        if DEVICE == "cuda":
            # The optimizer-state ratios are exact and device-independent; this is the part
            # that is not -- activations dominate, so the end-to-end cost of MuonSAM's
            # extra state can only be read off a real GPU run.
            print(f"  peak GPU mem: {torch.cuda.max_memory_allocated() / 1024**2:.0f} MB")
            torch.cuda.reset_peak_memory_stats()

    log.close()
    print(f"\nsaved {LOGFILE}")

    print("\n==== final summary ====")
    print(f"{'optimizer':<10}{'test_acc':>10}{'time(s)':>10}")
    for kind, hist in results.items():
        _, _, acc, t = hist[-1]
        print(f"{kind:<10}{acc * 100:>9.2f}%{t:>10.1f}")
    maybe_plot(results)

if __name__ == "__main__":
    main()