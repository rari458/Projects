use futures_util::StreamExt;
use serde_json::Value;
use std::sync::Arc;
use tokio::net::UdpSocket;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let url = "wss://stream.binance.com:9443/ws/btcusdt@depth5@100ms";
    let (ws_stream, _) = connect_async(url).await.expect("Failed to connect to Binance L2 WS");
    println!("-> [Rust Microstructure Engine] Connected to Binance L2 Orderbook.");

    let (_, mut read) = ws_stream.split();
    
    // Let Tokio handle address resolution natively. Avoid manual string parsing.
    let udp_socket = Arc::new(UdpSocket::bind("127.0.0.1:0").await.expect("Failed to bind UDP socket"));
    let target_addr = "127.0.0.1:9999";

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

                    let payload = format!("{:.2},{:.2},{:.4}", best_bid, best_ask, obi);
                    
                    // Fire-and-forget UDP blast
                    let _ = udp_socket.send_to(payload.as_bytes(), target_addr).await;
                }
            }
        }
    }
    Ok(())
}