// src/StrategyFactory.cpp

#include "../include/StrategyFactory.h"

#include <utility>

StrategyFactory& StrategyFactory::Instance() {
    static StrategyFactory factory;
    return factory;
}

void StrategyFactory::RegisterStrategy(const std::string& id, CreateStrategyFunction creator) {
    creators_[id] = std::move(creator);
}

std::unique_ptr<Strategy> StrategyFactory::CreateStrategy(const std::string& id) const {
    auto it = creators_.find(id);
    if (it == creators_.end()) {
        return nullptr;
    }
    return (it->second)();
}