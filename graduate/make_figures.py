"""Report figures from the v2 rerun campaign.

The advisor returned the final report asking for the results as graphs -- explicitly
"training step vs training/test loss, accuracy" -- so that family is built first and the
analysis figures (paired differences, the 2x2, cost and memory bars) follow.

Reads results/v2 only. Mixing a v1 and a v2 file on one axis is what the split exists to
prevent, and epoch is the only x-axis that aligns across sessions -- wall-clock does not,
so nothing here puts time from two seeds on one axis.

Loss panels are linear. The log-axis warning on record came from the CPU QUICK path, where
sam opens at 125.74 with lr=0.05 over 2k images; across the 50-epoch runs the widest test
loss range is 3.53 and a log axis would only flatten the late-epoch separation these figures
exist to show.

Labels are English on purpose: this machine has no Korean fonts, so matplotlib renders
Korean as empty boxes. Captions are written in Word, where the fonts exist.

    python make_figures.py            # every dataset
    python make_figures.py c100 c10   # a subset
"""
import csv
import glob
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")       # headless here, and headless on Kaggle too
import matplotlib.pyplot as plt

# Everything is drawn at final print scale rather than shrunk into place. Word fits an
# oversized image to the column, so a 15-inch figure lands at 0.45x and its 7pt labels come
# out at 3.1pt -- unreadable on paper while looking fine on screen, which is the worst shape
# a defect can take in the one artifact the advisor actually asked for. TW is the report's
# text width (9638 twips), so the scale is 1.0 and every point size below is the point size
# on the page.
TW = 6.69
plt.rcParams.update({
    "font.size": 7,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5,
    "figure.titlesize": 8.5,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "grid.linewidth": 0.4,
})
# Curve width and its increment along ORDER; see _plot for why the increment exists at all.
LW0, LWD = 0.9, 0.13

from analyze import load, last_n, last_n_loss    # one runlog reader for the project, not two

V2 = "results/v2"
OUT = os.path.join(V2, "figs")

DATASETS = {"inette": "Imagenette 64x64", "c100": "CIFAR-100", "c10": "CIFAR-10"}

# One colour per arm across every figure, so a reader who learns the legend once keeps it.
COLOR = {
    "muonsam": "#d62728",
    "muon": "#1f77b4",
    "adamw": "#2ca02c",
    "sam": "#ff7f0e",
    "muonsam_nomom": "#9467bd",
    "muon_nomom": "#8c564b",
}
# Legend order, not a ranking: the contribution, its baseline, the two ablation cells, then
# the two external baselines. Arms absent from a dataset are skipped silently.
ORDER = ["muonsam", "muon", "muonsam_nomom", "muon_nomom", "adamw", "sam"]

def _files(kind, tag):
    return sorted(glob.glob(os.path.join(V2, f"{kind}_{tag}_seed*.csv")))

def _agg(per_x):
    """{x: [v, ...]} -> (xs, means, sds); sd is 0.0 where only one seed contributed."""
    xs = sorted(per_x)
    return (
        xs, [statistics.mean(per_x[x]) for x in xs],
        [statistics.stdev(per_x[x]) if len(per_x[x]) > 1 else 0.0 for x in xs]
    )

def epoch_curves(tag):
    """{arm: {metric: (xs, mean, sd)}} pooled over however many seeds are present."""
    # hist tuples are indexed rather than unpacked: load() gained train_loss as a fifth
    # slot on 2026-09-09 and may gain a sixth.
    slots = {"test_acc": 1, "test_loss": 3, "train_loss": 4}
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    files = _files("runlog", tag)
    for path in files:
        arms, _ = load(path)
        for arm, hist in arms.items():
            for h in hist:
                for metric, i in slots.items():
                    if h[i] is not None:
                        acc[arm][metric][h[0]].append(h[i])
    return {a: {m: _agg(px) for m, px in ms.items()} for a, ms in acc.items()}, len(files)

def step_curves(tag):
    """{arm: (steps, mean, sd)} from steplog -- train_loss only, since the step log holds no
    eval, and that train_loss is a STEP_EVERY-batch window mean rather than the runlog's
    epoch mean. The two must not share an axis without a caption saying so."""
    acc = defaultdict(lambda: defaultdict(list))
    files = _files("steplog", tag)
    for path in files:
        with open(path, newline="") as f:
            body = [ln for ln in f if not ln.startswith("#")]
        for r in csv.DictReader(body):
            acc[r["optimizer"]][int(r["step"])].append(float(r["train_loss"]))
    return {a: _agg(px) for a, px in acc.items()}, len(files)

