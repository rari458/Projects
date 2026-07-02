// src/EngineCApi.cpp
//
// C ABI implementation. Every entry point (a) treats a NULL handle as a no-op
// and (b) swallows C++ exceptions -- letting one escape across an extern "C"
// boundary is undefined behaviour. C++ objects never cross the wall; only
// primitives and opaque pointers do.

#include "EngineCApi.h"
#include <string>
#include "Backtester.h"

namespace {
Backtester* as_bt(FosBacktester h) { return static_cast<Backtester*>(h); }
}  // namespace

extern "C" {

FosBacktester fos_bt_new(double capital, const char* strategy, double leverage) {
    try {
        return new Backtester(capital, strategy ? std::string(strategy) : std::string("EMA"), leverage);
    } catch (...) {
        return nullptr;
    }
}

void fos_bt_free(FosBacktester h) {
    delete as_bt(h);
}

void fos_bt_set_regime_filter(FosBacktester h, int use_filter, int lookback) {
    if (!h) return;
    try {
        as_bt(h)->set_regime_filter(use_filter != 0, lookback);
    } catch (...) {
    }
}

void fos_bt_on_market_data(FosBacktester h, const char* symbol,
                           double t, double open, double high, double low, double close) {
    if (!h || !symbol) return;
    try {
        as_bt(h)->on_market_data(symbol, t, open, high, low, close);
    } catch (...) {
    }
}

void fos_bt_send_micro(FosBacktester h, double t, const char* exchange,
                       double bid, double ask, int is_cancel) {
    if (!h) return;
    try {
        as_bt(h)->send_event(MicrostructureMessage{
            t, exchange ? std::string(exchange) : std::string(), bid, ask, is_cancel != 0});
    } catch (...) {
    }
}

double fos_bt_total_equity(FosBacktester h) {
    if (!h) return 0.0;
    try {
        return as_bt(h)->get_total_equity();
    } catch (...) {
        return 0.0;
    }
}

double fos_bt_holdings(FosBacktester h, const char* symbol) {
    if (!h || !symbol) return 0.0;
    try {
        return as_bt(h)->get_holdings(symbol);
    } catch (...) {
        return 0.0;
    }
}

}  // extern "C"