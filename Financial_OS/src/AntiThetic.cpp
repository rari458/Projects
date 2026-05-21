// src/AntiThetic.cpp

#include "../include/AntiThetic.h"

AntiThetic::AntiThetic(const RandomBase& innerGenerator)
    : RandomBase(innerGenerator.GetDimensionality()),
        InnerGenerator(innerGenerator.clone()),
        Odd(true) {
    NextVariates.resize(GetDimensionality());
}

AntiThetic::AntiThetic(const AntiThetic& original)
    : RandomBase(original),
        InnerGenerator(original.InnerGenerator->clone()),
        Odd(original.Odd),
        NextVariates(original.NextVariates) {
}

std::unique_ptr<RandomBase> AntiThetic::clone() const {
    return std::make_unique<AntiThetic>(*this);
}

void AntiThetic::GetUniforms(std::vector<double>& variates) {
    if (Odd) {
        InnerGenerator->GetUniforms(variates);
        for (unsigned long i = 0; i < GetDimensionality(); ++i) {
            NextVariates[i] = variates[i];
        }
        Odd = false;
    } else {
        for (unsigned long i = 0; i < GetDimensionality(); ++i) {
            variates[i] = 1.0 - NextVariates[i];
        }
        Odd = true;
    }
}

void AntiThetic::GetGaussians(std::vector<double>& variates) {
    if (Odd) {
        InnerGenerator->GetGaussians(variates);
        for (unsigned long i = 0; i < GetDimensionality(); ++i) {
            NextVariates[i] = variates[i];
        }
        Odd = false;
    } else {
        for (unsigned long i = 0; i < GetDimensionality(); ++i) {
            variates[i] = -NextVariates[i];
        }
        Odd = true;
    }
}

void AntiThetic::Reset() {
    InnerGenerator->Reset();
    Odd = true;
}

void AntiThetic::ResetDimensionality(unsigned long NewDimensionality) {
    RandomBase::ResetDimensionality(NewDimensionality);
    InnerGenerator->ResetDimensionality(NewDimensionality);
    NextVariates.resize(NewDimensionality);
    InnerGenerator->Reset();
    Odd = true;
}