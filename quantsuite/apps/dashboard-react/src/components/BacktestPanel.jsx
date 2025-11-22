// src/components/BacktestPanel.jsx
import React, { useState, useMemo } from "react";
import { runBacktest, runBacktestPortfolio } from "../api/backtest.jsx";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    Legend,
    CartesianGrid,
    ResponsiveContainer,
} from "recharts";

const DEFAULT_PRESETS = [
    {
        id: "single_ma_sp500",
        name: "Single: SP500 MA(5, 20)",
        config: {
            mode: "single",
            symbol: "SP500",
            weightsText: "",
            strategy: "ma",
            fast: 5,
            slow: 20,
            rsiPeriod: 14,
            rsiBuy: 30,
            rsiSell: 70,
            sliderW0: 50,
            weightMode: "auto",
        },
    },
    {
        id: "pf_ma_sp500_50_50",
        name: "Portfolio: SP500,SP500 (50/50 MA)",
        config: {
            mode: "portfolio",
            symbol: "SP500",
            symbolsText: "SP500,SP500",
            weightsText: "",
            strategy: "ma",
            fast: 5,
            slow: 20,
            rsiPeriod: 14,
            rsiBuy: 30,
            rsiSell: 70,
            sliderW0: 50,
            weightMode: "auto",
        },
    },
    {
        id: "single_rsi_sp500",
        name: "Single: SP500 RSI(14,30/70)",
        config: {
            mode: "single",
            symbol: "SP500",
            symbolsText: "SP500",
            weightsText: "",
            strategy: "rsi",
            fast: 5,
            slow: 20,
            rsiPeriod: 14,
            rsiBuy: 30,
            rsiSell: 70,
            sliderW0: 50,
            weightMode: "auto",
        },
    },
];

const PRESET_STORAGE_KEY = "qs_presets_v1";

