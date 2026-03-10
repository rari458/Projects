// include/BlackScholesFormulas.h

#pragma once
#include <cmath>

struct BSGreeks {
    double delta;
    double gamma;
    double theta;
    double vega;
    double rho;
};

class BlackScholes {
public:
    static double StandardNormalCDF(double x);
    static double StandardNormalPDF(double x);

    static double CallPrice(double spot, double strike, double r, double d, double vol, double expiry);
    static double PutPrice(double spot, double strike, double r, double d, double vol, double expiry);

    static BSGreeks CalculateGreeks(double spot, double strike, double r, double d, double vol, double expiry, bool is_call);
};