def _plot(ax, arm, xs, mean, sd, n):
    """ORDER is the legend order, and matplotlib makes it the paint order too -- so muonsam,
    drawn first, disappears under muon wherever the two coincide, which on the train-loss
    panels is nearly everywhere. zorder decouples the two: the legend keeps ORDER while the
    ink keeps priority, and every band sits under every line."""
    c = COLOR.get(arm, "#777777")
    # Width decreases along ORDER for the same reason zorder increases: where two arms
    # coincide -- muonsam and muon do so almost exactly on the train-loss panels -- the one
    # underneath still shows as a halo instead of vanishing, so the coincidence reads as a
    # finding rather than as a missing curve.
    i = ORDER.index(arm) if arm in ORDER else len(ORDER)
    ax.plot(xs, mean, color=c, lw=LW0 + LWD * i, label=arm, zorder=10 - i)
    if n > 1 and any(sd):
        ax.fill_between(
            xs, [m - s for m, s in zip(mean, sd)],
            [m + s for m, s in zip(mean, sd)], color=c, alpha=0.15, lw=0, zorder=1
        )

def _finish(fig, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, dpi=400)
    plt.close(fig)
    print(f"  wrote {path}")
    
def _legend(axes, **kw):
    """Legend gathered from every panel, not just the first. CIFAR-10 runs six arms and the
    other two datasets four, so a legend built from panel 0 leaves muon_nomom and
    muonsam_nomom as unlabelled curves on the one panel that has them. It goes on the
    fullest panel, re-sorted into ORDER since the union is collected left to right."""
    seen = {}
    for ax in axes:
        for h, l in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(l, h)
    fullest = max(axes, key=lambda a: len(a.get_legend_handles_labels()[1]))
    labels = sorted(seen, key=lambda l: ORDER.index(l) if l in ORDER else len(ORDER))
    fullest.legend([seen[l] for l in labels], labels, **kw)

def fig_curves(tag):
    curves, n = epoch_curves(tag)
    if not curves:
        print(f"  skip {tag}: no runlog in {V2}")
        return
    panels = [
        ("train_loss", "train loss (epoch mean)"),
        ("test_loss", "test loss (full test set)"),
        ("test_acc", "test accuracy (%)")
    ]
    fig, axes = plt.subplots(1, 3, figsize=(TW, 2.6))
    for ax, (metric, ylab) in zip(axes, panels):
        for arm in ORDER:
            if arm in curves and metric in curves[arm]:
                _plot(ax, arm, *curves[arm][metric], n)
        ax.set_xlabel("epoch")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.3)
    axes[0].legend()
    seeds = f"mean of {n} seeds, band +/-1 sd" if n > 1 else "1 seed"
    fig.suptitle(f"{DATASETS[tag]} -- {seeds}")
    _finish(fig, f"fig01_curves_{tag}.png")
    
def fig_steps(tags):
    have = [(t, c, n) for t, c, n in ((t, *step_curves(t)) for t in tags) if c]
    if not have:
        print("  skip step figure: no steplog files")
        return
    fig, axes = plt.subplots(1, len(have), figsize=(TW, 2.9), squeeze=False)
    for ax, (tag, curves, n) in zip(axes[0], have):
        for arm in ORDER:
            if arm in curves:
                _plot(ax, arm, *curves[arm], n)
        ax.set_xlabel("training step")
        ax.set_ylabel("train loss (50-batch window mean)")
        ax.set_title(f"{DATASETS[tag]} ({n} seed{'s' if n > 1 else ''})")
        # A second x-axis in epochs, because the panels are not comparable without it: 50
        # epochs is 3700 steps on Imagenette and 19550 on CIFAR, and the sawtooth below has
        # a period of exactly one epoch, which is unreadable on a step axis alone.
        spe = max(max(c[0]) for c in curves.values()) / 50
        sec = ax.secondary_xaxis("top", functions=(lambda s, k=spe: s / k, lambda e, k=spe: e * k))
        sec.set_xlabel("epoch")
        ax.grid(alpha=0.3)
    _legend(axes[0])
    _finish(fig, "fig02_step_trainloss.png")

