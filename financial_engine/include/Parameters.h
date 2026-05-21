// include/Parameters.h

#pragma once
#include <memory>

class ParametersInner {
public:
    virtual ~ParametersInner() = default;
    virtual double Integral(double time1, double time2) const = 0;
    virtual double IntegralSquare(double time1, double time2) const = 0;
    virtual std::unique_ptr<ParametersInner> clone() const = 0;
};

class Parameters {
public:
    Parameters(double constant);
    Parameters(const ParametersInner& innerObject);
    Parameters(const Parameters& original);
    Parameters& operator=(const Parameters& original);
    virtual ~Parameters() = default;

    double Integral(double time1, double time2) const;
    double IntegralSquare(double time1, double time2) const;
    double Mean(double time1, double time2) const;
    double RootMeanSquare(double time1, double time2) const;

private:
    std::shared_ptr<ParametersInner> innerObjectPtr;
};

class ParametersConstant : public ParametersInner {
public:
    ParametersConstant(double constant);
    double Integral(double time1, double time2) const override;
    double IntegralSquare(double time1, double time2) const override;

    std::unique_ptr<ParametersInner> clone() const override;

private:
    double constant_;
    double constantSquare_;
};