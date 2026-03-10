// src/BlackScholesFormulas.cpp

#include "../include/BlackScholesFormulas.h"

double BlackScholes::StandardNormalCDF(double x) {
    return 0.5 * std::erfc(-x * std::sqrt(0.5));
}

double BlackScholes::StandardNormalPDF(double x) {
    const double inv_sqrt_2pi = 0.3989422804014327;
    return inv_sqrt_2pi * std::exp(-0.5 * x * x);
}

double BlackScholes::CallPrice(double spot, double strike, double r, double d, double vol, double expiry) {
    if (expiry <= 0.0) return std::max(0.0, spot - strike);
    double d1 = (std::log(spot / strike) + (r - d + 0.5 * vol * vol) * expiry) / (vol * std::sqrt(expiry));
    double d2 = d1 - vol * std::sqrt(expiry);
    return spot * std::exp(-d * expiry) * StandardNormalCDF(d1) - strike * std::exp(-r * expiry) * StandardNormalCDF(d2);
}

double BlackScholes::PutPrice(double spot, double strike, double r, double d, double vol, double expiry) {
    if (expiry <= 0.0) return std::max(0.0, strike - spot);
    double d1 = (std::log(spot / strike) + (r - d + 0.5 * vol * vol) * expiry) / (vol * std::sqrt(expiry));
    double d2 = d1 - vol * std::sqrt(expiry);
    return strike * std::exp(-r * expiry) * StandardNormalCDF(-d2) - spot * std::exp(-d * expiry) * StandardNormalCDF(-d1);
}

BSGreeks BlackScholes::CalculateGreeks(double spot, double strike, double r, double d, double vol, double expiry, bool is_call) {
    BSGreeks greeks = {0.0, 0.0, 0.0, 0.0, 0.0};
    if (expiry <= 0.0 || vol <= 0.0 || spot <= 0.0) return greeks;

    double sqrt_t = std::sqrt(expiry);
    double d1 = (std::log(spot / strike) + (r - d + 0.5 * vol * vol) * expiry) / (vol * sqrt_t);
    double d2 = d1 - vol * sqrt_t;

    double nd1 = StandardNormalPDF(d1);
    double Nd1 = StandardNormalCDF(d1);
    double Nd2 = StandardNormalCDF(d2);
    double N_minus_d1 = StandardNormalCDF(-d1);
    double N_minus_d2 = StandardNormalCDF(-d2);

    double exp_minus_dt = std::exp(-d * expiry);
    double exp_minus_rt = std::exp(-r * expiry);

    greeks.gamma = (nd1 * exp_minus_dt) / (spot * vol * sqrt_t);
    greeks.vega = spot * sqrt_t * nd1 * exp_minus_dt;

    if (is_call) {
        greeks.delta = exp_minus_dt * Nd1;
        greeks.theta = -(spot * vol * nd1 * exp_minus_dt) / (2.0 * sqrt_t)
                       - r * strike * exp_minus_rt * Nd2
                       + d * spot * exp_minus_rt * Nd1;
        greeks.rho = strike * expiry * exp_minus_rt * Nd2;
    } else {
        greeks.delta = -exp_minus_dt * N_minus_d1;
        greeks.theta = -(spot * vol * nd1 * exp_minus_dt) / (2.0 * sqrt_t)
                       + r * strike * exp_minus_rt * N_minus_d2
                       - d * spot * exp_minus_dt * N_minus_d1;
        greeks.rho = -strike * expiry * exp_minus_rt * N_minus_d2;
    }

    return greeks;
}