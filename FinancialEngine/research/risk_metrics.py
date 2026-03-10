import numpy as np
import pandas as pd

def calculate_cvar(rets: pd.Series, delta: float = 0.01) -> float:
    var = rets.quantile(delta)
    cvar = rets[rets <= var].mean()
    return float(cvar)

def calculate_kelly_fraction(rets: pd.Series) -> float:
    win_rets = rets[rets > 0]
    loss_rets = rets[rets < 0]

    if len(win_rets) == 0 or len(loss_rets) == 0:
        return 0.0

    hit_ratio = len(win_rets) / len(rets[rets != 0])
    avg_win = win_rets.mean()
    avg_loss = abs(loss_rets.mean())

    kelly = hit_ratio - ((1 - hit_ratio) / (avg_win / avg_loss))

    half_kelly = kelly / 2.0

    return float(np.clip(half_kelly, 0.0, 1.0))