def fig_equal_compute(tags):
    """Accuracy against wall-clock, with each baseline's total time as a vertical line.
    
    Wall-clock is comparable only inside one session, so this reads seed 0 alone and says so
    in the title. Averaging time across seeds would put two hosts on one axis, which is the
    one thing the campaign's own rule forbids.
    """
    rows = [
        (t, load(os.path.join(V2, f"runlog_{t}_seed0.csv"))[0]) for t in tags
        if os.path.exists(os.path.join(V2, f"runlog_{t}_seed0.csv"))
    ]
    if not rows:
        print("  skip equal-compute figure: no seed-0 runlogs")
        return
    fig, axes = plt.subplots(1, len(rows), figsize=(TW, 2.7), squeeze=False)
    for ax, (tag, arms) in zip(axes[0], rows):
        floor = min(h[-1][1] for h in arms.values()) - 12
        for arm in ORDER:
            if arm not in arms: continue
            i, h = ORDER.index(arm), arms[arm]
            ax.plot(
                [r[2] / 3600 for r in h], [r[1] for r in h], color=COLOR[arm],
                lw=LW0 + LWD * i, label=arm, zorder=10 - i
            )
        # The budget lines are what make this the equal-compute figure rather than a second
        # accuracy plot: everything to the left of a baseline's line was bought with compute
        # that baseline also had.
        for base in ("muon", "adamw"):
            if base in arms:
                ax.axvline(arms[base][-1][2] / 3600, color=COLOR[base], ls="--", lw=0.8, alpha=0.8, zorder=2)
        ax.set_xlabel("wall-clock (hours)")
        ax.set_ylabel("test accuracy (%)")
        ax.set_ylim(bottom=floor)
        ax.set_title(DATASETS[tag])
        ax.grid(alpha=0.3)
    _legend(axes[0], loc="lower right", fontsize=5.5)
    fig.suptitle(
        "seed 0 only -- wall-clock is comparable only within one session; "
        "dashed = each baseline's own total"
    )
    _finish(fig, "fig03_equal_compute.png")

def fig_paired(tags):
    """Paired last-10 differences, one dot per seed, bar at the mean.
    
    Paired rather than marginal because the seed moves both arms together and the pairing
    cancels it -- which is exactly what identical weight init and identical batch order buy.
    """
    pairs = [("muonsam", "muon"), ("sam", "adamw")]
    marks = {"muonsam": "o", "sam": "s"}
    fig, ax = plt.subplots(figsize=(TW, 3.4))
    seen = set()
    for x, tag in enumerate(tags):
        for k, (a, b) in enumerate(pairs):
            vals = []
            for path in _files("runlog", tag):
                arms, _ = load(path)
                if a in arms and b in arms:
                    vals.append(last_n(arms[a], 10)[0] - last_n(arms[b], 10)[0])
            if not vals: continue
            off, c = -0.14 + 0.28 * k, COLOR[a]
            label = f"{a} - {b}" if a not in seen else None
            seen.add(a)
            ax.scatter([x + off] * len(vals), vals, s=16, color=c, marker=marks[a], zorder=3, label=label)
            m = statistics.mean(vals)
            ax.plot([x + off - 0.09, x + off + 0.09], [m, m], color=c, lw=1.8, zorder=4)
    ax.axhline(0, color="#444444", lw=0.7, zorder=1)
    ax.set_xticks(range(len(tags)))
    ax.set_xticklabels([DATASETS[t] for t in tags])
    ax.set_ylabel("last-10 accuracy difference (pp)")
    ax.set_title("Paired differences, one dot per seed, bar at the mean")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    _finish(fig, "fig04_paired_diffs.png")

def _sharpness(tag):
    """{arm: [sharpness per seed]} from the sharpness .txt files.
    
    Those are console tables rather than CSVs -- a header row, the arm rows, then a blank
    line and two lines of prose -- so rows are taken positionally after the header and the
    parse stops at the first line that is not five fields. Only the sharpness column is
    read: CIFAR-100 seed 1 was measured on CPU and adaptive_sharpness is device-independent,
    while rise@a=1 from the same file is not, so pooling that column would be wrong.
    """
    out = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(V2, f"sharpness_{tag}_seed*.txt"))):
        with open(path) as f:
            lines = f.read().splitlines()
        head = [i for i, ln in enumerate(lines) if ln.split()[:1] == ["optimizer"]]
        if not head: continue
        for ln in lines[head[0] + 1:]:
            parts = ln.split()
            if len(parts) != 5: break
            out[parts[0]].append(float(parts[3]))
    return out

