// src/api/backtest.jsx
const API_BASE = "http://localhost:8000";

export async function runBacktest(params) {
    const qs = new URLSearchParams({
        symbol: params.symbol,
        strategy: params.strategy,
        fast: String(params.fast),
        slow: String(params.slow),
        rsi_period: String(params.rsi_period),
        rsi_buy: String(params.rsi_buy),
        rsi_sell: String(params.rsi_sell),
    }).toString();

    const res = await fetch(`${API_BASE}/backtest?${qs}`);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Backtest failed: ${res.status} ${text}`);
    }
    return await res.json();
}

export async function runBacktestPortfolio(body) {
    const res = await fetch(`${API_BASE}/backtest/portfolio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Portfolio backtest failed: ${res.status} ${text}`);
    }

    return await res.json();
}