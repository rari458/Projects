// market_event.hpp -- the C++ half of the payload contract (DESIGN.md §13).
//
// This declaration is one of two. The Rust one is router/src/event.rs, and
// nothing generated ties them together: the offsets below are asserted against
// literals on both sides, so reordering a field fails that side's build.
// A mismatch that reached a run would corrupt every downstream number instead of
// erroring, which is why the asserts are not optional.

#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace mkt
{

// Bumped whenever the layout or the meaning of a field changes. Written into
// the ring header so a stale segment is refused rather than reinterpreted.
inline constexpr uint32_t kSchemaVersion = 1;

enum class EventType : uint8_t
{
    Trade = 0,
    Snapshot = 1,
    Update = 2
};

enum class Side : uint8_t
{
    Bid = 0,
    Ask = 1,
};

namespace flag
{
inline constexpr uint8_t kSnapshotBegin = 1u << 0;
inline constexpr uint8_t kSnapshotEnd = 1u << 1;
inline constexpr uint8_t kAggressorBuy = 1u << 2; // Trade only
// Set by the router when exchange_seq skipped. The router owns this because
// exchange-specific sequencing (Binance's U/u ranges, and so on) is parse-time
// knowledge, and the engine must not have to learn one exchange's dialect to
// find out that its book is wrong.
inline constexpr uint8_t kGapBefore = 1u << 3;
} // namespace flag

// The fields are raw integers rather than the enums above: what crosses the
// segment is bytes, and the enums name the values without claiming the wire
// format is a C++ type.
struct alignas(64) MarketEvent
{
    uint32_t instrument_id; // index into the generated table; 0 is valid
    uint8_t event_type;     // EventType
    uint8_t side;           // Side
    uint8_t flags;          // flag::*
    uint8_t reserved0;      // explicit, zeroed

    uint64_t exchange_seq; // the exchange's own update id
    uint64_t exchange_ts;  // ns since the Unix epoch, EXCHANGE clock
    uint64_t local_ts;     // raw TSC on the router's core, stamped at receipt

    uint64_t order_id;   // L3 identity; 0 when the feed is L2-only
    int64_t price_ticks; // whole ticks of this instrument, never a float
    int64_t quantity;    // smallest quantity unit; on Update this is the new ABSOLUTE resting size, and 0 removes the level

    uint64_t reserved1; // explicit, zeroed
};

static_assert(sizeof(MarketEvent) == 64, "one event is one cache line");
static_assert(alignof(MarketEvent) == 64, "one event is one cache line");
static_assert(std::is_trivially_copyable_v<MarketEvent>, "a slot is published by a plain store");
static_assert(std::is_standard_layout_v<MarketEvent>, "offsetof must be well defined");

static_assert(offsetof(MarketEvent, instrument_id) == 0, "layout drift");
static_assert(offsetof(MarketEvent, event_type) == 4, "layout drift");
static_assert(offsetof(MarketEvent, side) == 5, "layout drift");
static_assert(offsetof(MarketEvent, flags) == 6, "layout drift");
static_assert(offsetof(MarketEvent, reserved0) == 7, "layout drift");
static_assert(offsetof(MarketEvent, exchange_seq) == 8, "layout drift");
static_assert(offsetof(MarketEvent, exchange_ts) == 16, "layout drift");
static_assert(offsetof(MarketEvent, local_ts) == 24, "layout drift");
static_assert(offsetof(MarketEvent, order_id) == 32, "layout drift");
static_assert(offsetof(MarketEvent, price_ticks) == 40, "layout drift");
static_assert(offsetof(MarketEvent, quantity) == 48, "layout drift");
static_assert(offsetof(MarketEvent, reserved1) == 56, "layout drift");

} // namespace mkt