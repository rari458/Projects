# MuonSAM

SAM's sharpness-aware perturbation, lifted into Muon's spectral geometry.

Muon converges fast; SAM generalizes well but costs a second forward-backward pass on every
step. MuonSAM perturbs along the *orthogonalized* gradient — `ε = ρ · O(g)`, where `O(·)` is
Newton-Schulz orthogonalization — and amortizes the second pass LookSAM-style, running it once
every `sam_period` steps and reusing a slowly-varying correction in between.

The result beats plain Muon on every dataset we measured, at **+20–37% wall-clock and the same
optimizer memory AdamW already costs**.

> Hanyang University graduate capstone, Team 9 (문상철 / 박규현), advisor 이성윤, 2026.
> Research code: the optimizer and its tests are solid, the API is not frozen.

---

## Results

`muonsam − muon`, paired within each session so the seed cancels. Three seeds per dataset;
CIFAR-10 pools six sessions because two independent runs exist per seed. ResNet-18, 50 epochs,
batch 128, identical weight init and identical batch order across arms.

| dataset | sessions | last 10 ep | at equal compute | speedup |
|---|---|---|---|---|
| CIFAR-10 | 6 | **+0.97 ± 0.19** pp | +0.72 ± 0.22 pp | 2.42 ± 0.35× |
| CIFAR-100 | 3 | **+3.08 ± 0.22** pp | +2.75 ± 0.25 pp | 2.78 ± 0.24× |
| Imagenette 64×64 | 3 | **+1.51 ± 0.27** pp | +0.89 ± 0.36 pp | 2.13 ± 0.18× |

*Equal compute* = MuonSAM's accuracy at the wall-clock Muon needed for its whole run, averaged
over the last 5 epochs finishing inside that budget. *Speedup* = time for MuonSAM to reach Muon's
final accuracy. Both are reported because a method that costs more has to justify it on the axis
that matters, not on epochs.

The gap tracks headroom rather than class count — 93.9% final → +0.97, 90.6% → +1.51,
74.1% → +3.08 — so expect more benefit where the model has room left.

CIFAR-100 in full, mean of the last 10 epochs over 3 seeds:

| optimizer | accuracy | s/epoch | peak GPU mem |
|---|---|---|---|
| **MuonSAM** | **73.75%** | 99.6 | 838 MB |
| Muon | 70.67% | 73.3 | 787 MB |
| AdamW | 67.69% | 48.8 | 832 MB |
| SAM | 66.10% | 93.1 | 836 MB |

### Why not just use SAM?

Because it does not pay for itself. On Imagenette — the small, overfitting-prone dataset where
SAM should look best — `sam` is indistinguishable from `adamw` on accuracy (+0.54 ± 0.78 pp,
2/3 seeds positive), and **at equal compute it loses by 5.07 ± 1.21 pp, 3/3 seeds**, needing 1.5×
the wall-clock to reach AdamW's final accuracy. MuonSAM over Muon on the same dataset is
**+0.89 ± 0.36 pp at equal compute, 3/3 seeds**.

Both buy SAM's generalization. Only one can afford it. That is what the periodic 2-pass is for.

---

## Install

```bash
pip install -e .                 # torch only
pip install -e ".[keras]"        # + the Keras 3 port
pip install -e ".[bench]"        # + torchvision/matplotlib for the benchmark harness
```

Requires Python ≥ 3.10 and PyTorch ≥ 2.0.

---

## Usage

```python
from muonsam import MuonSAM

# Muon takes hidden weights with ndim >= 2; the head, biases and norm scales go to an
# internal AdamW. Which parameters land where is yours to decide -- this is the split the
# reported results used.
muon, aux = [], []
for name, p in model.named_parameters():
    (muon if p.ndim >= 2 and "fc" not in name else aux).append(p)

opt = MuonSAM(
    [dict(params=muon, use_muon=True,  lr=0.02, rho=0.05, weight_decay=5e-4),
     dict(params=aux,  use_muon=False, lr=1e-3, rho=0.01, weight_decay=5e-4)],
    total_steps=len(train_loader) * epochs,
    rho_warmup_frac=0.3,
)

for x, y in train_loader:
    def closure():
        opt.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        return loss
    loss = opt.step(closure)      # calls closure once or twice, depending on the step
```

### Three things that will not raise if you get them wrong

Each of these produces a healthy-looking run that is quietly a different optimizer. None of
them errors.

