// include/Payoff.h

#pragma once
#include <memory>

class Payoff {
public:
    virtual ~Payoff() = default;
    [[nodiscard]] virtual double operator()(double spot) const = 0;
    [[nodiscard]] virtual std::unique_ptr<Payoff> clone() const = 0;
};

class PayoffCall : public Payoff {
public:
    explicit PayoffCall(double strike);
    [[nodiscard]] double operator()(double spot) const override;
    [[nodiscard]] std::unique_ptr<Payoff> clone() const override;

private:
    double strike_;
};

class PayoffPut : public Payoff {
public:
    explicit PayoffPut(double strike);
    [[nodiscard]] double operator()(double spot) const override;
    [[nodiscard]] std::unique_ptr<Payoff> clone() const override;

private:
    double strike_;
};