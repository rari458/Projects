// include/Random.h

#pragma once
#include <vector>
#include <memory>
#include <random>

class RandomBase {
public:
    RandomBase(unsigned long Dimensionality);
    virtual ~RandomBase() = default;

    [[nodiscard]] unsigned long GetDimensionality() const;

    virtual void GetUniforms(std::vector<double>& variates) = 0;
    virtual void GetGaussians(std::vector<double>& variates) = 0;
    virtual void Reset() = 0;
    virtual void ResetDimensionality(unsigned long NewDimensionality);
    [[nodiscard]] virtual std::unique_ptr<RandomBase> clone() const = 0;

private:
    unsigned long Dimensionality;
};

class RandomMersenne : public RandomBase {
public:
    RandomMersenne(unsigned long Dimensionality, unsigned long Seed = 1234UL);

    void GetUniforms(std::vector<double>& variates) override;
    void GetGaussians(std::vector<double>& variates) override;
    void Reset() override;
    void ResetDimensionality(unsigned long NewDimensionality) override;
    [[nodiscard]] std::unique_ptr<RandomBase> clone() const override;

private:
    unsigned long InitialSeed;
    std::mt19937_64 Generator;
    std::normal_distribution<double> Distribution;
};