import React, { useEffect, useState } from "react";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: "ui-sans-serif, system-ui" }}>
      <h1>QuantSuite Dashboard</h1>
      <p>API Health:</p>
      <pre>
        {health ? JSON.stringify(health) : error ? `ERR: ${error}` : "loading..."}
      </pre>
      <small>Ensure FastAPI is running on http://localhost:8000</small>
    </div>
  );
}