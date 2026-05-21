// include/RegimeDetector.h

#pragma once
#include <vector>
#include <string>

enum class MarketState {
    BEAR = 0,
    SIDEWAYS = 1,
    BULL = 2,
    UNKNOWN = -1
};

struct RegimeResult {
    int state_id;
    std::string state_name;
    double current_volatility;
    double current_trend;
};

class RegimeDetector {
public:
    static RegimeResult DetectRegime(const std::vector<double>& prices, int window_size = 20);
};