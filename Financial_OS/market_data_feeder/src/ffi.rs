// market_data_feeder/src/ffi.rs
//
// Safe Rust wrapper over the C++ engine's C ABI (see include/EngineCApi.h).
// The raw extern "C" surface is unsafe; `Engine` is the safe RAII front: it owns
// the opaque handle, frees it on Drop, and hands C strings across the boundary
// with correct lifetimes. Exceptions are already firewalled on the C++ side.
#![allow(dead_code)] // Wired into the live loop in Stage 3; used by tests untill then.

use std::ffi::{c_char, c_double, c_int, c_void, CString};

unsafe extern "C" {
    fn fos_bt_new(capital: c_double, strategy: *const c_char, leverage: c_double) -> *mut c_void;
    fn fos_bt_free(h: *mut c_void);
    fn fos_bt_set_regime_filter(h: *mut c_void, use_filter: c_int, lookback: c_int);
    fn fos_bt_on_market_data(
        h: *mut c_void,
        symbol: *const c_char,
        t: c_double,
        open: c_double,
        high: c_double,
        low: c_double,
        close: c_double,
    );
    fn fos_bt_send_micro(
        h: *mut c_void,
        t: c_double,
        exchange: *const c_char,
        bid: c_double,
        ask: c_double,
        is_cancel: c_int,
    );
    fn fos_bt_total_equity(h: *mut c_void) -> c_double;
    fn fos_bt_holdings(h: *mut c_void, symbol: *const c_char) -> c_double;
}

pub struct Engine {
    handle: *mut c_void,
}

// SAFETY: the Backtester is not thread-safe, but `Engine` only ever grants
// exclusive (&mut) access, so it is never touched concurrently. Moving ownership
// between threads (e.g. when a multi-threaded Tokio runtime migrates the driver
// task) is sound. We deliberately do NOT implement Sync.
unsafe impl Send for Engine {}

impl Engine {
    pub fn new(capital: f64, strategy: &str, leverage: f64) -> Option<Engine> {
        let c_strategy = CString::new(strategy).ok()?;
        // SAFETY: c_strategy outlives the call; C++ copies the string.
        let handle = unsafe { fos_bt_new(capital, c_strategy.as_ptr(), leverage) };
        if handle.is_null() {
            None
        } else {
            Some(Engine { handle })
        }
    }

    pub fn set_regime_filter(&mut self, use_filter: bool, lookback: i32) {
        unsafe { fos_bt_set_regime_filter(self.handle, use_filter as c_int, lookback as c_int) }
    }

    pub fn on_market_data(&mut self, symbol: &str, t: f64, open: f64, high: f64, low: f64, close: f64) {
        // A NUL byte would silently truncate the C string; drop such a tick.
        let Ok(c_symbol) = CString::new(symbol) else { return };
        unsafe { fos_bt_on_market_data(self.handle, c_symbol.as_ptr(), t, open, high, low, close) }
    }

    pub fn send_micro(&mut self, t: f64, exchange: &str, bid: f64, ask: f64, is_cancel: bool) {
        let Ok(c_exchange) = CString::new(exchange) else { return };
        unsafe {
            fos_bt_send_micro(self.handle, t, c_exchange.as_ptr(), bid, ask, is_cancel as c_int)
        }
    }

    pub fn total_equity(&self) -> f64 {
        unsafe { fos_bt_total_equity(self.handle) }
    }

    pub fn holdings(&self, symbol: &str) -> f64 {
        let Ok(c_symbol) = CString::new(symbol) else { return 0.0 };
        unsafe {fos_bt_holdings(self.handle, c_symbol.as_ptr()) }
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        // SAFETY: handle came from fos_bt_new and is freed exactly once.
        unsafe { fos_bt_free(self.handle) }
    }
}

#[cfg(test)]
mod tests {
    use super::Engine;

    #[test]
    fn drives_engine_via_ffi() {
        let mut engine = Engine::new(100_000.0, "L3_EXECUTION", 1.0).expect("engine construction failed");
        engine.set_regime_filter(false, 252);

        for i in 0..50 {
            let t = i as f64;
            let mid = 60_000.0 + i as f64;
            engine.on_market_data("BTC", t, mid, mid, mid, mid);
            engine.send_micro(t, "BINANCE_L2", mid - 1.0, mid + 1.0, false);
        }

        let equity = engine.total_equity();
        println!("[selftest] equity after 50 synthetic ticks = {equity}");
        // Bridge is live: constructed, driven, and read back a finite equity
        // across FFI without UB. Exact values are the C++ golden suite's concern.
        assert!(equity.is_finite());
    }
}