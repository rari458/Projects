// layout_dump.cpp -- print the C++ view of the shared-memory contract.
//
// The static_asserts in ring.hpp and market_event.hpp are what make a mismatch
// a build failure. This exists for the other half of §10: a human comparing the
// two declarations, and a CI job diffing this output against a recorded copy.

#include "market_event.hpp"
#include "ring.hpp"

#include <cstddef>
#include <cstdio>

#define ROW(s, f) std::printf("  %-16s %3zu %3zu\n", #f, offsetof(s, f), sizeof(s::f))

int main()
{
    std::printf("ring::Header  size=%zu align=%zu\n", sizeof(ring::Header), alignof(ring::Header));
    std::printf("  %-16s %3zu\n", "stat", offsetof(ring::Header, stat));
    std::printf("  %-16s %3zu\n", "prod", offsetof(ring::Header, prod));
    std::printf("  %-16s %3zu\n", "cons", offsetof(ring::Header, cons));
    std::printf("  slot_bytes=%u header_bytes=%zu\n\n", ring::kSlotBytes, ring::kHeaderBytes);
    std::printf(
        "mkt::MarketEvent  size=%zu align=%zu schema_version=%u\n",
        sizeof(mkt::MarketEvent), alignof(mkt::MarketEvent), mkt::kSchemaVersion);
    std::printf("  %-16s %3s %3s\n", "field", "off", "sz");
    ROW(mkt::MarketEvent, instrument_id);
    ROW(mkt::MarketEvent, event_type);
    ROW(mkt::MarketEvent, side);
    ROW(mkt::MarketEvent, flags);
    ROW(mkt::MarketEvent, reserved0);
    ROW(mkt::MarketEvent, exchange_seq);
    ROW(mkt::MarketEvent, exchange_ts);
    ROW(mkt::MarketEvent, local_ts);
    ROW(mkt::MarketEvent, order_id);
    ROW(mkt::MarketEvent, price_ticks);
    ROW(mkt::MarketEvent, quantity);
    ROW(mkt::MarketEvent, reserved1);
    return 0;
}