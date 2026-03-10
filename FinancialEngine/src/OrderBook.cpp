// src/OrderBook.cpp

#include "../include/OrderBook.h"
#include <numeric>
#include <cmath>
#include <vector>

OrderBook::OrderBook(std::string symbol) : symbol_(symbol) {}

void OrderBook::add_order(uint64_t order_id, double price, double quantity, bool is_buy, double timestamp) {
    Order new_order = {order_id, price, quantity, is_buy, timestamp};
    order_map_[order_id] = new_order;

    if (is_buy) {
        bids_[price] += quantity;
    } else {
        asks_[price] += quantity;
    }
}

void OrderBook::cancel_order(uint64_t order_id, double timestamp) {
    (void)timestamp;
    auto it = order_map_.find(order_id);
    if (it != order_map_.end()) {
        const Order& ord = it->second;
        if (ord.is_buy) {
            bids_[ord.price] -= ord.quantity;
            remove_empty_levels(ord.price, true);
        } else {
            asks_[ord.price] -= ord.quantity;
            remove_empty_levels(ord.price, false);
        }
        order_map_.erase(it);
    }
}

void OrderBook::remove_empty_levels(double price, bool is_buy) {
    if (is_buy) {
        if (bids_[price] <= 1e-6) bids_.erase(price);
    } else {
        if (asks_[price] <= 1e-6) asks_.erase(price);
    }
}

void OrderBook::record_trade(double price, double quantity, bool is_buy_initiated, double timestamp) {
    tape_.push_back({price, quantity, is_buy_initiated, timestamp});
}

void OrderBook::clear_tape() {
    tape_.clear();
}

void OrderBook::modify_order(uint64_t order_id, double new_quantity, double timestamp) {
    (void)timestamp;
    auto it = order_map_.find(order_id);
    if (it != order_map_.end()) {
        Order& ord = it->second;
        double qty_diff = new_quantity - ord.quantity;
        ord.quantity = new_quantity;

        if (ord.is_buy) {
            bids_[ord.price] += qty_diff;
            remove_empty_levels(ord.price, true);
        } else {
            asks_[ord.price] += qty_diff;
            remove_empty_levels(ord.price, false);
        }

        if (new_quantity <= 1e-6) {
            order_map_.erase(it);
        }
    }
}

void OrderBook::execute_trade(double price, double quantity, double timestamp) {
    double best_bid = get_best_bid();
    double best_ask = get_best_ask();
    bool is_buy_initiated = true;

    if (best_ask > 0.0 && price >= best_ask) {
        is_buy_initiated = true;
        asks_[price] -= quantity;
        remove_empty_levels(price, false);
    } else if (best_bid > 0.0 && price <= best_bid) {
        is_buy_initiated = false;
        bids_[price] -= quantity;
        remove_empty_levels(price, true);
    }

    record_trade(price, quantity, is_buy_initiated, timestamp);
}

double OrderBook::get_best_bid() const {
    if (bids_.empty()) return 0.0;
    return bids_.begin()->first;
}

double OrderBook::get_best_ask() const {
    if (asks_.empty()) return 0.0;
    return asks_.begin()->first;
}

double OrderBook::get_mid_price() const {
    double best_bid = get_best_bid();
    double best_ask = get_best_ask();
    if (best_bid > 0.0 && best_ask > 0.0) {
        return (best_bid + best_ask) / 2.0;
    }
    return 0.0;
}

double OrderBook::calculate_imbalance(int levels) const {
    double bid_vol = 0.0;
    double ask_vol = 0.0;

    int count = 0;
    for (auto it = bids_.begin(); it != bids_.end() && count < levels; ++it, ++count) {
        bid_vol += it->second;
    }

    count = 0;
    for (auto it = asks_.begin(); it != asks_.end() && count < levels; ++it, ++count) {
        ask_vol += it->second;
    }

    double total_vol = bid_vol + ask_vol;
    if (total_vol <= 1e-6) return 0.0;

    return (bid_vol - ask_vol) / total_vol;
}

double OrderBook::calculate_vpin(double bucket_vol_size, int num_buckets) const {
    if (tape_.empty() || bucket_vol_size <= 0.0 || num_buckets <= 0) return 0.0;

    std::vector<double> bucket_imbalances;
    double current_buy_vol = 0.0;
    double current_sell_vol = 0.0;
    double current_total_vol = 0.0;

    for (const auto& trade : tape_) {
        if (trade.is_buy_initiated) {
            current_buy_vol += trade.quantity;
        } else {
            current_sell_vol += trade.quantity;
        }

        current_total_vol += trade.quantity;

        if (current_total_vol >= bucket_vol_size) {
            bucket_imbalances.push_back(std::abs(current_buy_vol - current_sell_vol));
            current_buy_vol = 0.0;
            current_sell_vol = 0.0;
            current_total_vol = 0.0;
        }
    }

    if (bucket_imbalances.size() < static_cast<size_t>(num_buckets)) {
        return 0.0;
    }

    double total_imbalance = 0.0;
    size_t start_idx = bucket_imbalances.size() - num_buckets;

    for (size_t i = start_idx; i < bucket_imbalances.size(); ++i) {
        total_imbalance += bucket_imbalances[i];
    }

    return total_imbalance / (num_buckets * bucket_vol_size);
}

double OrderBook::calculate_vwap() const {
    if (tape_.empty()) return 0.0;

    double cumulative_vol_price = 0.0;
    double cumulative_vol = 0.0;

    for (const auto& trade : tape_) {
        cumulative_vol_price += (trade.price * trade.quantity);
        cumulative_vol += trade.quantity;
    }

    if (cumulative_vol <= 1e-6) return 0.0;
    return cumulative_vol_price / cumulative_vol;
}