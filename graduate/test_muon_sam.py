"""Smoke test for MuonSAM: verify it runs end-to-end and exercises very code path."""
import torch
import torch.nn as nn
from muon_sam import MuonSAM

torch.manual_seed(0)

# Small model that deliberately mixes parameter kinds to test routing.
class TinyNet(nn.Module):
    def __init__(self, vocab=10, d=16, n_classes=4):
        super().__init__()
        self.embed = nn.Embedding(vocab, d)
        self.conv  = nn.Conv2d(1, 4, 3, padding=1)
        self.fc    = nn.Linear(4 * 8 * 8 + d, d)
        self.head  = nn.Linear(d, n_classes)
        self.logit_scale = nn.Parameter(torch.ones(1))

    def forward(self, img, tok):
        c = self.conv(img).flatten(1)
        e = self.embed(tok)
        h = torch.relu(self.fc(torch.cat([c, e], dim=1)))
        return self.head(h) * self.logit_scale

model = TinyNet()

# Same split rule as the muon.py example: only hidden weights with ndim>=2
# that are not embeddings or the head go to Muon.
muon_params, aux_params = [], []
for name, p in model.named_parameters():
    if p.ndim >=2 and "embed" not in name and "head" not in name:
        muon_params.append(p)     # conv.weight (4D), fc.weight (2D)
    else: aux_params.append(p)    # embed.weight, head.*, all biases, logit_scale

print(f"muon params: {len(muon_params)} | aux params: {len(aux_params)}")

param_groups = [
    dict(params=muon_params, use_muon=True, lr=0.02, rho=0.05),
    dict(params=aux_params, use_muon=False, lr=3e-4, rho=0.01),
]

# total_steps=6, sam_period=2, warmup=0 -> t=2,4,6 are SAM (2-pass); t=1,3,5 are plain.
opt = MuonSAM(param_groups, total_steps=6, rho_max=0.05, rho_warmup_frac=0.0, sam_period=2)
criterion = nn.CrossEntropyLoss()

def make_closure(img, tok, y):
    def closure():
        opt.zero_grad()
        loss = criterion(model(img, tok), y)
        loss.backward()
        return loss
    return closure

for step in range(1, 7):
    img = torch.randn(8, 1, 8, 8)
    tok = torch.randint(0, 10, (8,))
    y   = torch.randint(0, 4, (8,))

    w_before = model.fc.weight.detach().clone()      # a Muon-group parameter
    loss = opt.step(make_closure(img, tok, y))

    assert torch.isfinite(loss), f"step {step}: loss is NaN/Inf!"
    moved = not torch.equal(w_before, model.fc.weight)
    sam_step = (step % opt.sam_period == 0)          # was this a 2-pass step?
    print(f"step {step}: loss={loss.item():.4f} | SAM(2-pass)={sam_step} | fc.weight updated={moved}")

print("\nOK: if it runs to the end, import / NS5 / 2-pass / schedule branch / restore all work.")

# --- regression: with rho off, momentum_mode='pre_ns5' must equal plain Muon ---
from muon import SingleDeviceMuonWithAuxAdam

def split_params(m):
    mu, ax = [], []
    for name, p in m.named_parameters():
        (mu if p.ndim >=2 and "embed" not in name and "head" not in name else ax).append(p)
    return mu, ax

def closure_for(m, o, img, tok, y):
    def closure():
        o.zero_grad()
        loss = criterion(m(img, tok), y)
        loss.backward()
        return loss
    return closure

torch.manual_seed(0)
m_a, m_b = TinyNet(), TinyNet()
m_b.load_state_dict(m_a.state_dict())       # identical weights, identical batches

mu_a, ax_a = split_params(m_a)
mu_b, ax_b = split_params(m_b)

# rho_warmup_frac=1.0 pins _rho_scale() to 0 for every step, so do_sam is never True and
# no LookSAM correction is ever stored -- the pure-Muon configuration.
# rho_max=0.0 alone is NOT enough: _rho_scale() is already > 0 at t=1, so the 2-pass branch
# would still fire, store a numerically-zero u_v, and the ratio rescaling would then inject
# a full-magnitude noise direction on later steps.
opt_a = MuonSAM([dict(params=mu_a, use_muon=True, lr=0.02),
                dict(params=ax_a, use_muon=False, lr=3e-4)],
                total_steps=10, rho_max=0.0, rho_warmup_frac=1.0,
                momentum_mode="pre_ns5")
opt_b = SingleDeviceMuonWithAuxAdam(
    [dict(params=mu_b, use_muon=True, lr=0.02, weight_decay=0.0),
    dict(params=ax_b, use_muon=False, lr=3e-4, weight_decay=0.0)]
)

torch.manual_seed(1)
for _ in range(5):
    img = torch.randn(8, 1, 8, 8)
    tok = torch.randint(0, 10, (8,))
    y   = torch.randint(0, 4, (8,))
    opt_a.step(closure_for(m_a, opt_a, img, tok, y))
    opt_b.zero_grad()
    criterion(m_b(img, tok), y).backward()
    opt_b.step()

worst = max((pa - pb).abs().max().item()
            for pa, pb in zip(m_a.parameters(), m_b.parameters()))
for (n, pa) , pb in zip(m_a.named_parameters(), m_b.parameters()):
    tok = torch.randint(0, 10, (8,))
    y   = torch.randint(0, 4, (8,))
    opt_a.step(closure_for(m_a, opt_a, img, tok, y))
    opt_b.zero_grad()
    criterion(m_b(img, tok), y).backward()
    opt_b.step()

worst = max((pa - pb).abs().max().item()
            for pa, pb in zip(m_a.parameters(), m_b.parameters()))
for (n, pa), pb in zip(m_a.named_parameters(), m_b.parameters()):
    assert torch.allclose(pa, pb, atol=1e-5), f"{n} diverged: {(pa - pb).abs().max():.2e}"
print(f"OK: momentum_mode='pre_ns5' with rho off == SingleDeviceMuonWithAuxAdam "
      f"(max |diff| = {worst:.2e})")