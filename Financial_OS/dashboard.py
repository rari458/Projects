# dashboard.py

import sys
import os
import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Append C++ Core Directory
sys.path.append(os.path.abspath('./build/src'))
try:
    import FinancialEngine
except ImportError:
    st.error("Failed to import FinancialEngine C++ Core. Check the build path.")
    sys.exit(1)

# Page Config
st.set_page_config(page_title="FinancialOS Conductor", layout="wide", initial_sidebar_state="expanded")
st.title("Aladdin-Killer: FinancialOS v2.0 Dashboard")

# Sidebar Controls
st.sidebar.header("Command Center")
ticker = st.sidebar.text_input("Target Asset (Ticker)", "SPY")

# Expanded Strategy Selection (Including Phase A~D Desks)
strategy_options = [
    "MACD", "EMA", "RSI", "BB", "OU",
    "L3_EXECUTION", "STRUCTURAL_ARB", "DEEP_CYCLE", "META_BRAIN"
]
strategy_name = st.sidebar.selectbox("Active Strategy Engine", strategy_options)
run_button = st.sidebar.button("Execute Backtest")

if run_button:
    with st.spinner(f"Fetching real market data for {ticker}..."):
        data = yf.download(ticker, period="1y", interval="1d", progress=False)

    if data.empty:
        st.error(f"Failed to fetch data for {ticker}.")
    else:
        st.success(f"Data fetched! Streaming {len(data)} ticks to C++ Engine...")

        # Initialize Engine
        engine = FinancialEngine.Backtester(100000.0, strategy_name, 1.0)
        engine.set_regime_filter(False, 252)

        timestamps = []
        tick_count = 0

        # Feed Engine
        for index, row in data.iterrows():
            timestamps.append(index)

            # Handle yfinance multi-index gracefully
            open_p = float(row['Open'].iloc[0]) if isinstance(row['Open'], pd.Series) else float(row['Open'])
            high_p = float(row['High'].iloc[0]) if isinstance(row['High'], pd.Series) else float(row['High'])
            low_p = float(row['Low'].iloc[0]) if isinstance(row['Low'], pd.Series) else float(row['Low'])
            close_p = float(row['Close'].iloc[0]) if isinstance(row['Close'], pd.Series) else float(row['Close'])

            # 1. Base Market Data Feed
            engine.on_market_data(ticker, index.timestamp(), open_p, high_p, low_p, close_p)

            engine.on_market_data("TLT", index.timestamp(), 100.0, 100.0, 100.0, 100.0)

            # 2. Advanced Suites: Event Injection Logic (Simulation)
            tick_count += 1
            if tick_count % 15 == 0:  # Inject specific signals periodically to simulate complex conditions
                if strategy_name == "STRUCTURAL_ARB":
                    #Simulate Delta-Gamma Neutralization
                    event = FinancialEngine.StructuralEvent(
                        FinancialEngine.StructArbType.DELTA_GAMMA, ticker, "", close_p, 0.0, 50.0, index.timestamp()
                    )
                    engine.send_structural_event(event)

                elif strategy_name == "DEEP_CYCLE":
                    # Simulate Short-Term Overreaction Mean-Reversion
                    event = FinancialEngine.DeepCycleEvent(
                        FinancialEngine.DeepCycleType.OVERREACTION, ticker, "", -0.15, 0.0, index.timestamp()
                    )
                    engine.send_deep_cycle_event(event)

                elif strategy_name == "META_BRAIN":
                    # Simulate Risk Parity Rebalancing
                    event = FinancialEngine.MetaEvent(
                        FinancialEngine.MetaBrainType.RISK_PARITY, ticker, 0.18, 0.06, index.timestamp()
                    )
                    engine.send_meta_event(event)

                elif strategy_name == "L3_EXECUTION":
                    # Simulate Institutional Order Flow Front-Running
                    msg = FinancialEngine.L3OrderMessage(
                        index.timestamp(), ticker, "LIT", "INST", close_p, 10000.0, True
                    )
                    engine.send_l3_message(msg)

        # Extract Results
        equity_history = engine.get_equity_history()
        final_equity = engine.get_total_equity()
        mdd = engine.get_max_drawdown() * 100
        trades = engine.get_trade_history()

        # Display Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Final Equity", f"${final_equity:,.2f}", f"{(final_equity-100000)/100000 * 100:.2f}%")
        col2.metric("Max Drawdown", f"{mdd:.2f}%")
        col3.metric("Total Trades", f"{len(trades)}")
        col4.metric("Engine Language", "Native C++ 17")

        # Visualization (Plotly)
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        price_series = data['Close'].iloc[:, 0] if isinstance(data['Close'], pd.DataFrame) else data['Close']
        fig.add_trace(
            go.Scatter(x=timestamps, y=price_series, name=f"{ticker} Price", line=dict(color='rgba(255, 255, 255, 0.3)')), 
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(x=timestamps, y=equity_history, name="Portfolio Equity", line=dict(color='#00ff88', width=2)),
            secondary_y=True,
        )

        fig.update_layout(
            title_text=f"C++ Engine Execution Trace: {strategy_name} on {ticker}",
            template="plotly_dark",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
