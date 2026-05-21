// src/Backtester.cpp

#include "../include/Backtester.h"
#include "../include/Analytics.h"
#include "../include/PCAArbitrage.h"
#include "../include/BlackScholesFormulas.h"
#include <fmt/core.h>
#include <fmt/color.h>
#include <cmath>
#include <iostream>

double update_ema_calc_multi(double current_price, double prev_ema, int period) {
    if (prev_ema < 0.0) return current_price;
    double alpha = 2.0 / (period + 1);
    return (current_price - prev_ema) * alpha + prev_ema;
}

void EMAStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)timestamp; (void) open; (void) high; (void) low;

    if (history_.find(symbol) == history_.end()) {
        current_short_ema_[symbol] = -1.0;
        current_long_ema_[symbol] = -1.0;
        history_[symbol] = {};
    }

    history_[symbol].push_back(close);
    
    current_short_ema_[symbol] = update_ema_calc_multi(close, current_short_ema_[symbol], short_window_);
    current_long_ema_[symbol] = update_ema_calc_multi(close, current_long_ema_[symbol], long_window_);

    if (history_[symbol].size() > static_cast<size_t>(long_window_)) {
        double current_holdings = engine.get_holdings(symbol);
        double s_ema = current_short_ema_[symbol];
        double l_ema = current_long_ema_[symbol];

        if (s_ema > l_ema && current_holdings <= 1e-6) {
            double cash = engine.get_cash_balance();
            double capital_to_use = cash * 0.2 * engine.get_leverage();
            if (capital_to_use > 0) {
                double qty = capital_to_use / (close * 1.001);
                engine.send_order(symbol, "BUY", qty, close, timestamp);
            }
        }
        else if (s_ema < l_ema && current_holdings > 1e-6) {
            engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
        }
    }
}

void RSIStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;
    history_[symbol].push_back(close);

    if (history_[symbol].size() <= static_cast<size_t>(period_ + 1)) return;

    double rsi = Analytics::CalculateRSI(history_[symbol], period_);
    double current_holdings = engine.get_holdings(symbol);

    if (rsi < buy_thresh_ && current_holdings <= 1e-6) {
        double cash = engine.get_cash_balance();
        double capital_to_use = cash * 0.2 * engine.get_leverage();
        if (capital_to_use > 0) {
            double qty = capital_to_use / (close * 1.001);
            engine.send_order(symbol, "BUY", qty, close, timestamp);
        }
    }
    else if (rsi > sell_thresh_ && current_holdings > 1e-6) {
        engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
    }
}

void MACDStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    if (history_.find(symbol) == history_.end()) {
        fast_ema_[symbol] = -1.0;
        slow_ema_[symbol] = -1.0;
        signal_line_[symbol] = 0.0;
        macd_line_[symbol] = 0.0;
    }

    history_[symbol].push_back(close);

    fast_ema_[symbol] = update_ema_calc_multi(close, fast_ema_[symbol], fast_period_);
    slow_ema_[symbol] = update_ema_calc_multi(close, slow_ema_[symbol], slow_period_);

    if (history_[symbol].size() >= static_cast<size_t>(slow_period_)) {
        double prev_macd = macd_line_[symbol];
        double prev_signal = signal_line_[symbol];

        macd_line_[symbol] = fast_ema_[symbol] - slow_ema_[symbol];

        if (prev_signal == 0.0) signal_line_[symbol] = macd_line_[symbol];
        else signal_line_[symbol] = (macd_line_[symbol] - prev_signal) * (2.0 / (signal_period_ + 1)) + prev_signal;

        double current_holdings = engine.get_holdings(symbol);

        if (prev_macd < prev_signal && macd_line_[symbol] > signal_line_[symbol] && current_holdings <= 1e-6) {
            double cash = engine.get_cash_balance();
            double capital_to_use = cash * 0.2 * engine.get_leverage();
            if (capital_to_use > 0) {
                double qty = capital_to_use / (close * 1.001);
                engine.send_order(symbol, "BUY", qty, close, timestamp);
            }
        }
        else if (prev_macd > prev_signal && macd_line_[symbol] < signal_line_[symbol] && current_holdings > 1e-6) {
            engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
        }
    }
}

void BollingerStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    history_[symbol].push_back(close);
    if (history_[symbol].size() < static_cast<size_t>(period_)) return;

    double sum = 0.0;
    const auto& prices = history_[symbol];
    for (int i = 0; i < period_; ++i) sum += prices[prices.size() - 1 - i];
    double sma = sum / period_;

    double variance = 0.0;
    for (int i = 0; i < period_; ++i) {
        double val = prices[prices.size() - 1 - i];
        variance += (val - sma) * (val - sma);
    }
    double std_dev = std::sqrt(variance / period_);

    double upper_band = sma + (std_dev * mult_);
    double lower_band = sma - (std_dev * mult_);

    double current_holdings = engine.get_holdings(symbol);

    if (close <= lower_band && current_holdings <= 1e-6) {
        double cash = engine.get_cash_balance();
        double capital_to_use = cash * 0.2 * engine.get_leverage();
        if (capital_to_use > 0) {
            double qty = capital_to_use / (close * 1.001);
            engine.send_order(symbol, "BUY", qty, close, timestamp);
        }
    }
    else if (close >= upper_band && current_holdings > 1e-6) {
        engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
    }
}

void VolatilityStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)low; (void)close;

    const auto& highs = engine.get_highs(symbol);
    const auto& lows = engine.get_lows(symbol);

    if (highs.size() < 2) return;

    double prev_high = highs[highs.size() - 2];
    double prev_low = lows[lows.size() - 2];
    double range = prev_high - prev_low;
    double target_price = open + (range * k_);

    double current_holdings = engine.get_holdings(symbol);

    if (current_holdings <= 1e-6) {
        double buy_price = 0.0;
        if (open >= target_price) buy_price = open;
        else if (high >= target_price) buy_price = target_price;

        if (buy_price > 0.0) {
            double cash = engine.get_cash_balance();
            double capital_to_use = cash * 0.2 * engine.get_leverage();
            if (capital_to_use > 0) {
                double qty = capital_to_use / (buy_price * 1.001);
                engine.send_order(symbol, "BUY", qty, buy_price, timestamp);
            }
        }
    }
}

void OUStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    history_[symbol].push_back(close);
    const auto& prices = history_[symbol];

    if (prices.size() <= static_cast<size_t>(window_)) return;

    double sum_x = 0.0, sum_y = 0.0, sum_xx = 0.0, sum_xy = 0.0;
    int n = window_;
    size_t start_idx = prices.size() - window_ - 1;

    for (int i = 0; i < n; ++i) {
        double x = prices[start_idx + i];
        double y = prices[start_idx + i + 1];
        sum_x += x; sum_y += y;
        sum_xx += x * x; sum_xy += x * y;
    }

    double mean_x = sum_x / n;
    double mean_y = sum_y / n;
    double b = (sum_xy - n * mean_x * mean_y) / (sum_xx - n * mean_x * mean_x);
    double a = mean_y - b * mean_x;

    if (b <= 0.0 || b >= 1.0) return;

    double mu = a / (1.0 - b);
    double sum_e2 = 0.0;
    for (int i = 0; i < n; ++i) {
        double x = prices[start_idx + i];
        double y = prices[start_idx + i + 1];
        double e = y - (a + b * x);
        sum_e2 = e * e;
    }
    double sigma_eq = std::sqrt((sum_e2 / (n - 2)) / (1.0 - b * b));
    double z_score = (close - mu) / sigma_eq;

    double current_holdings = engine.get_holdings(symbol);

    if (z_score < -z_thresh_ && current_holdings <= 1e-6) {
        double cash = engine.get_cash_balance();
        double capital_to_use = cash * 0.2 * engine.get_leverage();
        if (capital_to_use > 0) {
            double qty = capital_to_use / (close * 1.001);
            engine.send_order(symbol, "BUY", qty, close, timestamp);
        }
    } else if (z_score > 0.0 && current_holdings > 1e-6) {
        engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
    }
}

void KalmanPairsStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    if (symbol == asset_x_) buffer_x_[timestamp] = close;
    if (symbol == asset_y_) buffer_y_[timestamp] = close;

    if (buffer_x_.count(timestamp) && buffer_y_.count(timestamp)) {
        double px = buffer_x_[timestamp];
        double py = buffer_y_[timestamp];

        kf_.update(px, py);
        double spread = kf_.get_spread(px, py);
        spread_history_.push_back(spread);

        if (spread_history_.size() < static_cast<size_t>(window_)) return;

        double sum = 0.0, sum_sq = 0.0;
        for (int i = 0; i < window_; ++i) {
            double val = spread_history_[spread_history_.size() - 1 - i];
            sum += val;
            sum_sq += val * val;
        }
        double mean = sum / window_;
        double std_dev = std::sqrt((sum_sq / window_) - (mean * mean));
        
        if (std_dev < 1e-9) return;
        double z_score = (spread - mean) / std_dev;

        double holding_x = engine.get_holdings(asset_x_);
        double holding_y = engine.get_holdings(asset_y_);
        double total_equity = engine.get_total_equity();
        double leverage = engine.get_leverage();

        double target_notional = total_equity * 0.4 * leverage;

        if (z_score > z_thresh_) {
            // Target: Short Y, Long X
            if (holding_y * py > -target_notional) {
                double current_val = holding_y * py;
                double diff = current_val - (-target_notional);
                double qty_to_sell = diff / py;
                if (qty_to_sell > 0) engine.send_order(asset_y_, "SELL", qty_to_sell, py, timestamp);
            }
            if (holding_x * px < target_notional) {
                double qty_needed = (target_notional - (holding_x * px)) / px;
                if (qty_needed > 0) engine.send_order(asset_x_, "BUY", qty_needed, px, timestamp);
            }
        }
        else if (z_score < -z_thresh_) {
            // Target: Long Y, Short X
            if (holding_y * py < target_notional) { 
                double qty_needed = (target_notional - (holding_y * py)) / py;
                if (qty_needed > 0) engine.send_order(asset_y_, "BUY", qty_needed, py, timestamp);
            }
            if (holding_x * px > -target_notional) {
                double current_val = holding_x * px;
                double diff = current_val - (-target_notional);
                double qty_to_sell = diff / px;
                if (qty_to_sell > 0) engine.send_order(asset_x_, "SELL", qty_to_sell, px, timestamp);
            }
        }
        else if (std::abs(z_score) < 0.5) {
            // Exit All
            if (std::abs(holding_x) > 1e-6) {
                if (holding_x > 0) engine.send_order(asset_x_, "SELL", holding_x, px, timestamp);
                else engine.send_order(asset_x_, "BUY", -holding_x, px, timestamp);
            }
            if (std::abs(holding_y) > 1e-6) {
                if (holding_y > 0) engine.send_order(asset_y_, "SELL", holding_y, py, timestamp);
                else engine.send_order(asset_y_, "BUY", -holding_y, py, timestamp);
            }
        }

        buffer_x_.erase(timestamp);
        buffer_y_.erase(timestamp);
    }
}

PCAStatArbStrategy::PCAStatArbStrategy(int window, double z_thresh)
    : window_(window), z_thresh_(z_thresh), last_timestamp_(-1.0) {}

void PCAStatArbStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    history_[symbol].push_back(close);

    if (timestamp != last_timestamp_) {
        bool enough_data = true;
        for (const auto& [sym, prices] : history_) {
            if (prices.size() < static_cast<size_t>(window_)) {
                enough_data = false;
                break;
            }
        }

        if (enough_data) {
            std::map<std::string, std::vector<double>> window_data;
            for (const auto& [sym, prices] : history_) {
                window_data[sym] = std::vector<double>(prices.end() - window_, prices.end());
            }

            PCAResult res = PCAArbitrage::CalculateSignals(window_data, 1);
            current_z_scores_ = res.z_scores;
        }
        last_timestamp_ = timestamp;
    }

    if (current_z_scores_.find(symbol) == current_z_scores_.end()) return;

    double z_score = current_z_scores_[symbol];
    double current_holdings = engine.get_holdings(symbol);

    double cash = engine.get_cash_balance();
    double target_notional = cash * 0.10 * engine.get_leverage();

    int basket_size = history_.size();
    if (basket_size <= 1) return;
    double hedge_notional_per_asset = target_notional / (basket_size - 1);

    if (z_score < -z_thresh_ && current_holdings <= 1e-6 && target_notional > 0) {
        engine.send_order(symbol, "BUY", target_notional / close, close, timestamp);

        for (const auto& [hedge_sym, prices] : history_) {
            if (hedge_sym != symbol) {
                double hedge_price = prices.back();
                engine.send_order(hedge_sym, "SELL", hedge_notional_per_asset / hedge_price, hedge_price, timestamp);
            }
        }
        fmt::print("[PCA] Market Neutral Arb Triggered: BUY {}, SHORT Basket (Z-score: {:.2f})\n", symbol, z_score);
    }
    else if (z_score > z_thresh_ && current_holdings >= -1e-6 && target_notional > 0) {
        engine.send_order(symbol, "SELL", target_notional / close, close, timestamp);

        for (const auto& [hedge_sym, prices] : history_) {
            if (hedge_sym != symbol) {
                double hedge_price = prices.back();
                engine.send_order(hedge_sym, "BUY", hedge_notional_per_asset / hedge_price, hedge_price, timestamp);
            }
        }
        fmt::print("[PCA] Market Neutral Arb Triggered: SHORT {}, BUY Basket (Z-score: {:.2f})\n", symbol, z_score);
    }
    else if (std::abs(z_score) < 0.5 && std::abs(current_holdings) > 1e-6) {
        fmt::print("[PCA] Z-Score Reverted ({:.2f}). Liquidating {} Arb Basket.\n", z_score, symbol);

        if (current_holdings > 0) engine.send_order(symbol, "SELL", current_holdings, close, timestamp);
        else engine.send_order(symbol, "BUY", -current_holdings, close, timestamp);

        for (const auto& [hedge_sym, prices] : history_) {
            if (hedge_sym != symbol) {
                double h_qty = engine.get_holdings(hedge_sym);
                double h_price = prices.back();
                if (h_qty > 0) engine.send_order(hedge_sym, "SELL", h_qty, h_price, timestamp);
                else if (h_qty < 0) engine.send_order(hedge_sym, "BUY", -h_qty, h_price, timestamp);
            }
        }
    }
}

GammaScalpingStrategy::GammaScalpingStrategy(double option_qty, double strike, double implied_vol, double hedge_band)
    : option_qty_(option_qty), strike_(strike), implied_vol_(implied_vol),
      hedge_band_(hedge_band), risk_free_rate_(0.05) {}

void GammaScalpingStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    double current_option_price = BlackScholes::CallPrice(close, strike_, risk_free_rate_, 0.0, implied_vol_, time_to_expiry_);

    BSGreeks greeks = BlackScholes::CalculateGreeks(
        close, strike_, risk_free_rate_, 0.0, implied_vol_, time_to_expiry_, true
    );

    if (!is_initialized_) {
        initial_option_price_ = current_option_price;
        is_initialized_ = true;
    }

    double option_pnl = (current_option_price - initial_option_price_) * option_qty_;
    engine.update_custom_pnl(option_pnl);

    double option_delta_total = option_qty_ * greeks.delta;
    double current_stock_qty = engine.get_holdings(symbol);

    double net_delta = option_delta_total + current_stock_qty;

    if (std::abs(net_delta) > hedge_band_) {
        double qty_to_trade = -net_delta;

        if (qty_to_trade > 0) {
            engine.send_order(symbol, "BUY", qty_to_trade, close, timestamp);
        } else if (qty_to_trade < 0) {
            engine.send_order(symbol, "SELL", std::abs(qty_to_trade), close, timestamp);
        }
    }
}

MarketMakerStrategy::MarketMakerStrategy(double risk_aversion, double volatility, double kappa)
    : gamma_(risk_aversion), sigma_(volatility), kappa_(kappa), time_horizon_(1.0) {}

void MarketMakerStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void MarketMakerStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    double mid_price = book.get_mid_price();
    if (mid_price <= 0.0) return;

    double current_inventory = engine.get_holdings("SPY");

    double reservation_price = mid_price - (current_inventory * gamma_ * sigma_ * sigma_ * time_horizon_);

    double spread = (gamma_ * sigma_ * sigma_ * time_horizon_) + ((2.0 / gamma_) * std::log(1.0 + (gamma_ / kappa_)));

    double optimal_bid = reservation_price - (spread / 2.0);
    double optimal_ask = reservation_price + (spread / 2.0);

    fmt::print("[L2 MM Tick {:.1f}] Mid: {:.2f} | Inv: {:>4.0f} | Opt Bid: {:.2f} | Opt Ask: {:.2f} | Spread: {:.2f}\n",
               timestamp, mid_price, current_inventory, optimal_bid, optimal_ask, spread);
}

VWAPExecutionStrategy::VWAPExecutionStrategy(double target_qty, double slice_qty, double total_time)
    : target_qty_(target_qty), slice_qty_(slice_qty), total_time_(total_time), executed_qty_(0.0) {}

void VWAPExecutionStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void VWAPExecutionStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (executed_qty_ >= target_qty_) return;

    double current_vwap = book.calculate_vwap();
    double mid_price = book.get_mid_price();

    if (current_vwap <= 0.0 || mid_price <= 0.0) return;

    double time_progress = std::min(timestamp / total_time_, 1.0);
    double allowed_qty = target_qty_ * time_progress;

    if (executed_qty_ < allowed_qty) {
        if (mid_price <= current_vwap) {
            double max_buy = allowed_qty - executed_qty_;
            double qty_to_buy = std::min(slice_qty_, max_buy);

            if (qty_to_buy > 0) {
                engine.send_order("SPY", "BUY", qty_to_buy, mid_price, timestamp);
                executed_qty_ += qty_to_buy;

                fmt::print("[VWAP Sniper] Executed {:.0f} shares @ {:.2f} (VWAP: {:.2f}) | Pacing: {:.1f}% / Allowed: {:.1f}%\n",
                           qty_to_buy, mid_price, current_vwap, (executed_qty_ / target_qty_) * 100.0, time_progress * 100.0);
            } 
        }
    }
}

TWAPExecutionStrategy::TWAPExecutionStrategy(double target_qty, double total_time)
    : target_qty_(target_qty), total_time_(total_time), executed_qty_(0.0) {}

void TWAPExecutionStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void TWAPExecutionStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (executed_qty_ >= target_qty_) return;

    double mid_price = book.get_mid_price();
    if (mid_price <= 0.0) return;

    double time_progress = std::min(timestamp / total_time_, 1.0);
    double allowed_qty = target_qty_ * time_progress;

    if (executed_qty_ < allowed_qty) {
        double qty_to_buy = allowed_qty - executed_qty_;
        engine.send_order("SPY", "BUY", qty_to_buy, mid_price, timestamp);
        executed_qty_ += qty_to_buy;
        fmt::print("[TWAP] Executed {:.0f} shares @ {:.2f} | Progress: {:.1f}%\n", qty_to_buy, mid_price, (executed_qty_ / target_qty_) * 100.0);
    }
}

POVExecutionStrategy::POVExecutionStrategy(double target_qty, double participation_rate)
    : target_qty_(target_qty), participation_rate_(participation_rate), executed_qty_(0.0), last_market_volume_(0.0) {}

void POVExecutionStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void) close;
}

void POVExecutionStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (executed_qty_ >= target_qty_) return;

    double mid_price = book.get_mid_price();
    if (mid_price <= 0.0) return;

    double current_market_volume = last_market_volume_ + 1000.0;
    double volume_delta = current_market_volume - last_market_volume_;
    last_market_volume_ = current_market_volume;

    double qty_to_buy = std::min<double>(volume_delta * participation_rate_, target_qty_ - executed_qty_);

    if (qty_to_buy > 0) {
        engine.send_order("SPY", "BUY", qty_to_buy, mid_price, timestamp);
        executed_qty_ += qty_to_buy;
        fmt::print("[POV] Executed {:.0f} shares @ {:.2f} (Participating {:.1f}%) | Progress: {:.1f}%\n",
                    qty_to_buy, mid_price, participation_rate_ * 100.0, (executed_qty_ / target_qty_) * 100.0);
    }
}

IcebergExecutionStrategy::IcebergExecutionStrategy(double target_qty, double display_size)
    : target_qty_(target_qty), display_size_(display_size), executed_qty_(0.0), current_visible_qty_(0.0) {}

void IcebergExecutionStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void IcebergExecutionStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (executed_qty_ >= target_qty_) return;

    double mid_price = book.get_mid_price();
    if (mid_price <= 0.0) return;

    if (current_visible_qty_ <= 1e-6) {
        double remaining = target_qty_ - executed_qty_;
        current_visible_qty_ = std::min(display_size_, remaining);

        engine.send_order("SPY", "BUY", current_visible_qty_, mid_price, timestamp);
        executed_qty_ += current_visible_qty_;

        fmt::print("[ICEBERG] Reloaded tip: {:.0f} shares @ {:.2f} | Hidden remaining: {:.0f}\n",
                    current_visible_qty_, mid_price, target_qty_ - executed_qty_);

        current_visible_qty_ = 0.0;
    }
}

SniperExecutionStrategy::SniperExecutionStrategy(double target_qty, double target_price)
    : target_qty_(target_qty), target_price_(target_price), executed_qty_(0.0) {}

void SniperExecutionStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void SniperExecutionStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (executed_qty_ >= target_qty_) return;

    double best_ask = book.get_best_ask();

    if (best_ask > 0.0 && best_ask <= target_price_) {
        double qty_to_buy = target_qty_ - executed_qty_;
        engine.send_order("SPY", "BUY", qty_to_buy, best_ask, timestamp);
        executed_qty_ += qty_to_buy;
        fmt::print("[SNIPER] Liquidity trapped! Crossed spread for {:.0f} shares @ {:.2f}\n", qty_to_buy, best_ask);
    }
}

VRPHarvestingStrategy::VRPHarvestingStrategy(double strike, double time_to_expiry, double iv_threshold)
    : strike_(strike), time_to_expiry_(time_to_expiry), iv_threshold_(iv_threshold) {}

void VRPHarvestingStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low;

    const auto& closes = engine.get_closes(symbol);
    if (closes.size() < 20) return;

    std::vector<double> recent_prices(closes.end() - 20, closes.end());
    std::vector<double> returns = Analytics::CalculateLogReturns(recent_prices);
    double realized_vol = Analytics::CalculateVolatility(returns) * std::sqrt(252);
    double implied_vol = realized_vol + 0.06;

    if (!position_opened_ && (implied_vol - realized_vol) > iv_threshold_) {
        strike_ = close;
        
        double otm_call_strike = strike_ * 1.05;
        double otm_put_strike = strike_ * 0.95;

        double atm_call_price = BlackScholes::CallPrice(close, strike_, risk_free_rate_, 0.0, implied_vol, time_to_expiry_);
        double atm_put_price = atm_call_price - close + strike_ * std::exp(-risk_free_rate_ * time_to_expiry_);

        double otm_call_price = BlackScholes::CallPrice(close, otm_call_strike, risk_free_rate_, 0.0, implied_vol, time_to_expiry_);
        double otm_put_price = otm_call_price - close + otm_put_strike * std::exp(-risk_free_rate_ * time_to_expiry_);

        initial_option_premium_ = (atm_call_price + atm_put_price - otm_call_price - otm_put_price) * option_qty_;
        position_opened_ = true;

        fmt::print("[VRP] Implied Vol ({:.2f}%) > Realized Vol ({:.2f}%).\n", implied_vol * 100.0, realized_vol * 100.0);
        fmt::print("[VRP] Iron Butterfly: Short ATM ({:.2f}), Long OTM ({:.2f}, {:.2f})\n", strike_, otm_put_strike, otm_call_strike);
        fmt::print("      -> Net Premium Collected: ${:.2f}\n", initial_option_premium_);
    }

    if (position_opened_) {
        double otm_call_strike = strike_ * 1.05;
        double otm_put_strike = strike_ * 0.95;

        BSGreeks atm_call_greeks = BlackScholes::CalculateGreeks(close, strike_, risk_free_rate_, 0.0, implied_vol, time_to_expiry_, true);
        double atm_put_delta = atm_call_greeks.delta - 1.0;

        BSGreeks otm_call_greeks = BlackScholes::CalculateGreeks(close, otm_call_strike, risk_free_rate_, 0.0, implied_vol, time_to_expiry_, true);
        double otm_put_delta = otm_call_greeks.delta - 1.0;

        double position_delta = (-(atm_call_greeks.delta + atm_put_delta) + (otm_call_greeks.delta + otm_put_delta)) * option_qty_;
        double current_stock_qty = engine.get_holdings(symbol);
        double delta_hedge_qty = position_delta - current_stock_qty;

        if (std::abs(delta_hedge_qty) > 5.0) {
            if (delta_hedge_qty > 0) engine.send_order(symbol, "BUY", delta_hedge_qty, close, timestamp);
            else engine.send_order(symbol, "SELL", std::abs(delta_hedge_qty), close, timestamp);
        }

        time_to_expiry_ = 1.0 / 252.0;

        if (time_to_expiry_ <= 1.0 / 252.0) {
            double short_leg_loss = std::max(close - strike_, 0.0) + std::max(strike_ - close, 0.0);
            double long_leg_gain = std::max(close - otm_call_strike, 0.0) +std::max(otm_put_strike - close, 0.0);

            double settlement_cost = (short_leg_loss - long_leg_gain) * option_qty_;
            double net_profit = initial_option_premium_ - settlement_cost;

            fmt::print("[VRP] Expiry reached (Spot: {:.2f}). Net Settlement Cost: ${:.2f}\n", close, settlement_cost);
            fmt::print(fg(fmt::color::cyan), "[VRP] Net Option Premium Profit: ${:.2f}\n", net_profit);

            current_stock_qty = engine.get_holdings(symbol);
            if (std::abs(current_stock_qty) > 1e-6) {
                if (current_stock_qty > 0) engine.send_order(symbol, "SELL", current_stock_qty, close, timestamp);
                else engine.send_order(symbol, "BUY", std::abs(current_stock_qty), close, timestamp);
            }

            engine.update_custom_pnl(net_profit);
            position_opened_ = false;
            time_to_expiry_ = 30.0 / 252.0;
        }
    }
}

