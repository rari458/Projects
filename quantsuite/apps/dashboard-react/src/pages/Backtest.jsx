import React, { useEffect, useState, useRef, useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, Tooltip, Legend,
    CartesianGrid, ResponsiveContainer, Scatter, 
    ReferenceLine, Brush
} from "recharts";

const API = "http://localhost:8000";

const usePersist = (key, init) => {
    const [v, setV] = useState(() => {
        try { return JSON.parse(localStorage.getItem(key) ?? "null") ?? init; }
        catch { return init; }
    });
    useEffect(() => { localStorage.setItem(key, JSON.stringify(v)); }, [key, v]);
    return [v, setV];
};

function BuyDot({ cx, cy }) {
    if (cx == null || cy == null) return null;
    return (
        <g transform={`translate(${cx},${cy})`}>
            <circle r={4} fill="#16a34a" stroke="#fff" strokeWidth={1} />
        </g>
    );
}

function SellDot({ cx, cy }) {
    if (cx == null || cy == null) return null;
    return (
        <g transform={`translate(${cx},${cy})`}>
            <circle r={4} fill="#ef4444" stroke="#fff" strokeWidth={1} />
        </g>
    );
}

function PriceTooltip({ active, payload }) {
    if (!active || !payload?.length) return null;

    const row = payload[0]?.payload ?? {};
    const ts = row.ts ?? null;
    const dateStr = ts ? new Date(ts).toISOString().slice(0,10) : '-';
    const byKey = Object.fromEntries(payload.map(p => [p.dataKey, p.value]));

    const val = (k) => {
        const v = byKey[k] ?? row[k];
        return Number.isFinite(v) ? v : null;
    };

    return (
        <div style={{ background:'#fff', border: '1px solid #ddd', padding: 8, borderRadius: 8 }}>
            <div style={{ fontWeight: 600 }}>{dateStr}</div>
            {"close" in row && <div>close : {val("close") != null ? val("close").toFixed(2) : "-"}</div>}
            {"ma_fast" in row && <div>ma_fast: {val("ma_fast") != null ? val("ma_fast").toFixed(2) : "-"}</div>}
            {"ma_slow" in row && <div>ma_slow: {val("ma_slow") != null ? val("ma_slow").toFixed(2) : "-"}</div>}
            {val("equity") != null && <div>equity: {val("equity").toFixed(6)}</div>}
            {val("bench_equity") != null && <div>benchmark: {val("bench_equity").toFixed(6)}</div>}
            {val("dd") != null && <div>drawdown: {val("dd").toFixed(2)}%</div>}
        </div>
    );
}

