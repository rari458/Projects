// src/Random.cpp

#include "../include/Random.h"

RandomBase::RandomBase(unsigned long Dimensionality_)
    : Dimensionality(Dimensionality_) {}

unsigned long RandomBase::GetDimensionality() const {
    return Dimensionality;
}

void RandomBase::ResetDimensionality(unsigned long NewDimensionality) {
    Dimensionality = NewDimensionality;
}

RandomMersenne::RandomMersenne(unsigned long Dimensionality, unsigned long Seed)
    : RandomBase(Dimensionality), InitialSeed(Seed), Generator(Seed), Distribution(0.0, 1.0) {    
}

void RandomMersenne::GetUniforms(std::vector<double>& variates) {
    std::uniform_real_distribution<double> uniDist(0.0, 1.0);
    for (unsigned long i = 0; i < GetDimensionality(); ++i) {
        variates[i] = uniDist(Generator);
    }
}

void RandomMersenne::GetGaussians(std::vector<double>& variates) {
    for (unsigned long i = 0; i < GetDimensionality(); ++i) {
        variates[i] = Distribution(Generator);
    }
}

void RandomMersenne::Reset() {
    Generator.seed(InitialSeed);
    Distribution.reset();
}

void RandomMersenne::ResetDimensionality(unsigned long NewDimensionality) {
    RandomBase::ResetDimensionality(NewDimensionality);
    Generator.seed(InitialSeed);
    Distribution.reset();
}

std::unique_ptr<RandomBase> RandomMersenne::clone() const {
    return std::make_unique<RandomMersenne>(*this);
}