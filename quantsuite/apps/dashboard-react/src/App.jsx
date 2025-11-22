import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Backtest from "./pages/Backtest";

export default function App() {
  return (
    <div style={{ padding: 24, fontFamily: "ui-sans-serif" }}>
      <nav style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Link to="/">Dashboard</Link> 
        <Link to="/backtest">Backtest</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backtest" element={<Backtest />} />
      </Routes>
    </div>
  );
}