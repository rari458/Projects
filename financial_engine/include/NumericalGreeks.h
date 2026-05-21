#pragma once
#include <cmath>
#include <functional>

template<class T>
double CalculateDelta(double Spot, double h, T TheFunction) {
    double PriceUp = TheFunction(Spot + h);
    double PriceDown = TheFunction(Spot - h);

    return (PriceUp - PriceDown) / (2.0 * h);
}

template<class T>
double CalculateGamma(double Spot, double h, T TheFunction) {
    double PriceUp = TheFunction(Spot + h);
    double PriceDown = TheFunction(Spot - h);
    double PriceSpot = TheFunction(Spot);

    return (PriceUp - 2.0 * PriceSpot + PriceDown) / (h * h);
}