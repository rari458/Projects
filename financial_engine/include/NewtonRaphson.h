// include/NewtonRaphson.h

#ifndef NEWTON_RAPHSON_H
#define NEWTON_RAPHSON_H

#include <cmath>
#include <functional>
#include <stdexcept>
#include <iostream>

class NewtonRaphson {
public:
    static double Calculate(std::function<double(double)> func,
                            std::function<double(double)> derivative,
                            double guess,
                            double tolerance = 1e-6,
                            int max_iterations = 100) {

        double x = guess;

        for (int i = 0; i < max_iterations; ++i) {
            double y = func(x);
            double dy = derivative(x);

            if (std::abs(dy) < 1e-10) {
                throw std::runtime_error("Newton-Raphson Error: Derivative is too close to zero (Vanishing Gradient).");
            }

            double next_x = x - (y / dy);

            if (std::abs(next_x - x) < tolerance) {
                return next_x;
            }

            x = next_x;
        }

        throw std::runtime_error("Newton-Raphson Error: Maximum iterations reached without convergence.");
    }
};

#endif