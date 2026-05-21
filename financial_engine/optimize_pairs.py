import requests
import yfinance as yf
import pandas as pd
import random
import copy

def fetch_data(symbol, start, end):
    print(f"  [Data] Downloading {symbol}...")
    df = yf.download(symbol ,start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

print("Initializing Evolution Data...")
start_date = "2022-01-01"
end_date = "2022-12-31"
ko = fetch_data("KO", start_date, end_date)
pep = fetch_data("PEP", start_date, end_date)
common_index = ko.index.intersection(pep.index)
ko = ko.loc[common_index]
pep = pep.loc[common_index]

BASE_PAYLOAD = {
    "initial_capital": 20000.0,
    "strategy": "PAIRS",
    "leverage": 1.0,
    "max_drawdown_limit": 0.15,
    "assets": {
        "KO": {"opens": ko["Open"].tolist(), "highs": ko["High"].tolist(), "lows": ko["Low"].tolist(), "closes": ko["Close"].tolist()},
        "PEP": {"opens": pep["Open"].tolist(), "highs": pep["High"].tolist(), "lows": pep["Low"].tolist(), "closes": pep["Close"].tolist()}
    }
}

POPULATION_SIZE = 10
GENERATIONS = 5

def create_random_gene():
    return {
        "window": random.randint(10, 60),
        "threshold": random.uniform(1.0, 3.5)
    }

def evaluate_fitness(gene):
    payload = copy.deepcopy(BASE_PAYLOAD)
    payload["pairs_window"] = gene["window"]
    payload["pairs_threshold"] = gene["threshold"]

    try:
        resp = requests.post("http://localhost:8000/api/backtest", json=payload)
        if resp.status_code == 200:
            res = resp.json()
            return res['return_pct']
        return -999.0
    except:
        return -999.0

def mutate(gene):
    if random.random() < 0.3:
        gene["window"] += random.randint(-5, 5)
        gene["window"] = max(5, min(100, gene["window"]))
    if random.random() < 0.3:
        gene["threshold"] += random.uniform(-0.2, 0.2)
        gene["threshold"] = max(0.5, min(5.0, gene["threshold"]))
    return gene

population = [create_random_gene() for _ in range(POPULATION_SIZE)]

print(f"\n🧬 Starting Evolution ({GENERATIONS} Generations)...")

for gen in range(GENERATIONS):
    print(f"\n[Generation {gen+1}] Fighting...")

    scored_pop = []
    for gene in population:
        score = evaluate_fitness(gene)
        scored_pop.append((score, gene))
        print(f"  > Gene [W={gene['window']:2d}, T={gene['threshold']:.2f}] -> Return: {score:.2f}%")

    scored_pop.sort(key=lambda x: x[0], reverse=True)
    best_score, best_gene = scored_pop[0]
    print(f"  🏆 Gen {gen+1} Best: {best_score:.2f}% (Window: {best_gene['window']}, Thresh: {best_gene['threshold']:.2f})")

    survivors = [g for s, g in scored_pop[:POPULATION_SIZE//2]]

    next_gen = []
    while len(next_gen) < POPULATION_SIZE:
        parent = random.choice(survivors)
        child = copy.deepcopy(parent)
        child = mutate(child)
        next_gen.append(child)

    population = next_gen

print("\n========================================")
print(f"🚀 Evolution Complete! Ultimate Parameters:")
print(f"   Window:    {best_gene['window']}")
print(f"   Threshold: {best_gene['threshold']:.2f}")
print(f"   Return:    {best_score:.2f}%")
print("========================================")