// src/Parameters.cpp

#include "../include/Parameters.h"

Parameters::Parameters(const ParametersInner& innerObject) {
    innerObjectPtr = innerObject.clone();
}

Parameters::Parameters(double constant) {
    innerObjectPtr = std::make_shared<ParametersConstant>(constant);
}

Parameters::Parameters(const Parameters& original) {
    innerObjectPtr = original.innerObjectPtr;
}

Parameters& Parameters::operator=(const Parameters& original) {
    if (this != &original) {
        innerObjectPtr = original.innerObjectPtr;
    }
    return *this;
}

double Parameters::Integral(double time1, double time2) const {
    return innerObjectPtr->Integral(time1, time2);
}

double Parameters::IntegralSquare(double time1, double time2) const {
    return innerObjectPtr->IntegralSquare(time1, time2);
}

double Parameters::Mean(double time1, double time2) const {
    double total = Integral(time1, time2);
    return total / (time2 - time1);
}

double Parameters::RootMeanSquare(double time1, double time2) const {
    double total = IntegralSquare(time1, time2);
    return total / (time2 - time1);
}

ParametersConstant::ParametersConstant(double constant)
    : constant_(constant), constantSquare_(constant * constant) {}

double ParametersConstant::Integral(double time1, double time2) const {
    return constant_ * (time2 - time1);
}

double ParametersConstant::IntegralSquare(double time1, double time2) const {
    return constantSquare_ * (time2 - time1);
}

std::unique_ptr<ParametersInner> ParametersConstant::clone() const {
    return std::make_unique<ParametersConstant>(*this);
}