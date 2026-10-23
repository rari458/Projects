//! Data Router (Rust). At this stage the crate carries only the shared-memory
//! contract: the payload declaration and the generated instrument table.
//! The tokio WebSocket ingestion of §3 lands on top of these.

pub mod event;
pub mod instruments_generated;