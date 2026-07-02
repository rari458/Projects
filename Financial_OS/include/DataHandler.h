// include/DataHandler.h

#pragma once
#include <string>
#include <unordered_map>
#include <vector>

class DataHandler {
public:
    void add_bar(const std::string& symbol, double open, double high, double low, double close) {
        opens_[symbol].push_back(open);
        highs_[symbol].push_back(high);
        lows_[symbol].push_back(low);
        closes_[symbol].push_back(close);
    }

    [[nodiscard]] const std::vector<double>& opens(const std::string& symbol) const { return opens_.at(symbol); }
    [[nodiscard]] const std::vector<double>& highs(const std::string& symbol) const { return highs_.at(symbol); }
    [[nodiscard]] const std::vector<double>& lows(const std::string& symbol) const { return lows_.at(symbol); }
    [[nodiscard]] const std::vector<double>& closes(const std::string& symbol) const { return closes_.at(symbol); }

    [[nodiscard]] bool has_closes(const std::string& symbol) const { return closes_.count(symbol) > 0; }

private:
    std::unordered_map<std::string, std::vector<double>> opens_;
    std::unordered_map<std::string, std::vector<double>> highs_;
    std::unordered_map<std::string, std::vector<double>> lows_;
    std::unordered_map<std::string, std::vector<double>> closes_;
};