AvellanedaStoikovStrategy::AvellanedaStoikovStrategy(double gamma, double sigma, double kappa, double T)
    : gamma_(gamma), sigma_(sigma), kappa_(kappa), T_(T) {}

void AvellanedaStoikovStrategy::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void AvellanedaStoikovStrategy::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    double s = book.get_mid_price();
    if (s <= 0.0) return;

    double t = std::min<double>(timestamp / 500.0, T_);
    double q = engine.get_holdings("SPY");

    double reservation_price = s - q * gamma_ * sigma_ * sigma_ * (T_ - t);

    double spread = gamma_ * sigma_ * sigma_ * (T_ - t) + (2.0 / gamma_) * std::log(1.0 + gamma_ / kappa_);

    double optimal_bid = reservation_price - spread / 2.0;
    double optimal_ask = reservation_price + spread / 2.0;

    double market_best_bid = book.get_best_bid();
    double market_best_ask = book.get_best_ask();

    if (last_ask_quote_ > 0.0 && market_best_bid >= last_ask_quote_) {
        engine.send_order("SPY", "SELL", 100.0, last_ask_quote_, timestamp);
        fmt::print("[Avellaneda] Filled ASK @ {:.2f}. Spread Captured. Inventory: {:.0f}\n", last_ask_quote_, engine.get_holdings("SPY"));
    }

    if (last_bid_quote_ > 0.0 && market_best_ask <= last_bid_quote_) {
        engine.send_order("SPY", "BUY", 100.0, last_bid_quote_, timestamp);
        fmt::print("[Avellaneda] Filled BID @ {:.2f}. Spread Captured. Inventory: {:.0f}\n", last_bid_quote_, engine.get_holdings("SPY"));
    }

    last_bid_quote_ = optimal_bid;
    last_ask_quote_ = optimal_ask;

    if (static_cast<int>(timestamp) % 100 == 0) {
        fmt::print("[Avellaneda] Mid: {:.2f} | Res Price: {:.2f} | Quoting: [{:.2f} ~ {:.2f}] | Inv: {:.0f}\n", 
                   s, reservation_price, optimal_bid, optimal_ask, q);
    }
}

void EventDrivenSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)open; (void)high; (void)low; (void)engine; (void) timestamp;
    latest_prices_[symbol] = close;
}

void EventDrivenSuite::on_corporate_action(Backtester& engine, const CorporateAction& action) {
    double current_price = latest_prices_.count(action.target_symbol) ? latest_prices_[action.target_symbol] : 100.0;

    switch (action.type) {
        case ActionType::INDEX_REBALANCE:
            engine.send_order(action.target_symbol, "BUY", 1000.0, current_price, action.timestamp);
            fmt::print("[Event Driven] Index Rebalance: BUY {} (Anticipating passive fund inflows)\n", action.target_symbol);
            break;

        case ActionType::MERGER_ANNOUNCEMENT: {
            double acq_price = latest_prices_.count(action.acquiring_symbol) ? latest_prices_[action.acquiring_symbol] : 100.0;
            engine.send_order(action.target_symbol, "BUY", 1000.0, current_price, action.timestamp);
            engine.send_order(action.acquiring_symbol, "SELL", 500.0, acq_price, action.timestamp);
            fmt::print("[Event Driven] Merger Arbitrage: LONG Target ({}), SHORT Acquirer ({})\n", action.target_symbol, action.acquiring_symbol);
            break;
        }

        case ActionType::EARNINGS_SURPRISE:
            if (action.metric > 2.0) {
                engine.send_order(action.target_symbol, "BUY", 1000.0, current_price, action.timestamp);
                fmt::print("[Event Driven] PEAD (Earnings Surprise): BUY {} (SUE: {:.2f})\n",action.target_symbol, action.metric);
            }
            break;

        case ActionType::SHARE_BUYBACK:
            engine.send_order(action.target_symbol, "BUY", 1000.0, current_price, action.timestamp);
            fmt::print("[Event Driven] Share Buyback: BUY {} (Exploiting downside rigidity)\n", action.target_symbol);
            break;
    }
}

void Backtester::send_corporate_action(const CorporateAction& action) {
    if (strategy_) {
        strategy_->on_corporate_action(*this, action);
    }
}

void AdvancedMicrostructureSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)timestamp; (void)open; (void)high; (void)low; (void)close;
}

void AdvancedMicrostructureSuite::on_microstructure_msg(Backtester& engine, const MicrostructureMessage& msg) {
    if (msg.timestamp_mu - window_start_ > 1000.0) {
        if (msg_count_ > 50) {
            fmt::print("[Microstructure] Quote Stuffing Detected! ({} msgs/ms). Enabling Toxicity Shield.\n", msg_count_);
            toxicity_alert_ = true;
        } else {
            toxicity_alert_ = false;
        }
        msg_count_ = 0;
        window_start_ = msg.timestamp_mu;
    }
    msg_count_++;

    if (toxicity_alert_ || msg.is_cancel) return;

    if (msg.exchange == "EXCHANGE_A") last_price_A_ = msg.ask;
    if (msg.exchange == "EXCHANGE_B") last_price_B_ = msg.bid;

    if (last_price_A_ > 0 && last_price_B_ > 0 && (last_price_B_ - last_price_A_ > 0.05)) {
        fmt::print("[Microstructure] Latency Arb Triggered! BUY on A @ {:.2f}, SELL on B @ {:.2f}\n", last_price_A_, last_price_B_);
        engine.update_custom_pnl(last_price_B_ - last_price_A_);
        last_price_A_ = 0.0;
        last_price_B_ = 0.0;
    }
}

void Backtester::send_microstructure_msg(const MicrostructureMessage& msg) {
    if (strategy_) strategy_->on_microstructure_msg(*this, msg);
}

void CryptoDeFiSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_spot_prices_[symbol] = close;
}

void CryptoDeFiSuite::on_crypto_event(Backtester& engine, const CryptoEvent& event) {
    double current_price = latest_spot_prices_.count(event.asset) ? latest_spot_prices_[event.asset] : 1000.0;

    switch (event.type) {
        case CryptoEventType::FUNDING_RATE:
            if (event.value > 0.001) {
                fmt::print("[Crypto/DeFi] Funding Rate +{:.2f}%. Executing Delta-Neutral Carry Trade (Long Spot, Short Perp).\n", event.value * 100.0);
                engine.send_order(event.asset + "_SPOT", "BUY", 1.0, current_price, event.timestamp);
                engine.send_order(event.asset + "_PERP", "SELL", 1.0, current_price, event.timestamp);
                engine.update_custom_pnl(current_price * event.value);
            }
            break;

        case CryptoEventType::MEMPOOL_TRANSACTION:
            if (event.value > 500000.0) {
                fmt::print("[Crypto/DeFi] MEV Target Detected: ${:.0f} pending swap in Mempool.\n", event.value);
                double front_run_price = current_price * 1.001;
                double back_run_price = current_price * 1.020;

                fmt::print("              -> Front-running BUY @ {:.2f}\n", front_run_price);
                fmt::print("              -> Target transaction executes (Slippage applied)\n");
                fmt::print("              -> Back-running SELL @ {:.2f}\n", back_run_price);

                engine.update_custom_pnl(back_run_price - front_run_price);
            }
            break;

        case CryptoEventType::DEX_PRICE_UPDATE:
            double price_a = current_price;
            double price_b = event.value;

            if (std::abs(price_a - price_b) / price_a > 0.005) {
                double flash_loan_amount = 1000000.0;
                double profit = (std::max(price_a, price_b) - std::min(price_a, price_b)) / std::min(price_a, price_b) * flash_loan_amount;
                double flash_loan_fee = flash_loan_amount * 0.0009;

                if (profit > flash_loan_fee) {
                    fmt::print("[Crypto/DeFi] Atomic Flash Loan Executed! Borrowed $1M. Spread: {:.2f}%\n", std::abs(price_a - price_b)/price_a * 100.0);
                    fmt::print(fg(fmt::color::cyan), "              -> Flash Loan Arbitrage Net Profit: ${:.2f}\n", profit - flash_loan_fee);
                    engine.update_custom_pnl(profit - flash_loan_fee);
                }
            }
            break;
    }
}

void Backtester::send_crypto_event(const CryptoEvent& event) {
    if (strategy_) strategy_->on_crypto_event(*this, event);
}

void AlternativeDataSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void AlternativeDataSuite::on_alt_data(Backtester& engine, const AltDataEvent& event) {
    double current_price = latest_prices_.count(event.ticker) ? latest_prices_[event.ticker] : 100.0;

    switch (event.type) {
        case AltDataType::NLP_SENTIMENT:
            if (event.value > 0.8) {
                engine.send_order(event.ticker, "BUY", 1000.0, current_price, event.timestamp);
                fmt::print("[Alt Data] NLP Sentiment Spike ({:.2f}). Executing Momentum BUY on {}\n", event.value, event.ticker);
            }
            break;

        case AltDataType::SATELLITE_IMAGE:
            if (event.value > 1.2) {
                engine.send_order(event.ticker, "BUY", 1500.0, current_price, event.timestamp);
                fmt::print("[Alt Data] Satellite Imagery: High traffic ratio ({:.2f}x) detected. Pre-earnings BUY on {}\n", event.value, event.ticker);
            }
            break;

        case AltDataType::CONGRESSIONAL_TRADE:
            if (event.value > 1000000.0) {
                engine.send_order(event.ticker, "BUY", 2000.0, current_price, event.timestamp);
                fmt::print("[Alt Data] Congressional Whale Trade Detected (${:.0f}). Copy-trading {}\n", event.value, event.ticker);
            }
            break;
    }
}

void Backtester::send_alt_data(const AltDataEvent& event) {
    if (strategy_) strategy_->on_alt_data(*this, event);
}

void AdvancedDownsideSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void AdvancedDownsideSuite::on_anomaly_event(Backtester& engine, const AnomalyEvent& event) {
    double current_price = latest_prices_.count(event.target) ? latest_prices_[event.target] : 100.0;

    switch (event.type) {
        case AnomalyType::SHORT_SQUEEZE:
            if (event.param1 > 30.0 && event.param2 > 50.0) {
                engine.send_order(event.target, "BUY", 2000.0, current_price, event.timestamp);
                fmt::print("[Anomaly] Short Squeeze Imminent! SI: {:.1f}%, Fee: {:.1f}. BUYING {}\n", event.param1, event.param2, event.target);
            }
            break;

        case AnomalyType::TAIL_RISK:
            fmt::print("[Anomaly] Tail Risk Hedging: Purchasing OTM Puts on {} to protect portfolio.\n", event.target);
            engine.update_custom_pnl(-500.0);
            break;

        case AnomalyType::BASIS_TRADE:
            if (event.param2 - event.param1 > 2.0) {
                engine.send_order(event.target, "BUY", 1000.0, event.param1, event.timestamp);
                engine.send_order(event.hedge_asset, "SELL", 1000.0, event.param2, event.timestamp);
                fmt::print("[Anomaly] Basis Trade: LONG Spot @ {:.2f}, SHORT Futures @ {:.2f}\n", event.param1, event.param2);
            }
            break;

        case AnomalyType::CROSS_BORDER:
            double spread_pct = (event.param1 - event.param2) / event.param2 * 100.0;
            if (std::abs(spread_pct) > 3.0) {
                fmt::print("[Anomaly] Cross-Border Arb Detected! Spread: {:.2f}%. Executing FX-Hedged Arb.\n", spread_pct);
                if (spread_pct > 0) {
                    engine.send_order(event.target, "SELL", 500.0, event.param1, event.timestamp);
                    engine.send_order(event.hedge_asset, "BUY", 500.0, event.param2, event.timestamp);
                } else {
                    engine.send_order(event.target, "BUY", 500.0, event.param1, event.timestamp);
                    engine.send_order(event.hedge_asset, "SELL", 500.0, event.param2, event.timestamp);
                }
            }
            break;
    }
}

void Backtester::send_anomaly_event(const AnomalyEvent& event) {
    if (strategy_) strategy_->on_anomaly_event(*this, event);
}

void GlobalMacroSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void GlobalMacroSuite::on_macro_event(Backtester& engine, const MacroEvent& event) {
    double price_a = latest_prices_.count(event.asset_a) ? latest_prices_[event.asset_a] : 100.0;
    double price_b = latest_prices_.count(event.asset_b) ? latest_prices_[event.asset_b] : 100.0;

    switch (event.type) {
        case MacroEventType::YIELD_CURVE:
            if (event.rate_b - event.rate_a < 0.1) {
                fmt::print("[Global Macro] Yield Curve Flattened ({:.2f}% vs {:.2f}%). Initiating Steepener Trade.\n", event.rate_a, event.rate_b);
                engine.send_order(event.asset_a, "BUY", 1000.0, price_a, event.timestamp);
                engine.send_order(event.asset_b, "SELL", 1000.0, price_b, event.timestamp);
            }
            break;

        case MacroEventType::CALENDER_SPREAD:
            if (event.rate_a < event.rate_b * 0.95) {
                fmt::print("[Global Macro] Extreme Contango Detected. Selling Far-Month ({}), Buying Near-Month ({}).\n", event.asset_b, event.asset_a);
                engine.send_order(event.asset_a, "BUY", 500.0, event.rate_a, event.timestamp);
                engine.send_order(event.asset_b, "SELL", 500.0, event.rate_b, event.timestamp);
            }
            break;

        case MacroEventType::FI_CARRY_TRADE:
            if (event.rate_b - event.rate_a > 3.0) {
                fmt::print("[Global Macro] FI Carry Trade: Borrowing {} at {:.2f}%, Yielding {} at {:.2f}%.\n", event.asset_a, event.rate_a, event.asset_b, event.rate_b);
                engine.update_custom_pnl(100000.0 * (event.rate_b - event.rate_a) / 100.0);
            }
            break;

        case MacroEventType::COMMODITY_FX:
            if (event.rate_a > 5.0) {
                fmt::print("[Global Macro] Commodity Spike (+{:.1f}% on {}). Front-running FX correlation on {}.\n", event.rate_a, event.asset_a, event.asset_b);
                engine.send_order(event.asset_b, "BUY", 10000.0, price_b, event.timestamp);
            }
            break;
    }
}

void Backtester::send_macro_event(const MacroEvent& event) {
    if (strategy_) strategy_->on_macro_event(*this, event);
}

void AIBehavioralSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void AIBehavioralSuite::on_ai_bhv_event(Backtester& engine, const AIBhvEvent& event) {
    double current_price = latest_prices_.count(event.target_asset) ? latest_prices_[event.target_asset] : 100.0;

    switch (event.type) {
        case AIBhvType::DEEP_ALPHA:
            if (event.metric_value > 0.8) {
                fmt::print("[AI/Bhv] Deep Alpha Activated (Latent Score: {:.2f}). Executing Model-Driven BUY on {}\n", event.metric_value, event.target_asset);
                engine.send_order(event.target_asset, "BUY", 800.0, current_price, event.timestamp);
            }
            break;

        case AIBhvType::GNN_PROPAGATION:
            fmt::print("[AI/Bhv] GNN Shock Propagation: Momentum from {} expanding to {}. Front-running related node.\n", event.related_asset, event.target_asset);
            engine.send_order(event.target_asset, "BUY", 800.0, current_price, event.timestamp);
            break;

        case AIBhvType::CROWDEDNESS:
            if (event.metric_value > 85.0) {
                fmt::print("[AI/Bhv] Severe Crowdedness Detected ({:.1f}%). Liquidating {} to avoid cascading wipeout.\n", event.metric_value, event.target_asset);
                double inventory = engine.get_holdings(event.target_asset);
                if (inventory > 0) {
                    engine.send_order(event.target_asset, "SELL", inventory, current_price, event.timestamp);
                }
            }
            break;

        case AIBhvType::FOMO_PANIC:
            if (event.metric_value < 10.0) {
                fmt::print("[AI/Bhv] Extreme Market Panic (Index: {:.1f}). Executing Contrarian BUY on {}\n", event.metric_value, event.target_asset);
                engine.send_order(event.target_asset, "BUY", 1500.0, current_price, event.timestamp);
            } else if (event.metric_value > 90.0) {
                fmt::print("[AI/Bhv] Extreme Market FOMO (Index: {:.1f}). Executing Contranian SELL on {}\n", event.metric_value, event.target_asset);
                double inventory = engine.get_holdings(event.target_asset);
                if (inventory > 0) {
                    engine.send_order(event.target_asset, "SELL", inventory, current_price, event.timestamp);
                } else {
                    engine.send_order(event.target_asset, "SELL", 1000.0, current_price, event.timestamp);
                }
            }
            break;
    }
}

void Backtester::send_ai_bhv_event(const AIBhvEvent& event) {
    if (strategy_) strategy_->on_ai_bhv_event(*this, event);
}

void GrandFinaleSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void GrandFinaleSuite::on_final_event(Backtester& engine, const FinalEvent& event) {
    double current_price = latest_prices_.count(event.asset) ? latest_prices_[event.asset] : 100.0;

    switch (event.type) {
        case FinalTacticsType::QUANTUM_OPT:
            fmt::print("[Grand Finale] Quantum-Inspired Annealing Completed. Escaped local minima.\n");
            fmt::print("               -> Reallocating entire portfolio to Global Optimum State.\n");
            engine.send_order(event.asset, "BUY", 5000.0, current_price, event.timestamp);
            break;

        case FinalTacticsType::DIVIDEND_CAPTURE:
            if (event.param1 > 0.04) {
                fmt::print("[Grand Finale] Ex-Dividend Arbitrage: Harvesting {:.1f}% yield on {}.\n", event.param1 * 100.0, event.asset);
                engine.send_order(event.asset, "BUY", 1000.0, current_price, event.timestamp);
                engine.update_custom_pnl(current_price * 1000.0 * event.param1);
            }
            break;

        case FinalTacticsType::LITIGATION_ARB:
            if (event.param1 > 0.75) {
                fmt::print("[Grand Finale] Asymmetric Info: {:.0f}% probability of lawsuit victory for {}. Executing aggressive LONG.\n", event.param1 * 100.0, event.asset);
                engine.send_order(event.asset, "BUY", 2000.0, current_price, event.timestamp);
            }
            break;

        case FinalTacticsType::CHAOS_REGIME:
            if (event.param1 > 0.5) {
                fmt::print("[Grand Finale] Chaos Theory: Hurst Exponent {:.2f}. Market is in ORDER (Trending).\n", event.param1);
                engine.send_order(event.asset, "BUY", 1000.0, current_price, event.timestamp);
            } else {
                fmt::print("[Grand Finale] Chaos Theory: Hurst Exponent {:.2f}. Market is in CHAOS (Mean-Reverting).\n", event.param1);
                double inventory = engine.get_holdings(event.asset);
                if (inventory > 0) {
                    engine.send_order(event.asset, "SELL", inventory, current_price, event.timestamp);
                }
            }
            break;
    }
}

void Backtester::send_final_event(const FinalEvent& event) {
    if (strategy_) strategy_->on_final_event(*this, event);
}

void L3ExecutionSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)symbol; (void)open; (void)high; (void)low;

    if (arrival_price_ > 0 && close < arrival_price_ * 0.85) {
        fmt::print("[L3 Desk] Strategy #53 (Flash Carsh Arb): Extreme price deviation detected (-15%). Executing Bottom Fishing BUY.\n");
        engine.send_order(symbol, "BUY", 5000.0, close, timestamp);
    }
}

void L3ExecutionSuite::on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) {
    if (toxicity_shield_active_) return;

    double bid_vol = book.get_best_bid();
    double ask_vol = book.get_best_ask();
    double mid_price = book.get_mid_price();

    if (arrival_price_ == 0.0) arrival_price_ = mid_price;

    double imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-6);
    if (imbalance > 0.8) {
        fmt::print("[L3 Desk] Strategy #1(OBI): Severe Bid Imbalance ({:.2f}). Predicting short-term upward tick.\n", imbalance);
        engine.send_order("SPY", "BUY", 100.0, mid_price, timestamp);
        last_trade_price_ = mid_price;
    }

    if (static_cast<int>(timestamp) % 10 == 0) {
        engine.update_custom_pnl(5.0);
    }
}

void L3ExecutionSuite::on_l3_message(Backtester& engine, const L3OrderMessage& msg) {
    if (last_trade_price_ > 0 && msg.price < last_trade_price_ * 0.999) {
        fmt::print("[L3 Desk] Strategy #71 (Anti-Selection): Price moved against us immediately after fill. Toxic flow detected!\n");
        fmt::print("          -> Activating Toxicity Shield. Halting Execution.\n");
        toxicity_shield_active_ = true;
        last_trade_price_ = 0.0;
        return;
    }

    if (msg.trader_type == "INST") {
        fmt::print("[L3 Desk] Strategy #62 & #52 (Flow Seg / Anticipation): Institutional VWAP slice detected ({} shares). Front-running.\n", msg.volume);
        engine.send_order(msg.symbol, msg.is_buy ? "SELL" : "BUY", 1000.0, msg.price, msg.timestamp);
    }

    if (msg.exchange == "LIT_FAST") fill_rates_["LIT_FAST"] = 0.98;
    if (msg.exchange == "LIT_SLOW") fill_rates_["LIT_SLOW"] = 0.45;
}

void Backtester::send_l3_message(const L3OrderMessage& msg) {
    if (risk_shutdown_) return;
    if (strategy_) strategy_->on_l3_message(*this, msg);
}

void StructuralArbSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void StructuralArbSuite::on_structural_event(Backtester& engine, const StructuralEvent& event) {
    switch (event.type) {
        case StructArbType::VIX_BASIS:
            if (event.price_b > event.price_a * 1.05) {
                fmt::print("[Struct Arb] Strategy #6 (VIX Basis): Extreme Contango. SHORT VIX Futures @ {:.2f}, LONG VIX Spot @ {:.2f}\n", event.price_b, event.price_a);
                engine.send_order(event.asset_b, "SELL", 500.0, event.price_b, event.timestamp);
                engine.send_order(event.asset_a, "BUY", 500.0, event.price_a, event.timestamp);
            }
            break;

        case StructArbType::DISPERSION:
            if (event.price_a < event.price_b * 0.80) {
                fmt::print("[Struct Arb] Strategy #7 (Dispersion): Index Vol ({:.2f}) < Components Vol ({:.2f}). SHORT Index Opt, LONG Basket Opt.\n", event.price_a, event.price_b);
                engine.update_custom_pnl(1500.0);
            }
            break;

        case StructArbType::TAX_LOSS:
            if (event.param == 12.0 && event.price_a < event.price_b * 0.6) {
                fmt::print("[Struct Arb] Strategy #45 (Tax-Loss): Institutional year-end dumping detected on {}. Executing Buy-and-Hold for January Rebound.\n", event.asset_a);
                engine.send_order(event.asset_a, "BUY", 2000.0, event.price_a, event.timestamp);
            }
            break;

        case StructArbType::SHARE_CLASS:
            if (std::abs(event.price_a - event.price_b) > event.param) {
                fmt::print("[Struct Arb] Strategy #46 (Share Class): Spread > {:.2f}. Arb executed between {} and {}.\n", event.param, event.asset_a, event.asset_b);
                engine.send_order(event.asset_a, "SELL", 1000.0, event.price_a, event.timestamp);
                engine.send_order(event.asset_b, "BUY", 1000.0, event.price_b, event.timestamp);
            }
            break;

        case StructArbType::DUAL_LISTED:
            {
                double fx_adjusted_local = event.price_b * event.param;
                double spread = (event.price_a - fx_adjusted_local) / fx_adjusted_local;
                if (std::abs(spread) > 0.02) {
                    fmt::print("[Struct Arb] Strategy #47 & #56: DLC & Cross-Listing (ADR vs Local + FX Hedge): ADR-Local Mismatch ({:.2f}%). Bridging liquidity.\n", spread * 100.0);
                    engine.update_custom_pnl(100000.0 * std::abs(spread));
                }
            }
            break;

        case StructArbType::ETF_ARB:
            if (event.price_a > event.price_b * 1.01) {
                fmt::print("[Struct Arb] Strategy #49 (ETF Arb): NAV ({:.2f}) > Price ({:.2f}). Acting as AP: BUY ETF, SELL Basket.\n", event.price_a, event.price_b);
                engine.send_order(event.asset_b, "BUY", 5000.0, event.price_b, event.timestamp);
            }
            break;

        case StructArbType::PREDICT_MARKET:
            if (std::abs(event.price_a - event.price_b) > 0.1) {
                fmt::print("[Struct Arb] Strategy #50 (Prediction Arb): Odds mismatch between PolyMarket ({:.2f}) and CME ({:.2f}). Hedging.\n", event.price_a, event.price_b);
                engine.update_custom_pnl(500.0);
            }
            break;

        case StructArbType::ODD_LOT:
            if (event.param < 100 && event.price_a < event.price_b * 0.995) {
                fmt::print("[Struct Arb] Strategy #64 (Odd-Lot): Sweeping discounted odd-lots ({} shares) and reselling as round-lots.\n", event.param);
                engine.send_order(event.asset_a, "BUY", event.param, event.price_a, event.timestamp);
            }
            break;

        case StructArbType::DELTA_GAMMA:
            fmt::print("[Struct Arb] Strategy #72 (Delta-Gamma): Rebalancing portfolio 2nd-order derivatives. Gamma neutral achieved.\n");
            engine.send_order(event.asset_a, "BUY", event.param, event.price_a, event.timestamp);
            break;
    }
}

void Backtester::send_structural_event(const StructuralEvent& event) {
    if (risk_shutdown_) return;

    if (strategy_) {
        if (auto* arb_suite = dynamic_cast<StructuralArbSuite*>(strategy_.get())) {
            arb_suite->on_structural_event(*this, event);
        } else {
            strategy_->on_structural_event(*this, event);
        }
    }
}

void DeepCryptoCycleSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void DeepCryptoCycleSuite::on_deep_cycle_event(Backtester& engine, const DeepCycleEvent& event) {
    double current_price = latest_prices_.count(event.asset_main)? latest_prices_[event.asset_main] : 100.0;

    switch (event.type) {
        case DeepCycleType::CROSS_ASSET_MOMO:
            if (event.metric > event.threshold) {
                fmt::print("[Deep Cycle] Strategy #12 (Cross-Asset Momo): {} spiked {:.1f}%. Front-running lagging asset {}.\n", event.asset_sub, event.metric * 100.0, event.asset_main);
                engine.send_order(event.asset_main, "BUY", 1000.0, current_price, event.timestamp);
            }
            break;

        case DeepCycleType::LOW_VOL_ANOMALY:
            if (event.metric < event.threshold) {
                fmt::print("[Deep Cycle] Strategy #13 (Low-Vol Anomaly): {} exhibits extreme low volatility. Accumulating defensive position.\n", event.asset_main);
                engine.send_order(event.asset_main, "BUY", 1500.0, current_price, event.timestamp);
            }
            break;

        case DeepCycleType::OVERREACTION:
            if (event.metric < -0.10) {
                fmt::print("[Deep Cycle] Strategy #58 (Overreaction): {} flash crashed by {:.1f}%. Executing Mean-Reversion BUY.\n", event.asset_main, std::abs(event.metric) * 100.0);
                engine.send_order(event.asset_main, "BUY", 2000.0, current_price, event.timestamp);
            }
            break;

        case DeepCycleType::WINDOW_DRESSING:
            if (event.metric == 1.0) {
                fmt::print("[Deep Cycle] Strategy #59 (Window Dressing): Quarter-end detected. Front-running institutional buying on top performer {}.\n", event.asset_main);
                engine.send_order(event.asset_main, "BUY", 1000.0, current_price, event.timestamp);
            }
            break;

        case DeepCycleType::INVENTORY_CYCLE:
            if (event.metric == 1.0) {
                fmt::print("[Deep Cycle] Strategy #65 (Inventory Cycle): Supply chain data signals 'Restocking' phase. BUYING cyclical asset {}.\n", event.asset_main);
                engine.send_order(event.asset_main, "BUY", 50.0, current_price * 0.90, event.timestamp);
            }
            break;

        case DeepCycleType::LIQUIDATION_HUNT:
            if (event.metric > 50000000.0) {
                fmt::print("[Deep Cycle] Strategy #67 (Liquidation Hunt): ${:.0f}M liquidation wall detected on {}. Placing Bottom-Fishing Limit Orders.\n", event.metric / 1000000.0, event.asset_main);
                engine.send_order(event.asset_main, "BUY", 50.0, current_price * 0.90, event.timestamp);
            }
            break;

        case DeepCycleType::CROSS_CHAIN_BRIDGE:
            if (std::abs(event.metric) > 0.02) {
                fmt::print("[Deep Cycle] Strategy #68 (Bridge Arb): {} depegged by {:.1f}% between networks. Executing Cross-Chain Arb.\n", event.asset_main, event.metric * 100.0);
                engine.update_custom_pnl(5000.0);
            }
    }
}

void Backtester::send_deep_cycle_event(const DeepCycleEvent& event) {
    if (risk_shutdown_) return;

    if (strategy_) {
        if (auto* suite = dynamic_cast<DeepCryptoCycleSuite*>(strategy_.get())) {
            suite->on_deep_cycle_event(*this, event);
        } else {
            strategy_->on_deep_cycle_event(*this, event);
        }
    }
}

void MetaBrainSuite::on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) {
    (void)engine; (void)timestamp; (void)open; (void)high; (void)low;
    latest_prices_[symbol] = close;
}

void MetaBrainSuite::on_meta_event(Backtester& engine, const MetaEvent& event) {
    double current_price = latest_prices_.count(event.target) ? latest_prices_[event.target] : 100.0;

    switch (event.type) {
        case MetaBrainType::RISK_PARITY:
            fmt::print("[Meta-Brain] Strategy #10 (Risk Parity): Rebalancing... Equities Vol {:.1f}%, Bonds Vol {:.1f}%.\n", event.value1 * 100, event.value2 * 100);
            fmt::print("             -> Allocating higher capital weight to low-volatility assets to achieve equal risk contribution.\n");
            engine.send_order("SPY", "BUY", 100.0, current_price, event.timestamp);
            engine.send_order("TLT", "BUY", 400.0, 100.0, event.timestamp);
            break;

        case MetaBrainType::HMM_REGIME:
            if (event.value1 == 1.0) {
                fmt::print("[Meta-Brain] Strategy #11 (HMM): High probability of 'Uptrend Regime'. Activating Trend-Following algorithms.\n");
                engine.send_order(event.target, "BUY", 500.0, current_price, event.timestamp);
            } else {
                fmt::print("[Meta-Brain] Strategy #11 (HMM): Transitioned to 'Sideways/Range-Bottom'. Switching to Mean-Reversion algorithms.\n");
            }
            break;

        case MetaBrainType::CLUSTERING:
            fmt::print("[Meta-Brain] Strategy #44 (Clustering): K-Means identified current market as '{}'. Activating specialized sub-strategy set.\n", event.target);
            break;

        case MetaBrainType::ADAPTIVE_ARRIVAL:
            if (event.value2 > 0.5) {
                fmt::print("[Meta-Brain] Strategy #69 (Adaptive Arrival): Volatility spiked to {:.1f}. Slowing down execution to minimize impact.\n", event.value2);
            } else if (current_price <= event.value1) {
                fmt::print("[Meta-Brain] Strategy #69 (Adaptive Arrival): Price ({:.2f}) moved below Arrival Price ({:.2f}). Accelerating aggressive BUY execution.\n", current_price, event.value1);
                engine.send_order(event.target, "BUY", 1000.0, current_price, event.timestamp);
            }
            break;

        case MetaBrainType::MULTI_STRAT_MVO:
            fmt::print("[Meta-Brain] Strategy #73 (Multi-Strat MVO): Calculating Markowitz Efficient Frontier across 70+ sub-strategies.\n");
            fmt::print("             -> Allocating optimal margin weight ({:.1f}%) to '{}' strategy.\n", event.value1, event.target);
            break;

        case MetaBrainType::TAIL_RISK:
            fmt::print("[Meta-Brain] Strategy #74 (Tail-Risk Parity): Re-weighting based on Extreme Loss (ES: {:.2f}%) rather than standard deviation.\n", event.value1 * 100.0);
            fmt::print("             -> Capital shifted to defensive posture to prevent Black Swan collapse.\n");
            engine.update_custom_pnl(-200.0);
            break;
    }
}

void Backtester::send_meta_event(const MetaEvent& event) {
    if (risk_shutdown_) return;

    if (strategy_) {
        if (auto* suite = dynamic_cast<MetaBrainSuite*>(strategy_.get())) {
            suite->on_meta_event(*this, event);
        } else {
            strategy_->on_meta_event(*this, event);
        }
    }
}

Backtester::Backtester(double initial_capital, std::string strategy_type, double leverage)
    : capital_(initial_capital), leverage_(leverage) {
    
    if (strategy_type == "EMA") strategy_ = std::make_unique<EMAStrategy>();
    else if (strategy_type == "RSI") strategy_ = std::make_unique<RSIStrategy>();
    else if (strategy_type == "MACD") strategy_ = std::make_unique<MACDStrategy>();
    else if (strategy_type == "BB") strategy_ = std::make_unique<BollingerStrategy>();
    else if (strategy_type == "VOL") strategy_ = std::make_unique<VolatilityStrategy>();
    else if (strategy_type == "OU") strategy_ = std::make_unique<OUStrategy>();
    else if (strategy_type == "PAIRS") strategy_ = std::make_unique<KalmanPairsStrategy>("KO", "PEP");
    else if (strategy_type == "PCA") strategy_ = std::make_unique<PCAStatArbStrategy>(60, 2.0);
    else if (strategy_type == "GAMMA") strategy_ = std::make_unique<GammaScalpingStrategy>(1000.0, 100.0, 0.20, 5.0);
    else if (strategy_type == "MM") strategy_ = std::make_unique<MarketMakerStrategy>(0.1, 0.2, 1.5);
    else if (strategy_type == "VWAP") strategy_ = std::make_unique<VWAPExecutionStrategy>(10000.0, 500.0, 200.0);
    else if (strategy_type == "TWAP") strategy_ = std::make_unique<TWAPExecutionStrategy>(10000.0, 200.0);
    else if (strategy_type == "POV") strategy_ = std::make_unique<POVExecutionStrategy>(10000.0, 0.05);
    else if (strategy_type == "ICEBERG") strategy_ = std::make_unique<IcebergExecutionStrategy>(10000.0, 500.0);
    else if (strategy_type == "SNIPER") strategy_ = std::make_unique<SniperExecutionStrategy>(10000.0, 99.50);
    else if (strategy_type == "VRP") strategy_ = std::make_unique<VRPHarvestingStrategy>(100.0, 30.0 / 252.0, 0.05);
    else if (strategy_type == "AVELLANEDA") strategy_ = std::make_unique<AvellanedaStoikovStrategy>(0.1, 0.2, 1.5, 1.0);
    else if (strategy_type == "EVENT_DRIVEN") strategy_ = std::make_unique<EventDrivenSuite>();
    else if (strategy_type == "MICROSTRUCTURE") strategy_ = std::make_unique<AdvancedMicrostructureSuite>();
    else if (strategy_type == "CRYPTO_DEFI") strategy_ = std::make_unique<CryptoDeFiSuite>();
    else if (strategy_type == "ALT_DATA") strategy_ = std::make_unique<AlternativeDataSuite>();
    else if (strategy_type == "DOWNSIDE_SQUEEZE") strategy_ = std::make_unique<AdvancedDownsideSuite>();
    else if (strategy_type == "GLOBAL_MACRO") strategy_ = std::make_unique<GlobalMacroSuite>();
    else if (strategy_type == "AI_BHV") strategy_ = std::make_unique<AIBehavioralSuite>();
    else if (strategy_type == "GRAND_FINALE") strategy_ = std::make_unique<GrandFinaleSuite>();
    else if (strategy_type == "L3_EXECUTION") strategy_ = std::make_unique<L3ExecutionSuite>();
    else if (strategy_type == "STRUCTURAL_ARB") strategy_ = std::make_unique<StructuralArbSuite>();
    else if (strategy_type == "DEEP_CYCLE") strategy_ = std::make_unique<DeepCryptoCycleSuite>();
    else if (strategy_type == "META_BRAIN") strategy_ = std::make_unique<MetaBrainSuite>();
    else {
        fmt::print("[Warning] Unknown strategy '{}', defaulting to EMA.\n", strategy_type);
        strategy_ = std::make_unique<EMAStrategy>();
    }
}

