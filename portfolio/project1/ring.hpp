// ring.hpp -- the SPSC shared-memory ring specified by DESIGN.md
//
// This header IS the C++ half of the contract. Every constant and every offset
// here has a counterpart in the Rust router, and DESIGN.md §10 exists because
// nothing but a compile-time assert and a CI offset dump ties the two together.
//
// The ring treats a slot as kSlotBytes opaque bytes. What goes inside is a
// separate contract; §8 lists the four properties the ring fixes about it.

#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <new>

namespace ring {
inline constexpr uint64_t kMagic = 0x52494e4730303031ull; // "RING0001"
inline constexpr uint32_t kVersion = 1;
inline constexpr uint32_t kSlotBytes = 64;
inline constexpr size_t kRegionBytes = 128;

// Recorded in the header so that a segment stamped with one clock is never
// compared against numbers taken with another. §9 settled on Rdtscp; the rest
// exist so the mismatch is loud rather than silent.
enum class ClockId : uint32_t {
    Rdtscp = 1,
    ClockMonotonic = 2,
    ClockMonotonicRaw = 3
};

// Lets the consumer tell "router not started yet" from "router exited" without
// a timeout heuristic (§6).
enum class ProducerState : uint32_t {
    NotStarted = 0,
    Running = 1,
    Exited = 2,
};

// Three 128 B regions grouped by writer. False sharing is a property of writes,
// so the grouping that matters is which side dirties the line -- not which
// fields are conceptually related. See DESIGN.md §1.
struct Header {
    // Written at init, read-only for the life of the segment. Shares no line
    // with anything mutable, so the validation attach() performs never touches
    // a line either side is writing.
    struct alignas(kRegionBytes) StaticBlock {
        std::atomic<uint64_t> magic; // atomic so that init can publish it last
        uint32_t version;
        uint32_t slot_bytes;
        uint64_t capacity; // power of two, validated at init
        uint32_t clock_id;
        uint32_t reserved;
    } stat;

    // Producer-written. dropped_count moves only on a drop and producer_state
    // twice per run, so they cost the consumer -- which reads all three and
    // writes none -- nothing here, and save a region.
    struct alignas(kRegionBytes) ProducerBlock {
        std::atomic<uint64_t> write_idx;
        std::atomic<uint64_t> dropped_count;
        std::atomic<uint32_t> producer_state;
    } prod;

    // Consumer-written.
    struct alignas(kRegionBytes) ConsumerBlock {
        std::atomic<uint64_t> read_idx;
    } cons;
};

inline constexpr size_t kHeaderBytes = sizeof(Header);

static_assert(sizeof(Header::StaticBlock) == kRegionBytes,
              "static block must own its region");
static_assert(sizeof(Header::ProducerBlock) == kRegionBytes,
              "producer block must own its region");
static_assert(sizeof(Header::ConsumerBlock) == kRegionBytes,
              "consumer block must own its region");
static_assert(sizeof(Header) == 3 * kRegionBytes,
              "header is exactly three regions");
static_assert(offsetof(Header, prod) == kRegionBytes, "producer block at 128");
static_assert(offsetof(Header, cons) == 2 * kRegionBytes,
              "consumer block at 256");
static_assert(kHeaderBytes % kSlotBytes == 0,
              "slot array must start slot-aligned");
static_assert(std::atomic<uint64_t>::is_always_lock_free,
              "a lock in the header is not a ring");

inline constexpr size_t segment_bytes(uint64_t capacity) {
    return kHeaderBytes + static_cast<size_t>(capacity) * kSlotBytes;
}

// The engine creates and sizes the segment; the router only ever attaches (§6).
inline Header *init(void *base, uint64_t capacity, ClockId clock) {
    if (capacity == 0 || (capacity & (capacity - 1)) != 0) {
        std::fprintf(stderr, "ring: capacity %llu is not a power of two\n",
                     static_cast<unsigned long long>(capacity));
        std::abort();
    }
    if (reinterpret_cast<uintptr_t>(base) % kRegionBytes != 0) {
        std::fprintf(stderr, "ring: segment base is not %zu-byte aligned\n",
                     kRegionBytes);
        std::abort();
    }

    Header *h = new (base) Header{};
    h->prod.write_idx.store(0, std::memory_order_relaxed);
    h->prod.dropped_count.store(0, std::memory_order_relaxed);
    h->prod.producer_state.store(
        static_cast<uint32_t>(ProducerState::NotStarted),
        std::memory_order_relaxed);
    h->cons.read_idx.store(0, std::memory_order_relaxed);
    h->stat.version = kVersion;
    h->stat.slot_bytes = kSlotBytes;
    h->stat.capacity = capacity;
    h->stat.clock_id = static_cast<uint32_t>(clock);
    h->stat.reserved = 0;

    // Magic goes last with a Release. A router attaching mid-init would
    // otherwise validate against a capacity that has not been written yet and
    // pass, which is the exact silent failure §6 exists to prevent.
    h->stat.magic.store(kMagic, std::memory_order_release);
    return h;
}

namespace detail {
inline bool check(const char *field, uint64_t got, uint64_t want) {
    if (got == want) return true;
    std::fprintf(
        stderr,
        "ring: %s mismatch -- segment has %llu, this build expects %llu\n",
        field, static_cast<unsigned long long>(got),
        static_cast<unsigned long long>(want));
    return false;
}
} // namespace detail

// A mismatch is a hard failure, never a warning (§6). Every field checked here
// is one whose silent disagreement corrupts results instead of erroring, which
// is why this aborts rather than returning a status nobody checks.
inline Header *attach(void *base, uint64_t expect_capacity,
                      ClockId expect_clock) {
    Header *h = static_cast<Header *>(base);
    bool ok = true;
    ok &= detail::check("magic", h->stat.magic.load(std::memory_order_acquire),
                        kMagic);
    ok &= detail::check("version", h->stat.version, kVersion);
    ok &= detail::check("slot_bytes", h->stat.slot_bytes, kSlotBytes);
    ok &= detail::check("capacity", h->stat.capacity, expect_capacity);
    ok &= detail::check("clock_id", h->stat.clock_id,
                        static_cast<uint32_t>(expect_clock));
    if (!ok) {
        std::fprintf(stderr, "ring: refusing to attach. This is a stale "
                             "segment or a version-skewed "
                             "binary; continuing would corrupt every number "
                             "downstream rathere than "
                             "produce an error.\n");
        std::abort();
    }
    return h;
}

// The producer's view. Its own index lives here, not in the segment: the
// producer never reads back what it published (§4).
class Producer {
  public:
    explicit Producer(Header *h) noexcept
        : h_(h), slots_(reinterpret_cast<uint8_t *>(h) + kHeaderBytes),
          capacity_(h->stat.capacity), mask_(h->stat.capacity - 1),
          write_idx_(h->prod.write_idx.load(std::memory_order_relaxed)),
          cached_read_idx_(h->cons.read_idx.load(std::memory_order_acquire)) {
        h_->prod.producer_state.store(
            static_cast<uint32_t>(ProducerState::Running),
            std::memory_order_release);
    }