1. **`step()` requires the closure.** MuonSAM decides *inside* `step()` whether this is a
   1-pass or a 2-pass step, so it has to be able to re-run forward-backward itself. The closure
   must do the full `zero_grad` + forward + `backward` and return the loss.
2. **Do not wrap `step()` in your own `zero_grad()`.** MuonSAM clears gradients itself, and an
   outer `opt.zero_grad()` will discard the gradient the second pass just produced.
3. **`total_steps` is required and is not the LR scheduler's business.** The ρ schedule runs off
   MuonSAM's own internal counter. Pass the wrong total and the perturbation ramp is wrong for
   the entire run, with no symptom other than worse numbers.

### Config axes

Every published variant is a keyword, not a code path.

| argument | default | what it does |
|---|---|---|
| `total_steps` | *required* | drives the ρ schedule |
| `rho_max` | `0.05` | peak perturbation radius; also each group's default `rho` |
| `rho_warmup_frac` | `0.0` | fraction of training with ρ=0 (pure Muon) before the linear ramp. **Use 0.3**; the reported runs do |
| `sam_period` | `5` | LookSAM *k*. Full 2-pass every *k* steps, 1-pass in between |
| `momentum_mode` | `"pre_ns5"` | `"pre_ns5"` momentum on the raw gradient (matches Muon; ρ=0 reduces to plain Muon **exactly**), `"post_ns5"` on the orthogonalized direction, `"none"` no Muon momentum |
| `correction_mode` | `"looksam"` | `"looksam"` keeps `O(g_s)`'s component orthogonal to `O(g)` and adds it; `"gsam"` keeps `O(g)`'s component orthogonal to `O(g_s)` and subtracts it ([2203.08065](https://arxiv.org/abs/2203.08065)). Ours is periodic where published GSAM re-derives every step |
| `adaptive` (per group) | `False` | ASAM ([kwon21b](https://proceedings.mlr.press/v139/kwon21b.html)). Elementwise `\|w\|` on the aux group; scales the spectral perturbation by `‖W‖_F` on the Muon group |
| `looksam_alpha` | `0.7` | weight of the stored correction |
| `ns_steps` | `5` | Newton-Schulz iterations |

`rho_warmup_frac` is not just a speed trick: [2509.21818](https://arxiv.org/abs/2509.21818) shows
SAM can converge to points where the *perturbed* gradient vanishes while the true one does not,
and names a short warm-start before enabling SAM as the safeguard.

---

## Keras 3

```python
from muonsam.keras import KerasMuonSAM, split_variables
from muonsam.keras.train_tf import make_train_step     # TensorFlow backend only

muon_vars, _ = split_variables(model)   # head auto-detected; pass head_layer= to override
opt = KerasMuonSAM(muon_vars, total_steps=steps_per_epoch * epochs, rho_warmup_frac=0.3)

train_step = make_train_step(model, loss_fn, opt)      # compiles both paths
for x, y in dataset:
    loss = train_step(x, y)
```

**`KerasMuonSAM.update_step` raises, by design.** A Keras optimizer only ever receives gradients
someone else computed, so it cannot run SAM's second forward-backward pass. The training loop
owns both passes and calls `sam_first_step` / `sam_second_step` / `looksam_update` explicitly —
`make_train_step` is that loop for TensorFlow. On the JAX or PyTorch Keras backends, write the
equivalent three-call loop yourself; everything except `train_tf` is `keras.ops` only.

**The LookSAM branch must be decided in Python.** Keras wraps `train_step` in a `tf.function`, so
a `t % sam_period == 0` test written inside the traced region is evaluated once and frozen —
periodicity silently disappears while training still looks fine. `should_sam()` is a Python-side
predicate and the two paths compile separately.

The port is pinned to the PyTorch implementation by four parity tests, not by inspection. Worst
deviations against `atol=1e-4`: NS5 `3.29e-06`, `KerasMuon` `3.13e-07`, `KerasMuonSAM`
`1.87e-06`, and the ρ=0 → plain-Muon reduction exact at `0.00e+00`. The compiled driver computes
the same step as the eager loop at ~6× the speed.

---

## Cost

| | 32×32 inputs | 64×64 inputs |
|---|---|---|
| wall-clock vs Muon | +35–37% | +20% |
| peak GPU memory vs Muon | 1.06× | 1.02× |
| optimizer state | **2.00× parameter bytes** | 2.00× (invariant) |

Vanilla SAM would cost ~2×; the periodic 2-pass is what buys the difference.

**MuonSAM's optimizer state is exactly what AdamW already costs** — measured on a T4, three
slots: `momentum_buffer` in fp32 plus `u_vanilla` and `u_v` in bf16. The two extra ratios fall as
inputs grow because the part of the overhead that is not a second pass is bound by *parameter
count*, not activation size. Quote the state ratio as the portable number; the others are
configuration-specific.

---

## Reproducing

The benchmark harness lives at the repo root and is not part of the package.

```bash
python preflight.py                          # every optimizer variant builds with the right config
python benchmark_cifar10.py                  # auto-QUICK on CPU, full 50-epoch run on GPU
DATASET=cifar100 python benchmark_cifar10.py # also: imagenette
python analyze.py results/runlog_c100_seed*.csv
python sharpness.py ckpt_*.pt                # post-hoc flatness of each saved minimum
```

Set `REQUIRE_GPU=1` on any cloud run: without it a CPU session silently produces a 3-epoch log
that looks valid. Every run log behind the tables above is in [`results/`](results/), each
carrying a `#` provenance line.

Tests — run all of them after touching any Keras file:

```bash
python check_bitidentical.py HEAD~1          # gate for any muon_sam.py edit; run it first
python test_muon_sam.py
python test_ns5_parity.py
python test_muon_keras_parity.py
python test_muon_sam_keras_parity.py
python test_muon_sam_keras_graph.py
```

---

## What we do not claim

The point of a capstone is the measurement, so the negative results are reported too.

- **Flatness does not explain Muon's advantage over AdamW.** We measured it. Muon is ~2× *sharper*
  than AdamW on CIFAR-100 while being more accurate, and *flatter* on Imagenette — the sign
  reverses across datasets, 3 seeds against 3. A mechanism whose sign depends on the dataset is
  not the mechanism.
- **SAM flattens the minimum within the Muon family, but the effect is partly a base-loss
  artifact.** `adaptive_sharpness()` returns an absolute loss rise, and the SAM arms sit at lower
  loss. Absolute: MuonSAM flatter than Muon 6/6. Normalized by base loss: 2 positive,
  3 indistinguishable, 1 reversed.
- **`adaptive_sharpness()` is heavy-tailed.** It maximizes over a 5-step ascent, so one steep
  direction dominates: AdamW returned 0.1970 / 1.0427 / 0.8291 across three seeds of one config.
  A single-seed sharpness number is not evidence.
- **The two mechanisms are sub-additive.** Momentum and SAM both smooth the update direction, so
  they partly do the same work: −1.28 ± 0.88 pp interaction, negative in 3/3 seeds. The sign is
  settled; the magnitude is not.
- **Reproducibility floor is ~0.3 pp, and Muon is why.** cuDNN nondeterminism at ~1e-8 is
  amplified roughly 10× per step by Newton-Schulz, because `O(G) = UVᵀ` is ill-conditioned wherever
  `G` is near-rank-deficient. On CPU the harness is bit-reproducible, so the whole floor is that.
  Do not read a single-seed difference below ~0.3 pp as an effect.
- **Learning rates are not per-optimizer tuned.** A 20-epoch screen found Muon and MuonSAM flat
  over a 4× LR range (0.30 / 0.50 pp) while AdamW moves 0.90 pp — so AdamW is the LR-sensitive arm,
  and the harness default sits inside its plateau rather than at an edge.
- **ImageNet was not run.** No lab GPU was available. Imagenette 64×64 is the honest substitute
  and is described as such, never as ImageNet.

---

## Attribution

`muonsam/muon.py` is adapted from [Keller Jordan's Muon](https://github.com/KellerJordan/Muon),
with two deliberate local modifications documented in its header: parameters without gradients
take a zero-gradient update rather than being skipped, and Newton-Schulz runs in fp32 on CPU
(bf16 on CUDA, byte-identical to upstream).

`muonsam/sam.py` follows the standard [davda54/sam](https://github.com/davda54/sam) two-phase
wrapper and is included as the baseline, not as the contribution.

Methods referenced: LookSAM (Liu et al., *Towards Efficient and Scalable Sharpness-Aware
Minimization*, CVPR 2022),
GSAM ([2203.08065](https://arxiv.org/abs/2203.08065)),
ASAM ([kwon21b](https://proceedings.mlr.press/v139/kwon21b.html)),
SAM warm-start ([2509.21818](https://arxiv.org/abs/2509.21818)),
filter-normalized loss surfaces (Li et al., NeurIPS 2018),
Shampoo ([1802.09568](https://arxiv.org/abs/1802.09568)) as Muon's preconditioning ancestor.
