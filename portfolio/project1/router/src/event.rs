//! The Rust half of the payload contract (DESIGN.md §13).
//! 
//! This declaration is one of two. The C++ one is market_event.hpp, and nothing
//! generated ties them together: both assert the same literal offsets,
//! so reordering a field here fails this build rather than corrupting a run.

/// Bumped whenever the layout or the meaning of a field changes.
pub const SCHEMA_VERSION: u32 = 1;

pub mod event_type
{
    pub const TRADE: u8 = 0;
    pub const SNAPSHOT: u8 = 1;
    pub const UPDATE: u8 = 2;
}

pub mod side
{
    pub const BID: u8 = 0;
    pub const ASK: u8 = 1;
}

pub mod flag
{
    pub const SNAPSHOT_BEGIN: u8 = 1 << 0;
    pub const SNAPSHOT_END: u8 = 1 << 1;
    pub const AGGRESSOR_BUY: u8 = 1 << 2;
    /// Set here, not in the engine: exchange-specific sequencing is parse-time
    /// knowledge, and the engine must not learn one exchange's dialect to find
    /// out that its book is wrong.
    pub const GAP_BEFORE: u8 = 1 << 3;
}

#[repr(C, align(64))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct MarketEvent
{
    /// Index into INSTRUMENTS; 0 is reserved as invalid.
    pub instrument_id: u32,
    pub event_type: u8,
    pub side: u8,
    pub flags: u8,
    pub reserved0: u8,

    /// The exchange's own update id, for gap detection.
    pub exchange_seq: u64,
    /// Nanoseconds since the Unix epoch, on the EXCHANGE's clock. Anything
    /// derived from it is a data-quality metric, not a latency measurement.
    pub exchange_ts: u64,
    /// Raw TSC on this core, stamped at receipt. Deliverable §7.1 is the
    /// difference between this and the engine's TSC at LOB update.
    pub local_ts: u64,

    /// L3 order identity; 0 when the feed is L2-only.
    pub order_id: u64,
    /// Whole ticks of this instrument. Never a float: §5 indexes price levels
    /// by tick, and a rounding convention that differs in the last bit between
    /// the two sides produces a plausible book rather than an error.
    pub price_ticks: i64,
    /// Smallest quantity unit. On an Update this is the new ABSOLUTE resting
    /// size at the level, and 0 removes the level.
    pub quantity: i64,
    pub reserved1: u64, 
}

const _: () = assert!(core::mem::size_of::<MarketEvent>() == 64);
const _: () = assert!(core::mem::align_of::<MarketEvent>() == 64);
const _: () = assert!(core::mem::offset_of!(MarketEvent, instrument_id) == 0);
const _: () = assert!(core::mem::offset_of!(MarketEvent, event_type) == 4);
const _: () = assert!(core::mem::offset_of!(MarketEvent, side) == 5);
const _: () = assert!(core::mem::offset_of!(MarketEvent, flags) == 6);
const _: () = assert!(core::mem::offset_of!(MarketEvent, reserved0) == 7);
const _: () = assert!(core::mem::offset_of!(MarketEvent, exchange_seq) == 8);
const _: () = assert!(core::mem::offset_of!(MarketEvent, exchange_ts) == 16);
const _: () = assert!(core::mem::offset_of!(MarketEvent, local_ts) == 24);
const _: () = assert!(core::mem::offset_of!(MarketEvent, order_id) == 32);
const _: () = assert!(core::mem::offset_of!(MarketEvent, price_ticks) == 40);
const _: () = assert!(core::mem::offset_of!(MarketEvent, quantity) == 48);
const _: () = assert!(core::mem::offset_of!(MarketEvent, reserved1) == 56);