export default function BacktestPanel() {
    const [mode, setMode] = useState("single");
    const [symbol, setSymbol] = useState("SP500");
    const [symbolsText, setSymbolsText] = useState("SP500,SP500");
    const [weightsText, setWeightsText] = useState("");

    const [strategy, setStrategy] = useState("ma");
    const [fast, setFast] = useState(5);
    const [slow, setSlow] = useState(20);
    const [rsiPeriod, setRsiPeriod] = useState(14);
    const [rsiBuy, setRsiBuy] = useState(30);
    const [rsiSell, setRsiSell] = useState(70);

    const [weightMode, setWeightMode] = useState("auto");
    const [sliderW0, setSliderW0] = useState(50);

    const [presets, setPresets] = useState(() => {
        try {
            const saved = window.localStorage.getItem(PRESET_STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    return parsed;
                }
            }
        } catch (_) {}
        return DEFAULT_PRESETS;
    });

    const [selectedPresetId, setSelectPresetId] = useState(
        DEFAULT_PRESETS[0]?.id || ""
    );

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const parsedSymbols = useMemo(
        () =>
            symbolsText
                .split(",")
                .map((s) => s.trim())
                .filter((s) => s.length > 0),
        [symbolsText]
    );
    const isTwoAssets = parsedSymbols.length === 2;

    const currentConfig = useMemo(
        () => ({
            mode,
            symbol,
            symbolsText,
            weightsText,
            strategy,
            fast,
            slow,
            rsiPeriod,
            rsiBuy,
            rsiSell,
            sliderW0,
            weightMode,
        }),
        [
            mode,
            symbol,
            symbolsText,
            weightsText,
            strategy,
            fast,
            slow,
            rsiPeriod,
            rsiBuy,
            rsiSell,
            sliderW0,
            weightMode,
        ]
    );

    const handleApplyPreset = () => {
        const p = presets.find((x) => x.id === selectedPresetId);
        if (!p) return;
        const cfg = p.config || {};

        setMode(cfg.mode ?? "single");
        setSymbol(cfg.symbol ?? "SP500");
        setSymbolsText(cfg.symbolsText ?? "SP500,SP500");
        setWeightsText(cfg.weightsText ?? "");
        setStrategy(cfg.strategy ?? "ma");
        setFast(cfg.fast ?? 5);
        setSlow(cfg.slow ?? 20);
        setRsiPeriod(cfg.rsiPeriod ?? 14);
        setRsiBuy(cfg.rsiBuy ?? 30);
        setRsiSell(cfg.rsiSell ?? 70);
        setSliderW0(cfg.sliderW0 ?? 50);
        setWeightMode(cfg.weightMode ?? "auto");
    };

    const handleSavePreset = () => {
        setPresets((prev) => {
            const idx = prev.findIndex((p) => p.id === selectedPresetId);
            if (idx === -1) return prev;

            const updated = [...prev];
            const old = updated[idx];
            updated[idx] = {
                ...old,
                config: { ...currentConfig },
            };

            try {
                window.localStorage.setItem(
                    PRESET_STORAGE_KEY,
                    JSON.stringify(updated)
                );
            } catch (_) {}

            return updated;
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            if (mode === "single") {
                const res = await runBacktest({
                    symbol,
                    strategy,
                    fast: Number(fast),
                    slow: Number(slow),
                    rsi_period: Number(rsiPeriod),
                    rsi_buy: Number(rsiBuy),
                    rsi_sell: Number(rsiSell),
                });
                setResult(res);
            } else {
                const symbolsArray = parsedSymbols;

                if (symbolsArray.length === 0) {
                    throw new Error("Please provide at least one symbol for portfolio backtest.");
                }

                let weights = undefined;
                const raw = weightsText.trim();

                if (raw.length > 0) {
                    const parts = raw.split(",").map((s) => s.trim());
                    if (parts.length !== symbolsArray.length) {
                        throw new Error(`You provided ${symbolsArray.length} symbols but ${parts.length} weights`);
                    }

                    const nums = parts.map((p) => {
                        const v = Number(p);
                        if (!Number.isFinite(v) || v < 0) {
                            throw new Error("Weights must be non-negative numbers.");
                        }
                        return v;
                    });

                    weights = nums;
                } else if (symbolsArray.length === 2 && weightMode === "auto") {
                    const w0 = sliderW0 / 100.0;
                    const w1 = 1.0 - w0;
                    weights = [w0, w1];
                }

                const res = await runBacktestPortfolio({
                    symbols: symbolsArray,
                    strategy,
                    fast: Number(fast),
                    slow: Number(slow),
                    rsi_period: Number(rsiPeriod),
                    rsi_buy: Number(rsiBuy),
                    rsi_sell: Number(rsiSell),
                    weights,
                    weight_mode: weightMode,
                });
                console.log("portfolio backtest result", res);
                setResult(res);
            }
        } catch (err) {
            setError(String(err));
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    const chartData = useMemo(() => {
        if (!result || !result.dates || !result.equity) return [];

        const n_Assets =
            typeof result.n_assets === "number" && result.equity_assets
                ? result.n_assets
                : 0;

        return result.dates.map((date, idx) => {
            const point = {
                date,
                equity: result.equity?.[idx] ?? null,
                close: result.close?.[idx] ?? null,
            };

            if (result.strategy === "ma") {
                point.ma_fast = result.ma_fast?.[idx] ?? null;
                point.ma_slow = result.ma_slow?.[idx] ?? null;
            }

            if (result.strategy === "rsi" && result.rsi) {
                point.rsi = result.rsi?.[idx] ?? null;
            }

            if (result.strategy === "boll") {
                point.boll_mid = result.boll_mid?.[idx] ?? null;
                point.boll_up  = result.boll_up?.[idx] ?? null;
                point.boll_dn  = result.boll_dn?.[idx] ?? null;
            }

            if (result.strategy === "donchian") {
                point.donch_high = result.donch_high?.[idx] ?? null;
                point.donch_low  = result.donch_low?.[idx] ?? null;
            }

            const nAssetsSafe = 
                typeof result.n_assets === "number" &&
                Array.isArray(result.equity_assets)
                    ? Math.min(result.n_assets, result.equity_assets.length)
                    : 0;

            if (nAssetsSafe > 0) {
                for (let i = 0; i < nAssetsSafe; i++) {
                    const arr = result.equity_assets[i];
                    if (Array.isArray(arr)) {
                        point[`eq_${i}`] = arr[idx] ?? null;
                    }
                }
            }

            return point;
        });
    }, [result]);

    const handleDownloadJSON = () => {
        if (!result) return;

        const pretty = JSON.stringify(result, null, 2);
        const blob = new Blob([pretty], { type: "application/json" });

        const baseName =
            mode === "single"
                ? `${symbol}_${result.strategy}`
                : `portfolio_${result.strategy}`;

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `backtest_${baseName}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    const handleDownloadCSV = () => {
        if (!result || !Array.isArray(chartData) || chartData.length === 0) return;

        const nAssetsSafe =
            typeof result.n_assets === "number" &&
            Array.isArray(result.equity_assets)
                ? Math.min(result.n_assets, result.equity_assets.length)
                : 0;

        const baseCols = ["date", "close", "equity"];
        const stratCols = [];

        if (result.strategy === "ma") {
            stratCols.push("ma_fast", "ma_slow");
        } else if (result.strategy === "rsi") {
            stratCols.push("rsi");
        } else if (result.strategy === "boll") {
            stratCols.push("boll_mid", "boll_up", "boll_dn");
        } else if (result.strategy === "donchian") {
            stratCols.push("donch_high", "donch_low");
        }

        const assetCols = [];
        for (let i = 0; i < nAssetsSafe; i++) {
            assetCols.push(`eq_${i}`);
        }

        const headers = [...baseCols, ...stratCols, ...assetCols];
        const lines = [];

        lines.push(headers.join(","));

        for (const row of chartData) {
            const values = headers.map((key) => {
                const v = row[key];
                if (v === null || typeof v === "undefined") return "";
                if (typeof v === "number") return v.toString();
                return `"${String(v).replace(/"/g, '""')}"`;
            });
            lines.push(values.join(","));
        }

        const csvStr = lines.join("\n");
        const blob = new Blob([csvStr], { type: "text/csv" });

        const baseName =
            mode === "single"
                ? `${symbol}_${result.strategy}`
                : `portfolio_${result.strategy}`;

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `backtest_${baseName}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    const nAssets = result && typeof result.n_assets === "number" ? result.n_assets : 0;
    const weights = result && Array.isArray(result.weights) ? result.weights : [];
    const assetVols = result && Array.isArray(result.asset_vols) ? result.asset_vols : [];
    const assetSharpes = result && Array.isArray(result.asset_sharpes) ? result.asset_sharpes : [];
    const nAssetsMetrics = Math.min(
        nAssets,
        assetVols.length > 0 ? assetVols.length : nAssets,
        assetSharpes.length > 0 ? assetSharpes.length : nAssets
    );


    return (
        <div 
            style={{ 
                padding: "1.5rem", 
                fontFamily: "sans-serif",
                maxWidth: "1200px",
                margin: "0 auto",
            }}
        >
            <h1 style={{ marginBottom: "1rem" }}>Quantsuite Backtester</h1>

            <div
                style={{
                    marginBottom: "1rem",
                    display: "flex",
                    gap: "1rem",
                    alignItems: "center",
                    flexWrap: "wrap",
                }}
            >
                <label>
                    <input
                        type="radio"
                        value="single"
                        checked={mode === "single"}
                        onChange={() => setMode("single")}
                    />{" "}
                    Single Asset
                </label>
                <label>
                    <input
                        type="radio"
                        value="portfolio"
                        checked={mode === "portfolio"}
                        onChange={() => setMode("portfolio")}
                    /> {" "}
                    Portfolio
                </label>
            </div>

            <div
                style={{
                    marginBottom: "1rem",
                    padding: "0.75rem 1rem",
                    border: "1px dashed #ccc",
                    borderRadius: "8px",
                    background: "#fafafa",
                }}
            >
                <div 
                    style={{
                        marginBottom: "0.5rem",
                        fontSize: "0.9rem",
                        fontWeight: 600,
                    }}
                >
                    Presets
                </div>
                <div
                    style={{
                        display: "flex",
                        gap: "0.5rem",
                        alignItems: "center",
                        flexWrap: "wrap",
                    }}
                >
                    <select
                        value={selectedPresetId}
                        onChange={(e) => setSelectPresetId(e.target.value)}
                    >
                        {presets.map((p) => (
                            <option key={p.id} value={p.id}>
                                {p.name}
                            </option>
                        ))}
                    </select>
                    <button type="button" onClick={handleApplyPreset}>
                        Apply
                    </button>
                    <button type="button" onClick={handleSavePreset}>
                        Save to Selected Slot
                    </button>
                    <span style={{ fontSize: "0.8rem", color: "#666" }}>
                        (Save = overwrite selected preset with current config)
                    </span>
                </div>
            </div>

            <form
                onSubmit={handleSubmit}
                style={{
                    marginBottom: "1.5rem",
                    padding: "1rem",
                    border: "1px solid #ddd",
                    borderRadius: "8px",
                }}
            >
                {mode === "single" && (
                    <div style={{ marginBottom: "0.5rem" }}>
                        <label>
                            Symbol:&nbsp;
                            <input
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                placeholder="SP500"
                            />
                        </label>
                    </div>
                )}

                {mode === "portfolio" && (
                    <>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Symbols (comma-separated):&nbsp;
                                <input
                                    style={{ width: "260px" }}
                                    value={symbolsText}
                                    onChange={(e) => setSymbolsText(e.target.value)}
                                    placeholder="SP500,SP500"
                                />
                            </label>
                            <div style={{ fontSize: "0.8rem", color: "#666" }}>
                                e.g., SP500, AAPL, MSFT
                            </div>
                        </div>

                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Weights (optional, comma-separated):&nbsp;
                                <input 
                                    style={{ width: "260px" }}
                                    value={weightsText}
                                    onChange={(e) => setWeightsText(e.target.value)}
                                    placeholder="0.5,0.3,0.2"
                                />
                            </label>
                            <div style={{ fontSize: "0.8rem", color: "#666" }}>
                                e.g., 0.5, 0.3, 0.2 (must sum to 1.0)
                                <br />
                                If empty and you have 2 symbols and Weight Mode
                                = auto, slider below will be used.
                            </div>
                        </div>

                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Weight Mode:&nbsp;
                                <select
                                    value={weightMode}
                                    onChange={(e) => setWeightMode(e.target.value)}
                                >
                                    <option value="auto">Auto</option>
                                    <option value="equal">Equal Weight</option>
                                    <option value="risk_parity">
                                        Risk Parity (min vol)
                                    </option>
                                </select>
                            </label>
                            <div style={{ fontSize: "0.8rem", color: "#666", marginTop: "0.2rem" }}>
                                - Auto: use manual weights if given; otherwise
                                for 2 assets use slider; else equal-weight.
                                <br />
                                - Equal: ignore slider and manual weights, use 1/N.
                                <br />
                                - Risk Parity: ignore weights field and slider,
                                backend computes vol-inverse weights.
                            </div>
                        </div>

                        {isTwoAssets && (
                            <div style={{ marginBottom: "0.5rem" }}>
                                <div
                                    style={{
                                        fontSize: "0.8rem",
                                        color: "#666",
                                        marginBottom: "0.25rem",
                                    }}
                                >
                                    2-asset slider (used only when weights field is empty & Weight Mode = auto)
                                </div>
                                <input 
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={sliderW0}
                                    onChange={(e) =>
                                        setSliderW0(Number(e.target.value))
                                    }
                                    style={{ width: "260px" }}
                                />
                                <div
                                    style={{
                                        fontSize: "0.8rem",
                                        color: "#333",
                                        marginTop: "0.25rem",
                                    }}
                                >
                                    {parsedSymbols[0]}:{" "}
                                    {(sliderW0 / 100).toFixed(2)} &nbsp; |{" "} 
                                    &nbsp;
                                    {parsedSymbols[1]}:{" "}
                                    {(1 - sliderW0 / 100).toFixed(2)}
                                </div>
                            </div>
                        )}
                    </>
                )}

                <div style={{ marginBottom: "0.5rem" }}>
                    <label>
                        Strategy:&nbsp;
                        <select
                            value={strategy}
                            onChange={(e) => setStrategy(e.target.value)}
                        >
                            <option value="ma">MA</option>
                            <option value="rsi">RSI</option>
                            <option value="macd">MACD</option>
                            <option value="boll">BOLL</option>
                            <option value="donchian">DONCHIAN</option>
                            <option value="breakout">BREAKOUT</option>
                        </select>
                    </label>
                </div>

                {strategy === "ma" && (
                    <>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Fast:&nbsp;
                                <input
                                    type="number"
                                    value={fast}
                                    onChange={(e) => setFast(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Slow:&nbsp;
                                <input
                                    type="number"
                                    value={slow}
                                    onChange={(e) => setSlow(e.target.value)}
                                />
                            </label>
                        </div>
                    </>
                )}

                {strategy === "rsi" && (
                    <>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                RSI Period:&nbsp;
                                <input
                                    type="number"
                                    value={rsiPeriod}
                                    onChange={(e) => setRsiPeriod(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                RSI Buy:&nbsp;
                                <input
                                    type="number"
                                    value={rsiBuy}
                                    onChange={(e) => setRsiBuy(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                RSI Sell:&nbsp;
                                <input
                                    type="number"
                                    value={rsiSell}
                                    onChange={(e) => setRsiSell(e.target.value)}
                                />
                            </label>
                        </div>
                    </>
                )}

                {strategy === "macd" && (
                    <>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                MACD Fast EMA:&nbsp;
                                <input
                                    type="number"
                                    value={fast}
                                    onChange={(e) => setFast(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                MACD Slow EMA:&nbsp;
                                <input
                                    type="number"
                                    value={slow}
                                    onChange={(e) => setSlow(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                MACD Signal Period:&nbsp;
                                <input
                                    type="number"
                                    value={rsiPeriod}
                                    onChange={(e) => setRsiPeriod(e.target.value)}
                                />
                            </label>
                        </div>
                    </>
                )}

                {strategy === "boll" && (
                    <>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                Window:&nbsp;
                                <input
                                    type="number"
                                    value={fast}
                                    onChange={(e) => setFast(e.target.value)}
                                />
                            </label>
                        </div>
                        <div style={{ marginBottom: "0.5rem" }}>
                            <label>
                                K (band width):&nbsp;
                                <input
                                    type="number"
                                    value={slow}
                                    onChange={(e) => setSlow(e.target.value)}
                                />
                            </label>
                        </div>
                    </>
                )}

                {strategy === "donchian" && (
                    <div style={{ marginBottom: "0.5rem" }}>
                        <label>
                            Window:&nbsp;
                            <input
                                type="number"
                                value={fast}
                                onChange={(e) => setFast(e.target.value)}
                            />
                        </label>
                    </div>
                )}

                {strategy === "breakout" && (
                    <div style={{ marginBottom: "0.5rem" }}>
                        <label>
                            Breakout Window:&nbsp;
                            <input
                                type="number"
                                value={fast}
                                onChange={(e) => setFast(e.target.value)}
                            />
                        </label>
                    </div>
                )}

                <button type="submit" disabled={loading}>
                    {loading ? "Running..." : "Run Backtest"}
                </button>
            </form>

            {error && (
                <div style={{ color: "red", marginBottom: "1rem", whiteSpace: "pre" }}>
                    Error: {error}
                </div>
            )}

            {result && (
                <div style={{ marginBottom: "1.5rem" }}>
                    <h2>Result</h2>

                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns:
                                "repeat(auto-fit, minmax(160px, 1fr))",
                            gap: "0.75rem",
                            marginBottom: "0.75rem",
                        }}
                    >

                        <div
                            style={{
                                border: "1px solid #ddd",
                                borderRadius: "6px",
                                padding: "0.5rem 0.75rem",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "0.8rem",
                                    color: "#666",
                                    marginBottom: "0.2rem",
                                }}
                            >
                                Total Return
                            </div>
                            <div style={{ fontSize: "1.3rem", fontWeight: 600 }}>
                                {(result.total_return * 100).toFixed(2)}%
                            </div>
                        </div>

                        <div
                            style={{
                                border: "1px solid #ddd",
                                borderRadius: "6px",
                                padding: "0.5rem 0.75rem",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "0.8rem",
                                    color: "#666",
                                    marginBottom: "0.2rem",
                                }}
                            >
                                CAGR (252)
                            </div>
                            <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                                {(result.cagr252 * 100).toFixed(2)}%
                            </div>
                        </div>

                        <div
                            style={{
                                border: "1px solid #ddd",
                                borderRadius: "6px",
                                padding: "0.5rem 0.75rem",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "0.8rem",
                                    color: "#666",
                                    marginBottom: "0.2rem",
                                }}
                            >
                                Volatility / Sharpe
                            </div>
                            <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                                {(result.volatility * 100).toFixed(2)}% / {" "}
                                {result.sharpe.toFixed(3)}
                            </div>
                        </div>

                        <div
                            style={{
                                border: "1px solid #ddd",
                                borderRadius: "6px",
                                padding: "0.5rem 0.75rem",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "0.8rem",
                                    color: "#666",
                                    marginBottom: "0.2rem",
                                }}
                            >
                                Max Drawdown
                            </div>
                            <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                                {(result.max_drawdown * 100).toFixed(2)}%
                            </div>
                        </div>
                    </div>

                    <div
                        style={{
                            margin: "0.5rem 0 0.75rem",
                            display: "flex",
                            gap: "0.5rem",
                            flexWrap: "wrap",
                        }}
                    >
                        <button type="button" onClick={handleDownloadJSON}>
                            Download JSON
                        </button>
                        <button type="button" onClick={handleDownloadCSV}>
                            Download CSV
                        </button>
                    </div>
                    
                    <p>Strategy: {result.strategy}</p>
                    <p style={{ margin: "0.25rem 0" }}>
                        Signals: buy = {result.signals?.buy ?? 0}, sell = {" "}
                        {result.signals?.sell ?? 0}
                    </p>

                    {nAssets > 0 && (
                        <div style={{ marginTop: "0.5rem" }}>
                            <p>
                                Assets: {nAssets}
                                {weights.length === nAssets && (
                                    <>
                                        {" "}
                                        | Weights: {" "}
                                        {weights
                                            .map((w, i) => 
                                            `w${i}=${(w * 100).toFixed(1)}%`
                                            )
                                            .join(", ")}
                                    </>                                    
                                )}
                            </p>

                            {nAssetsMetrics > 0 && (
                                <div
                                    style={{
                                        marginTop: "0.25rem",
                                        fontSize: "0.85rem",
                                        color: "#444",
                                    }}
                                >
                                    {Array.from({ length: nAssetsMetrics }).map((_, i) => {
                                        const v = assetVols[i];
                                        const s = assetSharpes[i];
                                        if (typeof v !== "number" && typeof s !== "number") {
                                            return null;
                                        }
                                        return (
                                            <div key={i}>
                                                Asset {i}:{" "}
                                                {typeof v === "number"
                                                    ? `vol=${(v * 100).toFixed(2)}%`
                                                    : "vol=-"}
                                                {" , "}
                                                {typeof s === "number"
                                                    ? `sharpe=${s.toFixed(3)}`
                                                    : "sharpe=-"}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            <table
                                style={{
                                    marginTop: "0.5rem",
                                    borderCollapse: "collapse",
                                    fontSize: "0.85rem",
                                }}
                            >
                                <thead>
                                    <tr>
                                        <th
                                            style={{
                                                borderBottom: "1px solid #ccc",
                                                padding: "0.25rem 0.5rem",
                                                textAlign: "left",
                                            }}
                                        >
                                            Asset
                                        </th>
                                        <th
                                            style={{
                                                borderBottom: "1px solid #ccc",
                                                padding: "0.25rem 0.5rem",
                                                textAlign: "right",
                                            }}
                                        >
                                            Weight
                                        </th>
                                        <th
                                            style={{
                                                borderBottom: "1px solid #ccc",
                                                padding: "0.25rem 0.5rem",
                                                textAlign: "right",
                                            }}
                                        >
                                            Vol (ann.)
                                        </th>
                                        <th
                                            style={{
                                                borderBottom: "1px solid #ccc",
                                                padding: "0.25rem 0.5rem",
                                                textAlign: "right",
                                            }}
                                        >
                                            Sharpe
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Array.from({ length: nAssets }).map((_, idx) => {
                                        const w =
                                            idx < weights.length
                                                ? weights[idx]
                                                : null;
                                        const vol =
                                            idx < assetVols.length
                                                ? assetVols[idx]
                                                : null;
                                        const sh =
                                            idx < assetSharpes.length
                                                ? assetSharpes[idx]
                                                : null;
                                        return (
                                            <tr key={`asset-row-${idx}`}>
                                                <td
                                                    style={{
                                                        padding: "0.25rem 0.5rem"
                                                    }}
                                                >
                                                    Asset {idx}
                                                </td>
                                                <td
                                                    style={{
                                                        padding: "0.25rem 0.5rem",
                                                        textAlign: "right",
                                                    }}
                                                >
                                                    {w != null
                                                        ? `${(w * 100).toFixed(1)}%`
                                                        : "-"}
                                                </td>
                                                <td
                                                    style={{
                                                        padding: "0.25rem 0.5rem",
                                                        textAlign: "right",
                                                    }}
                                                >
                                                    {vol != null
                                                        ? `${(vol * 100).toFixed(2)}%`
                                                        : "-"}
                                                </td>
                                                <td
                                                    style={{
                                                        padding: "0.25rem 0.5rem",
                                                        textAlign: "right",
                                                    }}
                                                >
                                                    {sh != null
                                                        ? sh.toFixed(3)
                                                        : "-"}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {result && chartData.length > 0 && (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "1rem",
                    }}
                >
                    <div
                        style={{
                            width: "100%",
                            minWidth: 0,
                            border: "1px solid #eee",
                            borderRadius: "8px",
                            padding: "0.5rem",
                        }}
                    >
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" hide />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="close" name="close" dot={false} />

                                {result.strategy === "ma" && (
                                    <>
                                        <Line
                                            type="monotone"
                                            dataKey="ma_fast"
                                            name="MA Fast"
                                            dot={false}
                                            strokeDasharray="2 2"
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="ma_slow"
                                            name="MA Slow"
                                            dot={false}
                                            strokeDasharray="4 4"
                                        />
                                    </>
                                )}

                                {result.strategy === "boll" && (
                                    <>
                                        <Line
                                            type="monotone"
                                            dataKey="boll_mid"
                                            name="Middle Band"
                                            dot={false}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="boll_up"
                                            name="Upper Band"
                                            dot={false}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="boll_dn"
                                            name="Lower Band"
                                            dot={false}
                                        />
                                    </>
                                )}

                                {result.strategy === "donchian" && (
                                    <>
                                        <Line
                                            type="monotone"
                                            dataKey="donch_high"
                                            name="Donchian High"
                                            dot={false}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="donch_low"
                                            name="Donchian Low"
                                            dot={false}
                                        />
                                    </>
                                )}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div
                        style={{
                            width: "100%",
                            minWidth: 0,
                            border: "1px solid #eee",
                            borderRadius: "8px",
                            padding: "0.5rem",
                        }}
                    >
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart
                                data={chartData}
                                margin={{top: 10, right: 20, bottom: 10, left: 0}}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line 
                                    type="monotone"
                                    dataKey="equity"
                                    name="Portfolio Equity"
                                    dot={false}
                                />
                                {nAssets > 0 &&
                                    Array.from({ length: nAssets }).map((_, idx) => (
                                        <Line 
                                            key={`eq_${idx}`}
                                            type="monotone"
                                            dataKey={`eq_${idx}`}
                                            name={`Asset ${idx} Equity`}
                                            dot={false}
                                            strokeDasharray="5 5"
                                        />
                                    ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}
        </div>
    );
}