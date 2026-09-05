"""Turn the logs in results/ into the numbers the report quotes.

Every figure in the project record was computed by hand, and two of them were wrong in a
way that eyeballing does not catch. The paired difference was given a +/-0.09 error bar --
the spread across seeds only, ignoring that rerunning the same seed moves it ~0.2pp. And
the equal-compute gap was read off a single epoch of a noisy curve, at a threshold that
itself moves between sessions; seed 1's two sessions disagreed by 0.70pp on it. Both are
definition errors, so they are fixed here in code rather than in prose, and the CIFAR-100
table will not have to be re-derived by eye.

Wall-clock is comparable only within one session, so every time-derived quantity is
computed inside a single file. Their *differences* pool across files safely, which is what
the summary at the end does; raw time_s never does.

Usage:
    python analyze.py results/runlog_seed*.csv
    python analyze.py results/runlog_flat_seed2_kaggle.csv --pair muonsam muon
    python analyze.py results/runlog_lrscreen_muon.csv --last 5     # an LR screen
"""
import argparse
import csv
import os
import statistics
from collections import defaultdict

DEFAULT_PAIR = ("muonsam", "muon")

def load(path):
    """One CSV -> {arm: [(epoch, test_acc, time_s, test_loss), ...]}, sorted by epoch.

    Three logs in results/ were hand-assembled rather than written by main() -- transcribed
    from a console log, or annotated afterwards -- and open with a block of `#` lines
    recording device, torch version, and what the arm names actually mean. csv.DictReader
    has no notion of comments and takes the first of those as the header, so they are split
    out here and handed back for printing rather than dropped: runlog_gpu_20260621's block
    is the only record that its "muonsam" is what later runs call "muonsam_nomom", and a tool
    that silently discarded it would invite exactly the misreading it exists to prevent.

    Handles all three runlog layouts: the 5-column one every file written before 2026-08-11
    uses, the 6-column one carrying `lr`, and the 7-column one carrying `test_loss` since
    2026-09. A kind that appears at more than one LR is split into `kind@lr` arms -- an LR
    screen otherwise collapses three separate runs onto one name and reads as a single arm
    with impossible epoch numbers.
    """
    notes, body = [], []
    with open(path, newline="") as f:
        for line in f:
            (notes if line.startswith("#") else body).append(line.rstrip("\n"))

    rows, lrs = defaultdict(list), defaultdict(set)
    for r in csv.DictReader(body):
        kind, lr = r["optimizer"], r.get("lr")
        # test_loss is absent from every file written before 2026-09; None rather than 0.0,
        # so a missing column reads as "not measured" instead of "measured as zero".
        te = float(r["test_loss"]) if r.get("test_loss") else None
        rows[(kind, lr)].append((int(r["epoch"]), float(r["test_acc"]), float(r["time_s"]), te))
        lrs[kind].add(lr)
    arms = {(kind if len(lrs[kind]) == 1 else f"{kind}@{lr}"): sorted(hist) for (kind, lr), hist in rows.items()}
    return arms, notes

def last_n(hist, n):
    accs = [h[1] for h in hist[-n:]]
    return statistics.mean(accs), statistics.stdev(accs) if len(accs) > 1 else 0.0

def last_n_loss(hist, n):
    """Mean test_loss over the tail window, or None if the log predates the column.

    Every file written before 2026-09 has no test_loss, and a window that is only partly
    present is not the mean of anything -- so this returns None rather than averaging
    whatever happens to be there.
    """
    vals = [h[3] for h in hist[-n:]]
    if any(v is None for v in vals): return None
    return statistics.mean(vals)

def at_budget(hist, budget, window):
    """(single-epoch acc, window mean, epoch range) at a wall-clock budget, or None.

    Only epochs that "finished" within the budget count: one that ran past it was bought
    with compute the comparison does not grant. The window mean is the correction to the
    single-epoch reading, which takes one sample off a curve whose epoch-to-epoch jitter is
    ~0.3pp -- two independent sources of noise, one point of measurement.
    """
    within = [(h[0], h[1]) for h in hist if h[2] <= budget]
    if not within: return None
    tail = within[-window:]
    return within[-1][1], statistics.mean(a for _, a in tail), (tail[0][0], tail[-1][0])

def time_to(hist, target):
    """(epoch, wall-clock) of the first epoch reaching `target`, or None.

    The target is the other arm's *final* accuracy, not its best: `best` is itself a max
    over 50 noisy points, which makes the speedup it produces unstable (1.81x +/- 0.56
    against 2.37x +/- 0.41 for this definition).
    """
    for h in hist:
        if h[1] >= target:
            return h[0], h[2]
    return None

