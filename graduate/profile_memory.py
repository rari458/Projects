"""Optimizer state size per kind -- the memory half of "MuonSAM's overhead".

State size dependson only on which slots get allocated, never on gradient values, so this
feeds synthetic gradients rather than running real forward-backward passes. The numbers are
exact rather than sampled, and the whole script takes seconds.

IT MUST BE RUN WHERE THE ANSWER IS WANTED. State size is independent of gradient values but
not of gradient DTYPE, and muon.py runs NS5 in bfloat16 on CUDA against float32 on CPU.
MuonSAM's two NS5-derived slots are therefore half as wide on a GPU: a CPU run reports 3.00x
parameter bytes where a T4 measures 2.00x -- the same as AdamW, which is a much better
result than the one the CPU figure implies. That overstatement stood for a week because the
output showed bytes and not dtypes, so every slot now prints its dtype and the header names
the devices.

Peak *activation* memory is a different quantity and a far larger one -- activations are
~80% of the peak for ResNet-18 at batch 128 -- so the end-to-end ratio is much milder than
the state ratio here. benchmark_cifar10.py reports it from torch.cuda.max_memory_allocated()
on a real run.
"""
import sys
import torch
import benchmark_cifar10 as B

STEPS = 12          # >= 10, so muonsam's rho warm-up ends and a 2-pass step fires
TOTAL_STEPS = 20    # what build_optimizer schedules rho against
MB = 1024 ** 2
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

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
    model. Dedup is by storage pointer for the same reason.

    per_slot is keyed by (name, dtype), not by name alone: the dtype is the whole reason a
    CPU run and a CUDA run disagree, and it has to be visible in the output rather than
    inferred from which machine happened to produce it.
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
                    key = (slot, str(v.dtype).removeprefix("torch."))
                    per_slot[key] = per_slot.get(key, 0) + nbytes

    walk(opt.state)
    if hasattr(opt, "base_optimizer"):
        walk(opt.base_optimizer.state)
    return own, aliased, per_slot

def main():
    model = B.make_resnet18().to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    param_mb = sum(p.numel() * p.element_size() for p in model.parameters()) / MB
    print(f"CIFAR ResNet-18: {n_params:,} parameters = {param_mb:.1f} MB in fp32")
    print(f"state measured on {DEVICE} after {STEPS} steps on synthetic gradients\n")

    print(f"{'optimizer':<16}{'state MB':>10}{'x model':>9}{'aliased':>9}   slots")
    rows = []
    for kind in B.KINDS:
        torch.manual_seed(0)
        model = B.make_resnet18().to(DEVICE)
        opt = B.build_optimizer(kind, model, total_steps=TOTAL_STEPS)
        run_steps(kind, model, opt)
        own, aliased, per_slot = optimizer_state_bytes(opt)
        slots = ", ".join(f"{name}/{dtype}({v / MB:.0f})" for (name, dtype), v in
                          sorted(per_slot.items(), key=lambda kv: -kv[1]))
        print(f"{kind:<16}{own / MB:>10.1f}{own / MB / param_mb:>9.2f}"
              f"{aliased / MB:>9.1f}   {slots}")
        rows.append((kind, own / MB))

    base = dict(rows)
    if "muon" in base and "muonsam" in base:
        print(f"\nMuonSAM vs Muon: {base['muonsam'] / max(base['muon'], 1e-9):.2f}x the "
              f"optimizer state, {base['muonsam'] - base['muon']:+.1f} MB on ResNet-18.")
    if DEVICE == "cpu":
        print("CPU run: the NS5-derived slots print as float32 above and are bfloat16 on "
              "CUDA, so the muonsam rows overstate a GPU. Re-run this under CUDA before "
              "quoting any of them.")
    print("Parameters, gradients and activations are excluded, and activations dominate -- "
          "benchmark_cifar10.py prints the end-to-end peak on a real GPU run.")
    return 0

if __name__ == "__main__":
    sys.exit(main())