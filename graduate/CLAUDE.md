# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working rules

- **Do not edit files directly. Show the user the code instead — the user makes all edits themselves.** Present proposed changes as code blocks; do not modify files in the repo on the user's behalf.
- **Code comments / annotations must be in English only — never Korean.** (Chat explanations to the user remain in Korean.)

## What this project is

Hanyang University graduate capstone (졸업 프로젝트, Team 9: 문상철 / 박규현, advisor 이성윤, 2026.03–2026.12).

**Goal:** implement a *new* deep-learning optimizer that fuses the fast convergence of **Muon** with the generalization of **SAM** (Sharpness-Aware Minimization), packaged so it can be `import`ed into existing training code. PyTorch is the primary implementation; a TensorFlow port follows later.

Evaluation is benchmark-driven: train standard vision models with the new optimizer and compare **convergence speed + validation accuracy at an equal compute budget** against baselines (AdamW, SAM). Dataset progression per the plan: CIFAR-10 (prototype/debug) → CIFAR-100 → ImageNet.

## Current state — read this first

The **PyTorch prototype now exists** (matching the proposal's 5–6월 milestone: prototype + CIFAR-10 debug). The novel optimizer is `MuonSAM` in `muon_sam.py`; `muon.py` and `sam.py` are the vendored baselines it builds on; `benchmark_cifar10.py` is the fair-comparison harness. Real tuning/benchmarking on GPU (CIFAR-100 → ImageNet) is the 9–10월 phase and not done yet — current numbers are harness checks, not a verdict (hyperparameters are untuned).

When extending, you are adding to this prototype, not starting from scratch. Design intent below is drawn from the project proposal (`졸업프로젝트_제안서_9팀_문상철_박규현.pdf`), which remains the spec.

## Code architecture / module map

The four combination axes in "Design intent" are the conceptual model; here is how the code realizes them.

- **`muon.py`** — vendored/adapted from Keller Jordan's official Muon. Reusable primitives `zeropower_via_newtonschulz5` (NS5 orthogonalization) and `muon_update` are imported by `muon_sam.py`. Four optimizer classes; the `*WithAuxAdam` variants route Muon vs internal AdamW via a per-param-group `use_muon` flag (Muon for 2D hidden weights, AdamW for the rest). The non-`SingleDevice` classes call `torch.distributed` and require an initialized process group — **use `SingleDeviceMuon` / `SingleDeviceMuonWithAuxAdam` for CPU/single-GPU.**
- **`sam.py`** — standard davda54-style SAM wrapper around a `base_optimizer`. Two-phase API (`first_step` perturbs to `w+ε`, `second_step` restores and updates); `step()` needs a closure. This is the generalization *baseline*, not the fusion.
- **`muon_sam.py`** — **the novel contribution: `MuonSAM(torch.optim.Optimizer)`.** Fuses SAM's perturbation into Muon's spectral geometry (`ε = ρ·O(g)`, `O(·)` = NS5) with:
  - **LookSAM-style periodic 2-pass:** a full SAM step every `sam_period` (= LookSAM k) steps stores a slowly-varying orthogonal correction (`u_v` for Muon group, `g_v` for aux); intermediate steps run 1-pass and reuse it. This is what amortizes SAM's ~2× cost.
  - **Dynamic ρ schedule:** `rho_warmup_frac` keeps ρ=0 early (pure Muon speed), then ramps to `rho_max`.
  - **Param routing:** same `use_muon` flag convention as `muon.py`.
  - `step()` **requires a closure** (full forward-backward), like SAM.
  - **Non-obvious fork:** this prototype **drops Muon's internal momentum** on the Muon group (uses the orthogonalized direction directly, for readable LookSAM logic). Reintroducing momentum is a documented variant to evaluate on GPU — expect Muon-group behavior to differ from a momentum-having version.
- **`benchmark_cifar10.py`** — the fair-comparison harness and de-facto smoke test. Trains **AdamW / SAM / Muon / MuonSAM** on a CIFAR-adapted ResNet-18 (3×3 stem, no maxpool) with **identical weight init and batch order** across all four. Each optimizer has its own branch in `train_epoch` because their step APIs differ (plain / SAM two-phase / closure). **Auto-selects a QUICK config on CPU** (3 epochs, 2k subset) vs a full run on GPU (`QUICK=False`: 50 epochs, full data). Plots accuracy vs epoch *and* vs wall-clock (equal compute budget) to `benchmark.png`.
- **`test_muon_sam.py`** — smoke test exercising MuonSAM's param routing and every step branch on a tiny mixed-parameter model.
- **`make_report.py`** — generates the Korean mid-term report (`중간보고서_9팀.docx`) using only the standard library (`zipfile` + hand-written OOXML), no `python-docx`. Open the result in Word/LibreOffice → "Save as PDF". Not part of the optimizer; it's project deliverable tooling.

## Environment & commands

The venv at `./venv` is the toolchain (Python 3.12.3, `torch 2.12.0+cu130`, `torchvision 0.27.0`, `numpy`, `matplotlib`, `tqdm`). There is **no GPU on this WSL2 machine** (`torch.cuda.is_available()` is `False`) — local runs are CPU-only for debugging; real training happens on Colab (see Workflow).

Always invoke through the venv rather than relying on a global Python:

```bash
# Linux / WSL (this machine)
./venv/bin/python benchmark_cifar10.py   # CIFAR-10 harness (auto QUICK on CPU; downloads CIFAR to ./data)
./venv/bin/python test_muon_sam.py       # MuonSAM smoke test (fast, no dataset)
./venv/bin/python make_report.py         # regenerate 중간보고서_9팀.docx
./venv/bin/pip list

# Windows (the user also works there; a parallel venv uses Scripts/)
venv\Scripts\python.exe benchmark_cifar10.py
venv\Scripts\pip.exe list
```

There is no build/lint infrastructure and no formal test runner; `test_muon_sam.py` and the QUICK path of `benchmark_cifar10.py` are the smoke tests. Prefer extending those over inventing a harness.

## Workflow: working dir vs GitHub vs Colab (non-obvious)

This trips up anyone assuming a normal git checkout:

- **The git repo root is `/mnt/c/projects`**, and this project lives in its **`graduate/`** subfolder. Commit/push from `/mnt/c/projects` (`git add graduate && git commit && git push origin main`). The source `.py` files are tracked.
- The GitHub repo is **`rari458/Projects`** (public); this project is under its `graduate/` subfolder.
- **Colab** trains via: `git clone https://github.com/rari458/Projects.git` → `cd Projects/graduate`. So any script must run correctly with `graduate/` as the working directory and must (re)download datasets (CIFAR auto-downloads; don't hardcode local absolute paths).
- A **`.gitignore` now exists** — it excludes `data/` (CIFAR), the reference PDFs/`.docx`, `venv/`, and caches. It ignores `*.md` broadly but re-includes this file via a `!CLAUDE.md` exception (other `.md` files stay ignored).

## Design intent for the optimizer

Ground new implementation in these points from the proposal. The combination axes are config dimensions, **not** hardcoded strategies — every variant and baseline should be a config, not a rewrite. Guardrail: first pin default configs that reproduce known baselines (pure SAM matching paper numbers, pure Muon, AdamW) to prove correctness, then sweep.

- Implement as a custom `torch.optim.Optimizer` subclass. **SAM costs ~2× compute**: each step does two forward/backward passes — ascend to the worst-case neighborhood (perturb weights by `ε · ĝ`), recompute the gradient there, restore weights, then update. Cutting this overhead while keeping generalization is the core research problem.
- **Muon** orthogonalizes the momentum update (Newton–Schulz iteration) for hidden 2D weight matrices, giving fast convergence; typically paired with a standard optimizer (e.g. AdamW) for non-2D params (biases, norms, embeddings).
- Combination axes to expose as config (orthogonal — each variant is a point in this space). Current `MuonSAM` realizations noted:
  - **SAM perturbation:** off / every step (vanilla, 2×) / every *k* steps (LookSAM-style) / adaptive (ASAM scaling). → `sam_period` (LookSAM k) + per-group `adaptive` flag.
  - **In-step composition order:** gradient at the SAM-perturbed point, *then* Muon-orthogonalize — vs the reverse. → MuonSAM perturbs along `O(g)` then updates with `O(g_s)`.
  - **Time schedule:** static / dynamic. → `rho_warmup_frac` / `rho_max` ρ ramp.
  - **Param-group routing:** Muon for 2D hidden weights, AdamW for biases/norms/embeddings. → `use_muon` flag.
- Always report comparisons at a fixed compute budget, not fixed epoch count (the harness plots both axes).

## Reference papers (PDFs in repo)

- `2010.01412v3.pdf` — **SAM** (Foret et al., ICLR 2021), the generalization baseline.
- `2502.16982v1.pdf` — *Muon is Scalable for LLM Training*.
- `2604.01472v1.pdf` — *The Newton–Muon Optimizer*.
- `2102.11600v3.pdf`, `2110.03141v2.pdf`, `2203.02714v1.pdf` — SAM-family efficiency/variant papers (ESAM, ASAM, GSAM, LookSAM and related) cited for reducing SAM's overhead.

Project documents (Korean): `졸업프로젝트_제안서_9팀_문상철_박규현.pdf` (full proposal/spec), `졸업프로젝트.pdf` (task announcement), `2026_1학기시작_졸프설명.pdf`.
