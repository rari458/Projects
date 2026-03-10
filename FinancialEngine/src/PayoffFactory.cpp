// src/PayoffFactory.cpp

#include "../include/PayoffFactory.h"
#include <iostream>

PayoffFactory& PayoffFactory::Instance() {
    static PayoffFactory theFactory;
    return theFactory;
}

void PayoffFactory::RegisterPayoff(const std::string& PayoffId, CreatePayoffFunction Creator) {
    TheCreatorMap[PayoffId] = Creator;
}

std::unique_ptr<Payoff> PayoffFactory::CreatePayoff(const std::string& PayoffId, double Strike) {
    auto i = TheCreatorMap.find(PayoffId);
    if (i == TheCreatorMap.end()) {
        std::cerr << "Error: Unknown Payoff ID '" << PayoffId << "'" << std::endl;
        return nullptr;
    }
    return (i->second)(Strike);
}