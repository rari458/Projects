# walkforward.py

import numpy as np
import FinancialEngine
import data_store

UNIVERSE = [
    "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "JNJ", "XOM",
    "PG", "KO", "HD", "V", "MA", "UNH"
]

TRAIN = 252
TEST = 63
RF = 0.02

def weights_for(method, train_block, symbols):
    n = len(symbols)
    if method == "equal_weight":
        return np.full(n, 1.0 / n)

    opt = FinancialEngine.Optimizer()
    for j, sym in enumerate(symbols):
        opt.add_asset(sym, train_block[:, j].tolist())

    if method == "min_variance":
        res = opt.optimize_minimum_variance(RF)
    elif method == "random_mc":
        res = opt.optimize_sharpe_ratio(100000, RF, 0)
    elif method == "tangency":
        res = opt.optimize_max_sharpe_analytic(RF)
    elif method == "shrunk":
        res = opt.optimize_max_sharpe_shrunk(RF)
    elif method == "robust":
        res = opt.optimize_max_sharpe_robust(RF)
    else:
        raise ValueError(method)
    return np.array(res.optimal_weights)

def walk_forward(returns, method):
    R = returns.values
    symbols = returns.columns.tolist()
    oos = []
    start = 0
    while start + TRAIN + TEST <= len(R):
        train_block = R[start : start + TRAIN]
        test_block  = R[start + TRAIN : start + TRAIN + TEST]
        w = weights_for(method, train_block, symbols)
        oos.append(test_block @ w)
        start += TEST
    return np.concatenate(oos)

def summarize(name, oos):
    ann_ret = oos.mean() * 252.0
    ann_vol = oos.std(ddof=1) * np.sqrt(252.0)
    sharpe  = (ann_ret - RF) / ann_vol if ann_vol > 1e-9 else 0.0
    print(f"    {name:14s}  OOS Sharpe {sharpe:7.3f}   ann.ret {ann_ret * 100:8.2f}%"
          f"    ann.vol {ann_vol * 100:8.2f}%")

def main():
    con = data_store.connect()
    stored = set(data_store.symbols(con)["symbol"])          
    missing = [s for s in UNIVERSE if s not in stored]
    if missing:
        print(f"-> Ingesting {len(missing)} missing symbols...")
        data_store.ingest_many(con, missing)

    returns = data_store.get_returns_matrix(con, UNIVERSE, start="2021-07-01")
    con.close()

    n_windows = (len(returns) - TRAIN - TEST) // TEST + 1
    print(f"-> {len(UNIVERSE)} symbols, {len(returns)} days, "
          f"{n_windows} OOS windows (train={TRAIN}, test={TEST})\n")
    print("-> Out-of-sample performance (weights fixed from in-sample only):")

    for method, label in [
        ("equal_weight", "Equal-weight"),
        ("min_variance", "Min-variance"),
        ("random_mc",    "Random MC"),
        ("shrunk",       "Shrunk-LW"),
        ("tangency",     "Tangency"),
        ("robust",       "Robust-BS+LW"),
    ]:
        summarize(label, walk_forward(returns, method))

if __name__ == "__main__":
    main()