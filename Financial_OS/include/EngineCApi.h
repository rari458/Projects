// include/EngineCApi.h
// Stable C ABI over the C++ Backtester so non-C++ callers (the Rust market-data
// feeder) can drive the engine directly across an FFI boundary -- no UDP, no
// Python. The engine lives behind an opaque handle; all C++ types and exceptions
// stay on the C++ side of this wall.

#ifndef ENGINE_C_API_H
#define ENGINE_C_API_H

#ifdef __cplusplus
extern "C" {
#endif

// Opaque handle to a heap-allocated Backtester (NULL on allocation failure).
typedef void* FosBacktester;

FosBacktester fos_bt_new(double capital, const char* strategy, double leverage);
void          fos_bt_free(FosBacktester h);

// Booleans cross the boundary as int (0/1) to avoid C _Bool ABI ambiguity.
void   fos_bt_set_regime_filter(FosBacktester h, int use_filter, int lookback);
void   fos_bt_on_market_data(FosBacktester h, const char* symbol,
                             double t, double open, double high, double low, double close);
double fos_bt_total_equity(FosBacktester h);
double fos_bt_holdings(FosBacktester h, const char* symbol);

#ifdef __cplusplus
}
#endif

#endif  // ENGINE_C_API_H