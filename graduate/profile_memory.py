"""Optimizer memory cost -- the half of MuonSAM's overhead that has never been measured.

The reported CIFAR-10 results quantify compute (+35% per epoch over Muon) and say nothing
about memory, which is the worse number: MuonSAM keeps four tensors per parameter where
Muon keeps one. "How much memory?" is the first question a reader asks about an optimizer
that stores a correction per weight matrix, and right now the project cannot answer it.

Optimizer state size depends only on which slots get allocated, never on gradient values,
so this feeds synthetic gradients instead of running real forward-backward passes. The
numbers are therefore exact rather than sampled, and the whole script takes seconds on
CPU. Peak *activation* memory is a different quantity that does need a GPU -- see the
note printed at the end.
"""
import sys
import torch
import benchmark_cifar10 as B

STEPS = 12          # >= 10, so muonsam's rho warm-up ends and a 2-pass step fires
TOTAL_STEPS = 20    # what build_optimizer chedules rho against
MB = 1024 ** 2

def fake_grads(model):
    """Gradient values are irrelevant to state allocation; shapes and dtypes are not."""
    for p in model.parameters():
        p.grad = torch.randn_like(p) * 1e-2

def run_steps(kind, model, opt, steps=STEPS):
    loss = torch.tensor(0.0)

    def closure():
        fake_grads(model)
        return loss

    for _ in range(steps):
        if kind in B.CLOSURE_KINDS:
            opt.step(closure)
        elif kind == "sam":
            fake_grads(model)
            opt.first_step(zero_grad=False)
            fake_grads(model)
            opt.second_step(zero_grad=False)
        else:
            fake_grads(model)
            opt.step()

def optimizer_state_bytes(opt):
    """Every tensor the optimizer keeps, split into what it owns and what merely aliases
    the model.

    Two traps. SAM keeps `old_p` in its own state dict and delegates the momentum buffer
    to the optimizer it wraps, so walking `opt.state` alone under-reports it by a whole
    copy of the model. And SAM's `second_step` does `p.data = old_p`, which makes that
    entry the parameter itself -- counting it as optimizer state would double-count the
    model. Debup is by storage pointer for the same reason.
    """
    param_ptrs = {p.data_ptr() for g in opt.param_groups for p in g["params"]}
    seen, own, aliased, per_slot = set(), 0, 0, {}

    def walk(state):
        nonlocal own, aliased
        for pstate in state.values():
            for slot, v in pstate.items():
                if not torch.is_tensor(v) or v.data_ptr() in seen:
                    continue
                seen.add(v.data_ptr())
                nbytes = v.numel() * v.element_size()
                if v.data_ptr() in param_ptrs:
                    aliased += nbytes
                else:
                    own += nbytes
                    per_slot[slot] = per_slot.get(slot, 0) + nbytes

    walk(opt.state)
    if hasattr(opt, "base_optimizer"):
        walk(opt.base_optimizer.state)
    return own, aliased, per_slot

def main():
    model = B.make_resnet18()
    n_params = sum(p.numel() for p in model.parameters())
    param_mb = sum(p.numel() * p.element_size() for p in model.parameters()) / MB
    print(f"CIFAR ResNet-18: {n_params:,} parameters = {param_mb:.1f} MB in fp32")
    print(f"state measured after {STEPS} steps on synthetic gradients\n")

    print(f"{'optimizer':<16}{'state MB':>10}{'x model':>9}{'aliased':>9}   slots")
    rows = []
    for kind in B.KINDS:
        torch.manual_seed(0)
        model = B.make_resnet18()
        opt = B.build_optimizer(kind, model, total_steps=TOTAL_STEPS)
        run_steps(kind, model, opt)
        own, aliased, per_slot = optimizer_state_bytes(opt)
        slots = ", ".join(f"{k}({v / MB:.0f})" for k, v in
                          sorted(per_slot.items(), key=lambda kv: -kv[1]))
        print(f"{kind:<16}{own / MB:>10.1f}{own / MB / param_mb:>9.2f}"
              f"{aliased / MB:>9.1f}   {slots}")
        rows.append((kind, own / MB))

    base = dict(rows)
    if "muon" in base and "muonsam" in base:
        print(f"\nMuonSAM vs Muon: {base['muonsam'] / max(base['muon'], 1e-9):.2f}x the "
              f"optimizer state, {base['muonsam'] - base['muon']:+.1f} MB on ResNet-18.")
    print("Total training footprint also includes parameters, gradients and activations, "
          "so the end-to-end ratio is milder than the column above.")
    print("\nPeak activation memory is NOT measured here -- it needs a GPU. Add "
          "torch.cuda.max_memory_allocated() to benchmark_cifar10.py's next cloud run.")
    return 0

if __name__ == "__main__":
    sys.exit(main())