def _summary(tag, field):
    """[{arm: value}, ...], one dict per seed. Per-file rather than pooled because a cost
    ratio has to be formed inside one session before it is averaged -- wall-clock is
    comparable only within a session, which is the rule analyze.py enforces structurally."""
    rows = []
    for path in _files("summary", tag):
        with open(path, newline="") as f:
            rows.append({r["optimizer"]: float(r[field]) for r in csv.DictReader(f)})
    return rows

# The 2x2 ablation as (momentum, sam) -> arm. Both nomom cells are MuonSAM with
# momentum_mode="none"; muon_nomom additionally pins rho_warmup_frac=1.0, which holds the
# rho schedule at 0 for the whole run so its SAM branch never fires.
CELLS = {(0, 0): "muon_nomom", (0, 1): "muonsam_nomom", (1, 0): "muon", (1, 1): "muonsam"}

def fig_ablation(tags):
    """The 2x2 momentum x SAM ablation on three axes at once.
    
    Only a six-arm session has all four cells, and only one has never saved checkpoints for
    the two nomom ones, so the flatness panel is data that did not exist before 2026-09-09.
    The dashed line over the fourth bar is what the two mechanisms would give if they acted
    independently -- accuracy and loss combined additively, sharpness multiplicatively,
    which is how the record states each of them -- and every panel falls short of it.
    
    Accuracy is drawn on truncated axis because the whole effect is 2.8pp on a 91-94 range;
    every bar is annotated with its value so the truncation cannot mislead.
    """
    for tag in tags:
        files = _files("runlog", tag)
        if not files: continue
        acc, loss = defaultdict(list), defaultdict(list)
        for path in files:
            arms, _ = load(path)
            for arm, hist in arms.items():
                acc[arm].append(last_n(hist, 10)[0])
                tl = last_n_loss(hist, 10)
                if tl is not None: loss[arm].append(tl)
        sharp = _sharpness(tag)
        panels = [
            (acc, "last-10 test accuracy (%)", "add", True, "{:.2f}"),
            (sharp, "adaptive sharpness (lower = flatter)", "mul", False, "{:.4f}"),
            (loss, "last-10 test loss (lower is better)", "add", False, "{:.4f}"),
        ]
        if any(not all(a in src for a in CELLS.values()) for src, *_ in panels):
            print(f"  skip 2x2 for {tag}: needs all four arms on all three axes")
            continue
        fig, axes = plt.subplots(1, 3, figsize=(TW, 2.9))
        for ax, (src, ylab, rule, truncate, fmt) in zip(axes, panels):
            means = {c: statistics.mean(src[CELLS[c]]) for c in CELLS}
            sds = {c: statistics.stdev(src[CELLS[c]]) if len(src[CELLS[c]]) > 1 else 0.0 for c in CELLS}
            cells = sorted(CELLS)
            xs = [2 * m + 0.44 * (2 * s - 1) for m, s in cells]
            ax.bar(
                xs, [means[c] for c in cells], width=0.56,
                color=[COLOR[CELLS[c]] for c in cells],
                yerr=[sds[c] for c in cells] if any(sds.values()) else None,
                capsize=2, zorder=3
            )
            for x, c in zip(xs, cells):
                ax.annotate(
                    fmt.format(means[c]), (x, means[c] + sds[c]), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=6, zorder=4
                )
            base, only_s, only_m, both = means[0, 0], means[0, 1], means[1, 0], means[1, 1]
            pred = only_s * only_m / base if rule == "mul" else only_s + only_m - base
            x11 = 2 + 0.44
            ax.plot([x11 - 0.32, x11 + 0.32], [pred, pred], color="#333333", ls="--", lw=1.0, zorder=5)
            lo, hi = min(means.values()), max(max(means.values()), pred)
            if truncate: ax.set_ylim(lo - 0.35 * (hi - lo) - 0.2, hi + 0.22 * (hi - lo))
            else: ax.set_ylim(0, hi * 1.18)
            ax.set_xticks(xs)
            ax.set_xticklabels([f"mom {'on' if c[0] else 'off'}\nSAM {'on' if c[1] else 'off'}" for c in cells], fontsize=6)
            ax.set_ylabel(ylab)
            ax.set_title(f"if independent {fmt.format(pred)}\nmeasured {fmt.format(both)}")
            ax.grid(axis="y", alpha=0.3, zorder=0)
        # The arm names would collide under adjacent bars at 2.2in per panel, so the
        # x axis carries the 2x2 state and one legend carries the names.
        cells = sorted(CELLS)
        axes[0].legend(
            [plt.Rectangle((0, 0), 1, 1, color=COLOR[CELLS[c]]) for c in cells],
            [CELLS[c] for c in cells], loc="upper left", fontsize=5.5,
            handlelength=1.0, handleheight=0.8, borderpad=0.4, labelspacing=0.3
        )
        n = len(files)
        fig.suptitle(f"{DATASETS[tag]} -- momentum x SAM, {n} seed{'s' if n > 1 else ''}; dashed = what independent mechanisms would give")
        _finish(fig, f"fig05_ablation_{tag}.png")

