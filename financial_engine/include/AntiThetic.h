// include/AntiThetic.h

#pragma once
#include "Random.h"
#include <vector>

class AntiThetic : public RandomBase {
public:
    explicit AntiThetic(const RandomBase& innerGenerator);

    AntiThetic(const AntiThetic& original);

    std::unique_ptr<RandomBase> clone() const override;
    void GetUniforms(std::vector<double>& variates) override;
    void GetGaussians(std::vector<double>& variates) override;
    void Reset() override;
    void ResetDimensionality(unsigned long NewDimensionality) override;

private:
    std::unique_ptr<RandomBase> InnerGenerator;
    bool Odd;
    std::vector<double> NextVariates;
};