void Backtester::set_regime_filter(bool use_filter, int lookback) {
    use_regime_filter_ = use_filter;
    regime_lookback_ = lookback;
    fmt::print("[System] Regime Filter: {}, Lookback: {}\n", use_filter ? "ON" : "OFF", lookback);
}

void Backtester::hibernate_positions(double timestamp, const std::string& symbol, double price) {
    if (holdings_.count(symbol)) {
        double qty = holdings_[symbol];
        if (std::abs(qty) > 1e-6) {
            if (qty > 0) {
                send_order(symbol, "SELL", qty, price, timestamp);
            } else {
                send_order(symbol, "BUY", -qty, price, timestamp);
            }
        }
    }
}

void Backtester::on_market_data(const std::string& symbol ,double timestamp, double open, double high, double low, double close) {
    last_price_[symbol] = close;

    opens_[symbol].push_back(open);
    highs_[symbol].push_back(high);
    lows_[symbol].push_back(low);
    closes_[symbol].push_back(close);

    bool is_bear_market = false;
    if (use_regime_filter_) {
        price_history_buffer_[symbol].push_back(close);
        const auto& history = price_history_buffer_[symbol];

        if (history.size() >= static_cast<size_t>(regime_lookback_)) {
            RegimeResult regime = RegimeDetector::DetectRegime(history, 20);
            if (regime.state_name == "Bear") {
                is_bear_market = true;
            }
        }
    }

    if (!risk_shutdown_) {
        check_risk_limits(timestamp);
    }

    if (!risk_shutdown_) {
        if (is_bear_market) {
            hibernate_positions(timestamp, symbol, close);
        } else {
            if (strategy_) {
                strategy_->on_market_data(*this, symbol, timestamp, open, high, low, close);
            }
        }
    }

    equity_history_.push_back(get_total_equity());
}

void Backtester::on_order_book_update(const OrderBook& book, double timestamp) {
    if (strategy_) {
        strategy_->on_order_book_update(*this, book, timestamp);
    }
}

void Backtester::send_order(const std::string& symbol, const std::string& side, double quantity, double price, double timestamp) {
    if (quantity <= 0) return;

    double commission = quantity * price * 0.0001;
    double prev_holding = holdings_[symbol];

    if (side == "BUY") {
        capital_ -= (quantity * price + commission);
        holdings_[symbol] += quantity;

        if (prev_holding >= 0) {
            double total_val = (prev_holding * avg_entry_price_[symbol]) + (quantity * price);
            double total_qty = prev_holding + quantity;
            if (total_qty > 0) {
                avg_entry_price_[symbol] = total_val / total_qty;
            }
            highest_price_[symbol] = price;
        }

        trades_.push_back({(int)trades_.size(), symbol, "BUY", quantity, price, commission, timestamp});
    } else if (side == "SELL") {
       capital_ += (quantity * price - commission);
       holdings_[symbol] -= quantity;

       if (prev_holding <= 0) {
            double prev_abs_qty = std::abs(prev_holding);
            double total_val = (prev_abs_qty * avg_entry_price_[symbol]) + (quantity * price);
            double total_qty = prev_abs_qty + quantity;

            if (total_qty > 0) {
                avg_entry_price_[symbol] = total_val / total_qty;
            }
        }

        trades_.push_back({(int)trades_.size(), symbol, "SELL", quantity, price, commission, timestamp});
    }
}

double Backtester::get_total_equity() const {
    double total = capital_ + custom_pnl_;

    for (const auto& [sym, qty] : holdings_) {
        if (last_price_.count(sym)) {
            total += qty * last_price_.at(sym);
        }
    }
    return total;
}

double Backtester::get_holdings(const std::string& symbol) const {
    if (holdings_.count(symbol)) return holdings_.at(symbol);
    return 0.0;
}

double Backtester::get_max_drawdown() const {
    return Analytics::CalculateMaxDrawdown(equity_history_);
}

const std::vector<double>& Backtester::get_opens(const std::string& symbol) const { return opens_.at(symbol); }
const std::vector<double>& Backtester::get_highs(const std::string& symbol) const { return highs_.at(symbol); }
const std::vector<double>& Backtester::get_lows(const std::string& symbol) const { return lows_.at(symbol); }
const std::vector<double>& Backtester::get_closes(const std::string& symbol) const { return closes_.at(symbol); }

void Backtester::set_macd_parameters(int fast, int slow, int signal) {
    if (auto* macd = dynamic_cast<MACDStrategy*>(strategy_.get())) {
        macd->set_parameters(fast, slow, signal);
    }
}

void Backtester::set_volatility_k(double k) {
    if (auto* vol = dynamic_cast<VolatilityStrategy*>(strategy_.get())) {
        vol->set_k(k);
    }
}

std::vector<double> Backtester::get_equity_history() const {
    return equity_history_;
}

void Backtester::set_risk_params(double max_drawdown_limit, double var_limit) {
    max_drawdown_limit_ = max_drawdown_limit;
    var_limit_ = var_limit;
}

void Backtester::check_risk_limits(double timestamp) {
    double current_mdd = get_max_drawdown();
    if (std::abs(current_mdd) > max_drawdown_limit_) {
        liquidator(timestamp, "Hard Stop-Loss Triggered (MDD > " + std::to_string(max_drawdown_limit_ * 100) + "%)");
        return;
    }

    double total_risk_amount = 0.0;
    double equity = get_total_equity();

    for (const auto& [sym, qty] : holdings_) {
        if (std::abs(qty) > 1e-6 && closes_.count(sym)) {
            const auto& prices = closes_.at(sym);
            if (prices.size() > 30) {
                std::vector<double> recent_prices(prices.end() - 30, prices.end());
                std::vector<double> returns = Analytics::CalculateLogReturns(recent_prices);
                double vol = Analytics::CalculateVolatility(returns);

                double position_value = std::abs(qty * last_price_.at(sym));
                double position_var = Analytics::CalculateParametricVaR(position_value, vol, 0.95);

                total_risk_amount += position_var;
            }
        }
    }

    double portfolio_var_ratio = (equity > 0) ? (total_risk_amount / equity) : 0.0;

    if (portfolio_var_ratio > var_limit_) {
        std::string msg = fmt::format("VaR Limit Breached! Current Risk: {:.2f}% > Limit: {:.2f}%", 
                                      portfolio_var_ratio * 100.0, var_limit_ * 100.0);
        liquidator(timestamp, msg);
    }
}

void Backtester::liquidator(double timestamp, const std::string& reason) {
    if (risk_shutdown_) return;

    fmt::print("\n[!!! RISK ALERT !!!] {}\n", reason);
    fmt::print("Execution: LIQUIDATING ALL POSITIONS...\n");

    for (auto& [sym, qty] : holdings_) {
        if (std::abs(qty) > 1e-6) {
            double price = last_price_[sym];
            if (qty > 0) {
                send_order(sym, "SELL", qty, price, timestamp);
            } else {
                send_order(sym, "BUY", -qty, price, timestamp);
            }
        }
    }

    risk_shutdown_ = true;
    fmt::print("System Halted. No further trades will be executed.\n");
}

void Backtester::set_pairs_parameters(int window, double threshold) {
    if (auto* pairs = dynamic_cast<KalmanPairsStrategy*>(strategy_.get())) {
        pairs->set_parameters(window, threshold);
    } else {
        fmt::print("[Error] Current strategy is not KalmanPairsStrategy. Cannot set parameters.\n");
    }
}