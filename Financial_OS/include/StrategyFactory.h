// include/StrategyFactory.h

#pragma once
#include <functional>
#include <memory>
#include <string>
#include <map>

#include "Strategy.h"

class StrategyFactory {
public:
    using CreateStrategyFunction = std::function<std::unique_ptr<Strategy>()>;

    static StrategyFactory & Instance();

    void RegisterStrategy(const std::string& id, CreateStrategyFunction creator);

    [[nodiscard]] std::unique_ptr<Strategy> CreateStrategy(const std::string& id) const;

private:
    StrategyFactory() = default;
    StrategyFactory(const StrategyFactory&) = delete;
    StrategyFactory& operator=(const StrategyFactory&) = delete;

    std::map<std::string, CreateStrategyFunction> creators_;
};
