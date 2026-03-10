// include/OrderBook.h

#ifndef ORDERBOOK_H
#define ORDERBOOK_H

#include <map>
#include <string>
#include <vector>
#include <cstdint>

struct Order {
    uint64_t order_id;
    double price;
    double quantity;
    bool is_buy;
    double timestamp;
};

struct TapeRecord {
    double price;
    double quantity;
    bool is_buy_initiated;
    double timestamp;
};

class OrderBook {
public:
    OrderBook(std::string symbol);

    void add_order(uint64_t order_id, double price, double quantity, bool is_buy, double timestamp);
    void modify_order(uint64_t order_id, double new_quantity, double timestamp);
    void cancel_order(uint64_t order_id, double timestamp);
    void execute_trade(double price, double quantity, double timestamp);
    void record_trade(double price, double quantity, bool is_buy_initiated, double timestamp);
    void clear_tape();

    double get_best_bid() const;
    double get_best_ask() const;
    double get_mid_price() const;
    double calculate_imbalance(int levels = 5) const;
    double calculate_vpin(double bucket_vol_size, int num_buckets) const;
    double calculate_vwap() const;

private:
    std::string symbol_;

    std::map<double, double, std::greater<double>> bids_;

    std::map<double, double> asks_;

    std::map<uint64_t, Order> order_map_;

    void remove_empty_levels(double price, bool is_buy);

    std::vector<TapeRecord> tape_;
};

#endif