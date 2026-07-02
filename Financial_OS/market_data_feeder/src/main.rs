use futures_util::StreamExt;
use serde_json::Value;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};

mod ffi;
use ffi::Engine;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let url = "wss://stream.binance.com:9443/ws/btcusdt@depth5@100ms";
    let (ws_stream, _) = connect_async(url).await.expect("Failed to connect to Binance L2 WS");
    println!("-> [Rust Microstructure Engine] Connected to Binance L2 Orderbook.");

    // Boot the C++ engine directly acrosst the FFI boundary -- no UDP, no Python.
    let mut engine = Engine::new(100_000.0, "L3_EXECUTTION", 1.0)
        .expect("Failed to construct C++ Backtester over FFI");
    engine.set_regime_filter(false, 252);
    println!("-> [FFI Bridge] Navtive C++ engine booted (strategy  = L3_EXECUTION).");

    let (_, mut read) = ws_stream.split();

    let mut tick_count: u64 = 0;

    while let Some(message) = read.next().await {
        if let Ok(Message::Text(text)) = message {
            if let Ok(json) = serde_json::from_str::<Value>(&text) {
                let bids = json["bids"].as_array();
                let asks = json["asks"].as_array();

                if let (Some(bids), Some(asks)) = (bids, asks) {
                    let mut total_bid_vol = 0.0;
                    let mut total_ask_vol = 0.0;

                    let best_bid = bids.first().and_then(|b| b[0].as_str()).unwrap_or("0").parse::<f64>().unwrap_or(0.0);
                    let best_ask = asks.first().and_then(|a| a[0].as_str()).unwrap_or("0").parse::<f64>().unwrap_or(0.0);

                    for b in bids { total_bid_vol += b[1].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0); }
                    for a in asks { total_ask_vol += a[1].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0); }

                    let obi = if total_bid_vol + total_ask_vol > 0.0 {
                        (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)
                    } else {
                        0.0
                    };

                    // Wall-clock seconds, matching the old Python bridge's time.time().
                    let t = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .map(|d| d.as_secs_f64())
                        .unwrap_or(0.0);
                    let mid_price = (best_bid + best_ask) / 2.0;

                    // Drive the C++ core directly (was: UDP blast -> Python bridge).
                    engine.on_market_data("BTC", t, mid_price, mid_price, mid_price, mid_price);
                    engine.send_micro(t, "BINANCE_L2", best_bid, best_ask, false);

                    tick_count += 1;
                    if tick_count % 20 == 0 {
                        let equity = engine.total_equity();
                        println!(
                            "[Core Sync {tick_count:>4}]  Bid: {best_bid:.2} | Ask: {best_ask:.2} | OBI: {obi:+.4} | Spread: {:.2} | Equity: {equity:.2}",
                            best_ask - best_bid
                        );
                        if obi > 0.6 {
                            println!("   >>> [Signal] Extreme Buy Pressure (OBI={obi:+.4}).");
                        } else if obi < -0.6 {
                            println!("   >>> [Signal] Extreme Sell Wall (OBI={obi:+.4}).");
                        }
                    }
                }
            }
        }
    }
    Ok(())
}