def fig_cost(tags):
    """Wall-clock and peak-memory overhead, each arm against its own baseline.
    
    One mechanism explains both panels and it is report's scalability argument.
    The periodic 2-pass is activation-bound and does not dilute as the input grows;
    the extra NS5 and the LookSAM slots are parameter-bound and do. So MuonSAM's overhead
    falls from +35% at 32x32 to +20% at 64x64 while vanilla SAM's, being a second pass
    every step, stays where it is -- two arms, two predicted behaviours, both visible here.
    
    Every ratio is formed inside one session before being averaged, since wall-clock is
    comparable only within a session.
    """
    pairs = [("muonsam", "muon"), ("sam", "adamw")]
    have = [t for t in tags if _files("summary", t)]
    if not have:
        print("  skip cost figure: no summary files")
        return
    fig, axes = plt.subplots(1, 2, figsize=(TW, 3.0))
    for ax, (field, name) in zip(axes, [("s_per_epoch", "wall-clock per epoch"), ("peak_mem_mb", "peak GPU memory")]):
        tops = []
        for k, (a, b) in enumerate(pairs):
            series = [[100 * (d[a] / d[b] - 1) for d in _summary(t, field) if a in d and b in d] for t in have]
            xs = [i + 0.19 * (2 * k - 1) for i in range(len(have))]
            keep = [(x, v) for x, v in zip(xs, series) if v]
            if not keep: continue
            m = [statistics.mean(v) for _, v in keep]
            sd = [statistics.stdev(v) if len(v) > 1 else 0.0 for _, v in keep]
            ax.bar(
                [x for x, _ in keep], m, width=0.34, color=COLOR[a],
                yerr=sd if any(sd) else None, capsize=2, label=f"{a} over {b}", zorder=3
            )
            for (x, _), y, e in zip(keep, m, sd):
                tops.append(y + e)
                ax.annotate(f"{y:+.1f}%", (x, y + e), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=6, zorder=4)
        ax.axhline(0, color="#444444", lw=0.7, zorder=1)
        ax.set_xticks(range(len(have)))
        ax.set_xticklabels([DATASETS[t] for t in have])
        ax.set_ylabel("overhead over its own baseline (%)")
        ax.set_title(name)
        ax.grid(axis="y", alpha=0.3, zorder=0)
        # Headroom first, then the legend pinned into it. Six bars leave "best" placement
        # nowhere to go, and it put the box on top of a bar on the wall-clock panel.
        if tops: ax.set_ylim(top=max(tops) * 1.24)
        ax.legend(loc="upper center", ncol=2)
    _finish(fig, "fig06_cost_memory.png")

def main():
    bad = [t for t in sys.argv[1:] if t not in DATASETS]
    if bad:
        raise SystemExit(f"unknown dataset(s) {bad}; choose from {list(DATASETS)}")
    tags = sys.argv[1:] or list(DATASETS)
    for tag in tags:
        print(DATASETS[tag])
        fig_curves(tag)
    fig_steps(tags)
    fig_equal_compute(tags)
    fig_paired(tags)
    fig_ablation(tags)
    fig_cost(tags)
    
if __name__ == "__main__":
    main()