export default function Backtest() {
    const [symbol, setSymbol] = useState("SP500");
    const [fast, setFast] = useState(5);
    const [slow, setSlow] = useState(20);
    const [bt, setBt] = useState(null);
    const [err, setErr] = useState("");
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);

    const [showSignals, setShowSignals] = usePersist("bt.showSignals", true);
    const [showMA, setShowMA]           = usePersist("bt.showMA", true);
    const [logPrice, setLogPrice]       = usePersist("bt.logPrice", false);
    const [logEquity, setLogEquity]     = usePersist("bt.logEquity", false);
    const [asPct, setAsPct]             = usePersist("bt.asPct", false);
    const [showDD, setShowDD]           = usePersist("bt.showDD", true);
    const [showGrid, setShowGrid]       = usePersist("bt.grid", true);
    const [gridDense, setGridDense]     = usePersist("bt.gridDense", false);
    const [showLegend, setShowLegend]   = usePersist("bt.legend", true);
    const [lineW, setLineW]             = usePersist("bt.lineW", 2);
    const [lineAlpha, setLineAlpha]     = usePersist("bt.alpha", 1.0);
    const [dark, setDark]               = usePersist("bt.dark", false);
    const [autoRun, setAutoRun]         = usePersist("bt.autoRun", true);

    const [cursorTs, setCursorTs]       = useState(null);
    const [viewStartTs, setViewStartTs] = useState(null);
    const [brushKey, setBrushKey]       = useState(0);

    const priceWrapRef  = useRef(null);
    const equityWrapRef = useRef(null);

    const fetchJSON = async (url, init) => {
        const r = await fetch(url, init);
        const t = await r.text();
        if (!r.ok) throw new Error(t || `HTTP ${r.status}`);
        return JSON.parse(t);
    };

    const asNum = (v) => {
        if (v === null || v === undefined || v === '') return null;
        if (typeof v === 'number') return Number.isFinite(v) ? v : null;
        const n = parseFloat(String(v).replace(/,/g, '').trim());
        return Number.isFinite(n) ? n : null;
    };

    const toSeries = (res) => {
        if (!res?.dates) return [];
        const tmp = res.dates.map((d, i) => {
            const ts = new Date(String(d)).getTime();
            return {
                date: String(d),
                ts,
                close:   asNum(res.close?.[i]),
                ma_fast: asNum(res.ma_fast?.[i]),
                ma_slow: asNum(res.ma_slow?.[i]),
                equity:  asNum(res.equity?.[i]), 
            };
        });
        tmp.sort((a, b) => a.ts - b.ts);

        const firstClose = tmp.find(r => Number.isFinite(r.close))?.close ?? null;
        if (Number.isFinite(firstClose) && firstClose !== 0) {
            for (const r of tmp) {
                r.bench_equity = Number.isFinite(r.close)
                    ? r.close / firstClose
                    : null;
            }
        } else {
            for (const r of tmp) r.bench_equity = null;
        }

        return tmp;
    };

    const signalPointsFromSeries = (s) => {
        const buys = [], sells = [];
        for (let i = 1; i < s.length; i++) {
            const p0 = s[i-1], p1 = s[i];
            const ok = [p0.ma_fast, p0.ma_slow, p1.ma_fast, p1.ma_slow, p1.close].every((v) => Number.isFinite(v));
            if (!ok) continue;
           
            if (p0.ma_fast <= p0.ma_slow && p1.ma_fast > p1.ma_slow) 
                buys.push({ ts: p1.ts, y: p1.close, side: "Buy" });
            if (p0.ma_fast >= p0.ma_slow && p1.ma_fast < p1.ma_slow) 
                sells.push({ ts: p1.ts, y: p1.close, side: "Sell" });
        }
        return { buys, sells };
    };

    const run = async () => {
        if (loading) return;
        setLoading(true); 
        setErr(""); 
        setBt(null);
        try {
            const j = await fetchJSON(`${API}/backtest?symbol=${symbol}&fast=${fast}&slow=${slow}`);
            setBt(j);
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    };

    const runUpload = async () => {
        if (!file || loading) return;
        setLoading(true); 
        setErr(""); 
        setBt(null);
        try {
            const form = new FormData();
            form.append("file", file);
            const r = await fetch(`${API}/backtest/upload?fast=${fast}&slow=${slow}`, { 
                method: "POST", 
                body: form, 
            });
            const t = await r.text();
            if (!r.ok) throw new Error(t || `HTTP ${r.status}`);
            setBt(JSON.parse(t));
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    };

    const s  = bt ? toSeries(bt) : [];
    const sp = s.length ? signalPointsFromSeries(s) : { buys: [], sells: [] };
    const minTs = s.length ? s[0].ts : undefined;
    const maxTs = s.length ? s[s.length - 1].ts : undefined;

    const yDomain = (() => {
        if (!s.length) return ['auto','auto'];
        const vals = s.flatMap(d => [d.close, d.ma_fast, d.ma_slow]).filter(Number.isFinite);
        if (!vals.length) return ['auto','auto'];
        const mn = Math.min(...vals), mx = Math.max(...vals);
        const pad = Math.max(1e-6, (mx - mn) * 0.06);
        return mn === mx
            ? [mn - Math.max(1e-4, Math.abs(mn) * 0.01), mx + Math.max(1e-4, Math.abs(mx) * 0.01)]
            : [mn - pad, mx + pad];
    })();

    const equityDomain = useMemo(() => {
        const vals = s.flatMap(d => [d.equity, d.bench_equity]).filter(Number.isFinite);
        if (!vals.length) return ['auto','auto'];
        const mn = Math.min(...vals), mx = Math.max(...vals);
        const pad = Math.max(1e-6, (mx - mn) * 0.06);
        if (mx - mn === 0) {
            const p = Math.max(1e-6, Math.abs(mx) * 0.01);
            return [mn - p, mx + p];
        }
        return [mn - pad, mx + pad];
    }, [s]);

    const baseRow = s.length
        ? (s.find(r => r.ts >= (viewStartTs ?? (s[0]?.ts))) ?? s[0])
        : null;

    const priceData = (asPct && baseRow?.close != null)
        ? s.map(r => ({
                ...r,
                close_p:   r.close   != null ? (r.close   / baseRow.close - 1) * 100 : null,
                ma_fast_p: r.ma_fast != null ? (r.ma_fast / baseRow.close - 1) * 100 : null,
                ma_slow_p: r.ma_slow != null ? (r.ma_slow / baseRow.close - 1) * 100 : null, 
            }))
        : s;

    const equityWithDD = (() => {
        let peak = -Infinity;
        return s.map(r => {
            if (Number.isFinite(r.equity)) peak = Math.max(peak, r.equity);
            const dd = (Number.isFinite(r.equity) && peak > 0) ? (r.equity / peak - 1) * 100 : null;
            return { ...r, dd };
        });
    })();

    const ddDomain = useMemo(() => {
        const vals = equityWithDD.map(d => d.dd).filter(Number.isFinite);
        if (!vals.length) return [-100, 0];
        const mn = Math.min(...vals);
        const mx = Math.max(...vals);
        const lo = Math.min(-100, Math.floor(mn));
        const hi = Math.min(0, Math.ceil(mx));
        return [lo, hi];
    }, [equityWithDD]);

    const downloadsSignalsCSV = () => {
        const rows = [["date", "ts", "side", "price"]];
        const pushRows = (arr, side) => {
            for (const r of arr) rows.push([new Date(r.ts).toISOString().slice(0,10), r.ts, side, r.y]);
        };
        pushRows(sp.buys, "Buy");
        pushRows(sp.sells, "Sell");
        const csv = rows.map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `signals_${symbol}_f${fast}_s${slow}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const exportPNG = (wrapRef, name) => {
        const root = wrapRef.current;
        if (!root) return;
        const svg = root.querySelector("svg");
        if (!svg) return;
        const s = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([s], { type: "image/svg+xml;charset=utf-8" });
        const svgUrl = URL.createObjectURL(svgBlob);
        const img = new Image();
        img.onload = () => {
            const rect = svg.viewBox?.baseVal;
            const W = rect?.width  || svg.clientWidth || 1200;
            const H = rect?.height || svg.clientWidth || 360;
            const canvas = document.createElement("canvas");
            canvas.width = W; canvas.height = H;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, W, H);
            canvas.toBlob((b) => {
                const a = document.createElement("a");
                a.href = URL.createObjectURL(b);
                a.download = `${name}.png`;
                a.click();
            });
            URL.revokeObjectURL(svgUrl);
        };
        img.src = svgUrl;
    };

    const canLogPrice = useMemo(() => {
        if (!logPrice) return false;
        for (const r of s) {
            const tri = [r.close, r.ma_fast, r.ma_slow].filter(v => v != null);
            if (tri.some(v => v <= 0)) return false;
        }
        return s.some(r => [r.close, r.ma_fast, r.ma_slow].some(v => Number.isFinite(v) && v > 0));
    }, [logPrice, s]);

    const canLogEquity = useMemo(() => {
        if (!logEquity) return false;
        for (const r of s) {
            if (Number.isFinite(r.equity) && r.equity <= 0) return false;
        }
        return s.some(r => Number.isFinite(r.equity) && r.equity > 0);
    }, [logEquity, s]);

    useEffect(() => {
        document.body.classList.toggle("dark", dark);
    }, [dark]);

    useEffect(() => {
        if (!autoRun) return;
        const id = setTimeout(() => { if (!loading) run(); }, 400);
        return () => clearTimeout(id);
    }, [symbol, fast, slow]);

    useEffect(() => {
        const onKey = (e) => {
            if (["INPUT","SELECT","TEXTAREA"].includes(e.target.tagName)) return;
            if (e.key === "r") run();
            if (e.key === "l") setLogPrice(v => !v);
            if (e.key === "m") setShowMA(v => !v);
            if (e.key === "s") setShowSignals(v => !v);
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, []);

    return (
        <div style={{ fontFamily: "ui-sans-serif" }}>
            <h2>Run Backtest (C++)</h2>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
                <label>Symbol:&nbsp;
                    <select value={symbol} onChange={(e)=>setSymbol(e.target.value)}>
                        <option value="SP500">SP500</option>
                    </select>
                </label>
                <label>Fast:&nbsp;
                    <input type="number" min={1} max={200} value={fast} onChange={(e)=>setFast(Number(e.target.value) || 5)} />
                </label>
                <label>Slow:&nbsp;
                    <input type="number" min={2} max={400} value={slow} onChange={(e)=>setSlow(Number(e.target.value) || 20)} />
                </label>

                <button onClick={run} disabled={loading}>{loading ? "Running..." : "Run Backtest"}</button>

                <input type="file" accept=".csv" onChange={(e)=>setFile(e.target.files?.[0] ?? null)} />
                <button onClick={runUpload} disabled={loading || !file}>{loading ? "Uploading..." : "Run on CSV"}</button>

                <button onClick={downloadsSignalsCSV} disabled={!s.length}>Download Signals CSV</button>
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "6px 0 12" }}>
                <label><input type="checkbox" checked={showSignals} onChange={e=>setShowSignals(e.target.checked)} />Signals</label>
                <label><input type="checkbox" checked={showMA} onChange={e=>setShowMA(e.target.checked)} />MAs</label>
                <label><input type="checkbox" checked={showLegend} onChange={e=>setShowLegend(e.target.checked)} />Legend</label>
                <label><input type="checkbox" checked={showGrid} onChange={e=>setShowGrid(e.target.checked)} />Grid</label>
                <label><input type="checkbox" checked={gridDense} onChange={e=>setGridDense(e.target.checked)} />Dense grid</label>
                <label><input type="checkbox" checked={asPct} onChange={e=>setAsPct(e.target.checked)} />Percent axis</label>
                <label><input type="checkbox" checked={showDD} onChange={e=>setShowDD(e.target.checked)} />Drawdown</label>
                <label><input type="checkbox" checked={logPrice} onChange={e=>setLogPrice(e.target.checked)} />Log price</label>
                <label><input type="checkbox" checked={logEquity} onChange={e=>setLogEquity(e.target.checked)} />Log equity</label>
                <label><input type="checkbox" checked={dark} onChange={e=>setDark(e.target.checked)} />Dark</label>
                <label><input type="checkbox" checked={autoRun} onChange={e=>setAutoRun(e.target.checked)} />Auto-run</label>
                <button onClick={()=>setBrushKey(k=>k+1)}>Reset Zoom</button>
                <button onClick={()=>exportPNG(priceWrapRef,  "price_chart")}  disabled={!s.length}>Save Price PNG</button>
                <button onClick={()=>exportPNG(equityWrapRef, "equity_chart")} disabled={!s.length}>Save Equity PNG</button>
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
                <label>Width&nbsp;
                    <input type="range" min="1" max="5" value={lineW} onChange={e=>setLineW(+e.target.value)} />
                </label>
                <label>Opacity&nbsp;
                    <input type="range" min="0.2" max="1" step="0.1" value={lineAlpha} onChange={e=>setLineAlpha(+e.target.value)} />
                </label>
            </div>

            {err && <pre style={{ color: "crimson" }}>{err}</pre>}

            {bt && (
                <div style={{ display: "flex", gap: 16, margin: "12px 0", flexWrap: "wrap" }}>
                    <KPI title="Total Return"      value={`${(bt.total_return * 100).toFixed(2)}%`} />
                    <KPI title="CAGR(252)"         value={`${(bt.cagr252      * 100).toFixed(2)}%`} />
                    <KPI title="Trades"            value={`B:${(bt.signals?.buy ?? 0)} / S:${bt.signals?.sell ?? 0}`} />
                    <KPI title="Volatility (Ann.)" value={`${(bt.volatility   * 100).toFixed(2)}%`} />
                    <KPI title="Max Drawdown"      value={`${(bt.max_drawdown * 100).toFixed(2)}%`} />
                    <KPI title="Sharpe (252)"      value={`${Number(bt.sharpe).toFixed(2)}`} />
                </div>
            )}

            {s.length > 0 && (
                <ResponsiveContainer width="99%" height={360} minWidth={200} minHeight={200} key={`p-${s.length}-${fast}-${slow}`}>
                    <div ref={priceWrapRef}>
                        <LineChart
                            data={asPct ? priceData : s}
                            margin={{ top: 24, right: 32, left: 16, bottom: 16 }}
                            onMouseMove={(e)=>{ const ts = e?.activePayload?.[0]?.payload?.ts; if (ts) setCursorTs(ts); }}
                            onMouseLeave={()=>setCursorTs(null)}
                        >
                            {showGrid && <CartesianGrid strokeDasharray={gridDense ? "2 2" : "3 3"} />}

                            <XAxis 
                                xAxisId="price"
                                dataKey="ts"
                                type="number"
                                domain={minTs !== undefined ? [minTs, maxTs] : ["dataMin","dataMax"]}
                                tickFormatter={(ts)=>new Date(ts).toISOString().slice(0,10)}
                                minTickGap={32}
                            />
                            <YAxis 
                                yAxisId="priceY"
                                type="number"
                                domain={yDomain}
                                padding={{ top: 6, bottom: 6 }}
                                allowDataOverflow={false}
                                scale={canLogPrice ? "log" : "linear"}
                            />

                            {cursorTs != null && <Reference x={cursorTs} xAxisId="price" stroke="#94a3b8" strokeDasharray="3 3" />}

                            <Tooltip content={<PriceTooltip />} isAnimationActive={false} filterNull={false} />
                            {showLegend && <Legend />}

                            <Brush 
                                key={brushKey}
                                dataKey="ts"
                                height={24}
                                travellerWidth={10}
                                onChange={(r)=>{ if (r?.startIndex!=null) {
                                    const row = (asPct ? priceData : s)[r.startIndex];
                                    if (row?.ts) setViewStartTs(row.ts);
                                }}}
                            />
                            <Line isAnimationActive={false} type="linear"
                                dataKey={asPct ? "close_p" : "close"}
                                name="close"
                                xAxisId="price" yAxisId="priceY"
                                stroke="#1677ff" strokeWidth={lineW} strokeOpacity={lineAlpha}
                                dot={false} connectNulls strokeLinejoin="round" strokeLinecap="round" />
                            {showMA && (
                                <>
                                    <Line isAnimationActive={false} type="linear"
                                        dataKey={asPct ? "ma_fast_p" : "ma_fast"}
                                        name="ma_fast"
                                        xAxisId="price" yAxisId="priceY"
                                        stroke="#10b981" strokeWidth={lineW} strokeOpacity={lineAlpha}
                                        dot={false} connectNulls strokeLinejoin="round" strokeLinecap="round" />
                                    <Line isAnimationActive={false} type="linear"
                                        dataKey={asPct ? "ma_slow_p" : "ma_slow"}
                                        name="ma_slow"
                                        xAxisId="price" yAxisId="priceY"
                                        stroke="#f59e0b" strokeWidth={lineW} strokeOpacity={lineAlpha}
                                        dot={false} connectNulls strokeLinejoin="round" strokeLinecap="round" />
                                </>
                            )}

                            {showSignals && (
                                <>
                                    <Scatter data={sp.buys}  dataKey="y" x="ts" y="y"
                                        xAxisId="price" yAxisId="priceY" name="Buy"
                                        shape={BuyDot}  fill="#16a34a" isAnimationActive={false} legendType="circle" />
                                    <Scatter data={sp.sells} dataKey="y" x="ts" y="y"
                                        xAxisId="price" yAxisId="priceY" name="Sell"
                                        shape={SellDot} fill="#ef4444" isAnimationActive={false} legendType="circle" />
                                </>
                            )}
                        </LineChart>
                    </div>
                </ResponsiveContainer>
            )}

            {s.length > 0 && (
                <div style={{ marginTop: 12 }}>
                    <ResponsiveContainer width="99%" height={360} minWidth={200} minHeight={200} key={`e-${s.length}-${fast}-${slow}`}>
                        <div ref={equityWrapRef}>
                            <LineChart
                                data={equityWithDD}
                                margin={{ top: 24, right: 32, left: 16, bottom: 16}}
                                onMouseMove={(e)=>{ const ts = e?.activePayload?.[0]?.payload?.ts; if (ts) setCursorTs(ts); }}
                                onMouseLeave={()=>setCursorTs(null)}
                            >
                                {showGrid && <CartesianGrid strokeDasharray={gridDense ? "2 2" : "3 3"} />}

                                <XAxis
                                    xAxisId="price"
                                    dataKey="ts"
                                    type="number"
                                    domain={minTs !== undefined ? [minTs, maxTs] : ["dataMin","dataMax"]}
                                    tickFormatter={(ts)=>new Date(ts).toISOString().slice(0,10)}
                                    minTickGap={32}
                                />
                                <YAxis
                                    yAxisId="eqY"
                                    type="number"
                                    domain={equityDomain}
                                    padding={{ top: 6, bottom: 6 }}
                                    allowDataOverflow={false}
                                    scale={canLogEquity ? "log" : "linear"}
                                />

                                <YAxis 
                                    yAxisId="ddY"
                                    orientation="right"
                                    type="number"
                                    domain={ddDomain}
                                    tickFormatter={(v) => `${v.toFixed(0)}%`}
                                    padding={{ top: 6, bottom: 6 }}
                                    allowDataOverflow={false}
                                    hide={!showDD}
                                />

                                {cursorTs != null && (
                                    <ReferenceLine
                                        x={cursorTs}
                                        xAxisId="price"
                                        stroke="#94a3b8"
                                        strokeDasharray="3 3"
                                    />
                                )}

                                <Tooltip content={<PriceTooltip />} isAnimationActive={false} />
                                {showLegend && <Legend />}

                                <Brush 
                                    key={brushKey}
                                    dataKey="ts"
                                    height={24}
                                    travellerWidth={10}
                                    onChange={(r)=>{ 
                                        if (r?.startIndex != null) {
                                            const row = equityWithDD[r.startIndex];
                                            if (row?.ts) setViewStartTs(row.ts);
                                        }
                                    }}
                                />

                                <Line 
                                    xAxisId="price" 
                                    yAxisId="eqY" 
                                    type="monotone"
                                    dataKey="equity" 
                                    name="equity" 
                                    dot={false}
                                    stroke="#3b82f6" 
                                    strokeWidth={lineW} 
                                    strokeOpacity={lineAlpha}
                                    isAnimationActive={false} 
                                />
                                <Line 
                                    xAxisId="price" 
                                    yAxisId="eqY"
                                    type="monotone"
                                    dataKey="bench_equity" 
                                    name="benchmark(BH)" 
                                    dot={false}
                                    stroke="#64748b"
                                    isAnimationActive={false} 
                                />

                                {showDD && (
                                    <Line 
                                        xAxisId="price" 
                                        yAxisId="ddY" 
                                        type="monotone"
                                        dataKey="dd" 
                                        name="drawdown(%)" 
                                        dot={false}
                                        stroke="#dc2626" 
                                        strokeDasharray="4 2"
                                        isAnimationActive={false}
                                    />
                                )}
                            </LineChart>
                        </div>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

function KPI({ title, value }) {
    return (
        <div style={{ padding: 12, border: "1px solid #ddd", borderRadius: 12 }}>
            <div style={{ fontSize: 12, color: "#666" }}>{title}</div>
            <div style={{ fontSize: 20 }}>{value}</div>
        </div>
    );
}