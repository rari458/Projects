import React, { useEffect, useState } from "react";

const API = "http://localhost:8000";

export default function Dashboard() {
    const [health, setHealth] = useState(null);

    const [price, setPrice] = useState(null);
    const [priceErr, setPriceErr] = useState("");

    const [factor, setFactor] = useState(null);
    const [factorErr, setFactorErr] = useState("");

    const [weights, setWeights] = useState(null);
    const [weightsErr, setWeightsErr] = useState("");

    const fetchJSON = async (url, init) => {
        const r = await fetch(url, init);
        const txt = await r.text();
        if (!r.ok) throw new Error(txt || `HTTP ${r.status}`);
        return JSON.parse(txt);
    };

    useEffect(() => {
        fetchJSON(`${API}/health`)
            .then(setHealth)
            .catch((e) => setHealth({ error: String(e) }));
    }, []);

    const callPrice = async () => {
        setPriceErr(""); setPrice(null);
        try {
            const data = await fetchJSON(`${API}/price?symbol=AAPL`);
            setPrice(data);
        } catch (e) { setPriceErr(String(e)); }
    };

    const callFactor = async () => {
        setFactorErr(""); setFactor(null);
        try {
            const data = await fetchJSON(`${API}/factor?symbol=AAPL&type=momentum`);
            setFactor(data);
        } catch (e) { setFactorErr(String(e)); }
    };

    const callOptimize = async () => {
        setWeightsErr(""); setWeights(null);
        try {
            const data = await fetchJSON(`${API}/portfolio/optimize`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    expected_returns: [0.1, 0.2, 0.05],
                    cov_flat: [1,0,0, 0,1,0, 0,0,1],
                    n: 3
                })
            });
            setWeights(data);
        } catch (e) { setWeightsErr(String(e)); }
    };

    return (
        <div style={{ padding: 24, fontFamily: "ui-sans-serif" }}>
            <h2>Dashboard</h2>

            <section style={{ marginTop: 12 }}>
                <h3>API Health</h3>
                <pre>{health ? JSON.stringify(health, null, 2) : "loading..."}</pre>
            </section>

            <section style={{ marginTop: 12 }}>
                <h3>Price</h3>
                <button onClick={callPrice}>Get AAPL Price</button>
                {priceErr && <pre style={{ color: "crimson" }}>{priceErr}</pre>}
                <pre>
                    {price ? `symbol=${price.symbol}\nprice=${price.price}` : "No result yet"}
                </pre>
            </section>

            <section style={{ marginTop: 12 }}>
                <h3>Factor (Momentum)</h3>
                <button onClick={callFactor}>Get Factor</button>
                {factorErr && <pre style={{ color: "crimson" }}>{factorErr}</pre>}
                <pre>
                    {factor
                        ? `symbol=${factor.symbol}\nfactor=${factor.factor}\nvalue=${factor.value}` 
                        : "No result yet"}
                </pre>
            </section>

            <section style={{ marginTop: 12 }}>
                <h3>Optimize Portfolio (Equal Weight)</h3>
                <button onClick={callOptimize}>Optimize</button>
                {weightsErr && <pre style={{ color: "crimson" }}>{weightsErr}</pre>}
                <pre>
                    {weights
                        ? `weights=[${weights.weights?.map((w)=>w.toFixed(4)).join(", ")}]`
                        : "No result yet"}
                </pre>
            </section>
        </div>
    );
}