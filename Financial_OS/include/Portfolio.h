// include/Portfolio.h

#pragma once
#include <string>
#include <unordered_map>
#include <vector>

struct Trade {
    int id;
    std::string symbol;
    std::string side;
    double quantity;
    double price;
    double commission;
    double timestamp;
};

class Portfolio {
public:
    explicit Portfolio(double initial_capital) : cash_(initial_capital) {}

    void mark(const std::string& symbol, double price) { last_price_[symbol] = price; }

    void execute(const std::string& symbol, const std::string& side,
                 double quantity, double price, double timestamp) {
        if (quantity <= 0) return;

        double commission = quantity * price * 0.0001;

        if (side == "BUY") {
            cash_ -= (quantity * price + commission);
            holdings_[symbol] += quantity;
            trades_.push_back({(int)trades_.size(), symbol, "BUY", quantity, price, commission, timestamp});
        } else if (side == "SELL") {
            cash_ += (quantity * price - commission);
            holdings_[symbol] -= quantity;
            trades_.push_back({(int)trades_.size(), symbol, "SELL", quantity, price, commission, timestamp});
        }
    }

    [[nodiscard]] double total_equity() const {
        double total = cash_ + custom_pnl_;
        for (const auto& [sym, qty] : holdings_) {
            if (last_price_.count(sym)) {
                total += qty * last_price_.at(sym);
            }
        }
        return total;
    }

    [[nodiscard]] double holding(const std::string& symbol) const {
        if (holdings_.count(symbol)) return holdings_.at(symbol);
        return 0.0;
    }

    [[nodiscard]] double cash() const { return cash_; }
    void set_custom_pnl(double pnl) { custom_pnl_ = pnl; }

    [[nodiscard]] const std::unordered_map<std::string, double>& holdings() const { return holdings_; }
    [[nodiscard]] const std::vector<Trade>& trades() const { return trades_; }

    [[nodiscard]] double last_price(const std::string& symbol) const {
        auto it = last_price_.find(symbol);
        return it != last_price_.end() ? it->second : 0.0;
    }

private:
    double cash_;
    double custom_pnl_ = 0.0;
    std::unordered_map<std::string, double> holdings_;
    std::unordered_map<std::string, double> last_price_;
    std::vector<Trade> trades_;
};
