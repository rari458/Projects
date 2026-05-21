// include/PayoffFactory.h

#pragma once
#include "Payoff.h"
#include <map>
#include <string>
#include <functional>
#include <memory>

class PayoffFactory {
public:
    using CreatePayoffFunction = std::function<std::unique_ptr<Payoff>(double)>;

    static PayoffFactory& Instance();

    void RegisterPayoff(const std::string& PayoffId, CreatePayoffFunction Creator);

    std::unique_ptr<Payoff> CreatePayoff(const std::string& PayoffId, double Strike);

private:
    PayoffFactory() = default;

    PayoffFactory(const PayoffFactory&) = delete;
    PayoffFactory& operator=(const PayoffFactory&) = delete;

    std::map<std::string, CreatePayoffFunction> TheCreatorMap;
};