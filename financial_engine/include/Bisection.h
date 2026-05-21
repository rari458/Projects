// include/Bisection.h

#pragma once
#include <cmath>
#include <functional>

template<class T>
double Bisection(double Target, 
                double Low, 
                double High, 
                double Tolerance, 
                T TheFunction) {
    
    double x = 0.5 * (Low + High);
    double y = TheFunction(x);

    do {
        if (y < Target) {
            Low = x; 
        } else {
            High = x;
        }

        x = 0.5 * (Low + High);
        y = TheFunction(x);
    } while (std::abs(y - Target) > Tolerance);

    return x;
}