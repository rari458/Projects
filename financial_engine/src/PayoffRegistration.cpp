// src/PayoffRegistration.cpp

#include "../include/PayoffFactory.h"
#include "../include/Payoff.h"
#include <memory>

namespace {
    class PayoffHelper {
    public:
        PayoffHelper() {
            PayoffFactory& factory = PayoffFactory::Instance();

            factory.RegisterPayoff("call", [](double Strike) {
                return std::make_unique<PayoffCall>(Strike);
            });

            factory.RegisterPayoff("put", [](double Strike) {
                return std::make_unique<PayoffPut>(Strike);
            });
        }
    };

    PayoffHelper registerHelper;
}