def compare(arms, a, b, last, window):
    """Every paired A-vs-B figure for one session. Paired on purpose: the seed moves both
    arms together, and cancelling it is exactly what the harness's identical init and
    identical batch order buy."""
    ah, bh = arms[a], arms[b]
    out = {"final": ah[-1][1] - bh[-1][1], f"last{last}": last_n(ah, last)[0] - last_n(bh, last)[0]}
    # Loss runs the opposite way from accuracy: a NEGATIVE value here is A winning.
    la, lb = last_n_loss(ah, last), last_n_loss(bh, last)
    if la is not None and lb is not None: out[f"loss{last}"] = la - lb
    budget, target = bh[-1][2], bh[-1][1]
    eq = at_budget(ah, budget, window)
    if eq:
        single, mean, span = eq
        out["eq_single"] = single - target
        out[f"eq_mean{window}"] = mean - target
        out["_eq_note"] = f"budget {budget:.0f}s -> ep{span[0]}-{span[1]}"
    hit = time_to(ah, target)
    if hit:
        out["speedup"] = budget / hit[1]
        out["_sp_note"] = f"{hit[1]:.0f}s (ep{hit[0]}) vs {budget:.0f}s for {target:.2f}%"
    return out

def analyze_file(path, pair, last, window):
    arms, notes = load(path)
    print(f"\n=== {os.path.basename(path)} ===")
    for note in notes:
        print(f"  {note}")
    head = (f"{'optimizer':<20}{'final':>8}{'best':>8}{'last' + str(last):>17}{'loss' + str(last):>10}{'time_s':>10}{'s/ep':>8}")
    print(head)
    for name, hist in sorted(arms.items(), key=lambda kv: -kv[1][1][1]):
        m, s = last_n(hist, last)
        total, best = hist[-1][2], max(h[1] for h in hist)
        ml = last_n_loss(hist, last)
        window_col = f"{m:.2f} +/- {s:.2f}"
        loss_col = "-" if ml is None else f"{ml:.4f}"
        print(f"{name:<20}{hist[-1][1]:>8.2f}{best:>8.2f}{window_col:>17}"
              f"{loss_col:>10}{total:>10.1f}{total / len(hist):>8.1f}")

    a, b = pair
    if a not in arms or b not in arms:
        print(f"  ({a} vs {b}: not both present -- no paired comparison)")
        return None
    res = compare(arms, a, b, last, window)
    print(f"\n  {a} - {b}")
    for key, label in (("final", "at final epoch"), (f"last{last}", f"last {last} epochs"),
                       ("eq_single", "equal compute, 1 ep"),
                       (f"eq_mean{window}", f"equal compute, {window} ep")):
        if key in res:
            note = res.pop("_eq_note", "") if key.startswith("eq_") else ""
            print(f"    {label:<24}{res[key]:>+8.2f}pp  {note}")
    # Printed outside the loop above: loss runs the other way, so a shared "+Xpp" line
    # would read as A losing where it is winning.
    if f"loss{last}" in res:
        print(f"    {'test loss (lower=better)':<24}{res[f'loss{last}']:>+8.4f}")
    if "speedup" in res:
        print(f"    {'speedup to target':<24}{res['speedup']:>8.2f}x  {res.pop('_sp_note')}")
    return res

def pool(rows, pair, last, window):
    """Mean +/- sd of the per-session differences.

    n is printed because it is the whole story: the same point estimate with n=3 carried
    +/-0.09 and with n=5 carries +/-0.17, and the second is the honest one -- adding two
    sessions did not move the estimate, it revealed the error bar had been the wrong one.
    """
    if len(rows) < 2: return
    a, b = pair
    print(f"\n=== pooled over {len(rows)} sessions containing both {a} and {b} ===")
    print("Differences are within-session, so pooling them is safe; raw time_s is not.")
    print(f"\n{'metric':<26}{'mean':>8}{'sd':>8}{'n':>4}   values")
    for key, unit in (("final", "pp"), (f"last{last}", "pp"), ("eq_single", "pp"),
                      (f"eq_mean{window}", "pp"), ("speedup", "x"), (f"loss{last}", "loss")):
        vals = [r[key] for r in rows if key in r]
        if not vals: continue
        # Loss differences live two decimal places below accuracy ones (0.29 vs 0.45 on
        # CIFAR-100), so 2dp would round the effect away.
        prec = 4 if unit == "loss" else 2
        sd = f"{statistics.stdev(vals):.{prec}f}" if len(vals) > 1 else "-"
        fmt = {"pp": "%+.2f", "x": "%.2f", "loss": "%+.4f"}[unit]
        shown = " ".join(fmt % v for v in vals)
        print(f"{key:<26}{statistics.mean(vals):>8.{prec}f}{sd:>8}{len(vals):>4}   {shown}")

def main():
    ap = argparse.ArgumentParser(description="Report figures from benchmark run logs.")
    ap.add_argument("csv", nargs="+", help="run logs, e.g. results/runlog_seed*.csv")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"), default=list(DEFAULT_PAIR), help="the paired comparison to run in every file (default: muonsam muon)")
    ap.add_argument("--last", type=int, default=10, help="epochs in the tail window")
    ap.add_argument("--window", type=int, default=5, help="epochs averaged at the equal-compute budget")
    args = ap.parse_args()

    rows = [r for r in (analyze_file(p, args.pair, args.last, args.window) for p in args.csv) if r]
    pool(rows, args.pair, args.last, args.window)

if __name__ == "__main__":
    main()