    // The slot to write, or nullptr when the ring is full. The consumer's line
    // is touched only when the cached copy says it has to be -- without that,
    // every push becomes a cross-core transfer (§4).
    uint8_t *claim() noexcept {
        if (write_idx_ - cached_read_idx_ == capacity_) {
            cached_read_idx_ =
                h_->cons.read_idx.load(std::memory_order_acquire);
            if (write_idx_ - cached_read_idx_ == capacity_) return nullptr;
        }
        return slots_ + (write_idx_ & mask_) * kSlotBytes;
    }

    // Publishes what claim() handed out. The Release is what makes the payload
    // visible; the payload itself needs no atomics. On x86-64 this is a plain
    // MOV and exists for the compiler (§3).
    void publish() noexcept {
        h_->prod.write_idx.store(++write_idx_, std::memory_order_release);
    }

    void finish() noexcept {
        h_->prod.producer_state.store(
            static_cast<uint32_t>(ProducerState::Exited),
            std::memory_order_release);
    }

  private:
    Header *h_;
    uint8_t *slots_;
    uint64_t capacity_;
    uint64_t mask_;
    uint64_t write_idx_;
    uint64_t cached_read_idx_;
};

// The consumer's view. available() is the only cross-core read; peek() and
// pop() touch nothing shared, which is what lets one Acquire cover a whole
// batch (§4).
class Consumer {
  public:
    explicit Consumer(Header *h) noexcept
        : h_(h), slots_(reinterpret_cast<uint8_t *>(h) + kHeaderBytes),
          mask_(h->stat.capacity - 1),
          read_idx_(h->cons.read_idx.load(std::memory_order_relaxed)),
          cached_write_idx_(0) {}

    uint64_t available() noexcept {
        cached_write_idx_ = h_->prod.write_idx.load(std::memory_order_acquire);
        return cached_write_idx_ - read_idx_;
    }

    const uint8_t *peek() const noexcept {
        return slots_ + (read_idx_ & mask_) * kSlotBytes;
    }

    // Advances the private index only; the slot is not yet free.
    void pop() noexcept { ++read_idx_; }

    // Frees every slot popped since the last call. One Release per batch.
    void commit() noexcept {
        h_->cons.read_idx.store(read_idx_, std::memory_order_release);
    }

  private:
    Header *h_;
    uint8_t *slots_;
    uint64_t mask_;
    uint64_t read_idx_;
    uint64_t cached_write_idx_;
};

} // namespace ring
