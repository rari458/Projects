// include/HyperOptimizer.h

#ifndef HYPEROPTIMIZER_H
#define HYPEROPTIMIZER_H

#include <vector>
#include <algorithm>
#include <random>
#include <fmt/core.h>
#include "Backtester.h"

struct Gene {
    int fast;
    int slow;
    int signal;
    double fitness;

    static Gene Random(std::mt19937& rng) {
        std::uniform_int_distribution<int> dist_fast(5, 50);
        std::uniform_int_distribution<int> dist_slow(2, 100);
        std::uniform_int_distribution<int> dist_signal(5, 30);

        int f = dist_fast(rng);
        int s = dist_slow(rng);
        if (f >= s) s = f + 5;

        return {f, s, dist_signal(rng), -999.0};
    }
};

class GeneticOptimizer {
public:
    static Gene evolve_macd(const std::vector<double>& prices, double initial_capital, int generations = 10, int population_size = 50) {
        std::random_device rd;
        std::mt19937 rng(rd());

        std::vector<Gene> population;
        for (int i = 0; i < population_size; ++i) {
            population.push_back(Gene::Random(rng));
        }

        for (int gen = 0; gen < generations; ++gen) {
            for (auto& individual : population) {
                individual.fitness = Evaluate(individual, prices, initial_capital);
            }

            std::sort(population.begin(), population.end(), [](const Gene& a, const Gene& b){
                return a.fitness > b.fitness;
            });

            std::vector<Gene> next_generation;

            int elite_count = population_size * 0.2;
            for (int i = 0; i < elite_count; ++i) next_generation.push_back(population[i]);

            while (next_generation.size() < static_cast<size_t>(population_size)) {
                Gene p1 = TournamentSelect(population, rng);
                Gene p2 = TournamentSelect(population, rng);
                Gene child = Crossover(p1, p2, rng);
                Mutate(child, rng);
                next_generation.push_back(child);
            }
            population = next_generation;
        }

        return population[0];
    }

private:
    static double Evaluate(const Gene& c, const std::vector<double>& prices, double capital) {
        Backtester engine(capital, "MACD", 1.0);
        engine.set_macd_parameters(c.fast, c.slow, c.signal);

        for (size_t t = 0; t < prices.size(); ++t) {
            engine.on_market_data("TARGET", static_cast<double>(t), prices[t], prices[t], prices[t], prices[t]);
        }
        return (engine.get_total_equity() - capital) / capital * 100.0;
    }

    static Gene TournamentSelect(const std::vector<Gene>& pop, std::mt19937& rng) {
        std::uniform_int_distribution<int> dist_idx(0, pop.size() - 1);
        Gene best = pop[dist_idx(rng)];
        for (int i = 0; i < 2; ++i) {
            Gene contender = pop[dist_idx(rng)];
            if (contender.fitness > best.fitness) best = contender;
        }
        return best;
    }

    static Gene Crossover(const Gene& p1, Gene& p2, std::mt19937& rng) {
        std::uniform_int_distribution<int> dist_split(0, 1);
        Gene child = {
            dist_split(rng) ? p1.fast : p2.fast,
            dist_split(rng) ? p1.slow : p2.slow,
            dist_split(rng) ? p1.signal : p2.signal,
            -999.0
        };
        if (child.fast >= child.slow) child.slow = child.fast + 5;
        return child;
    }

    static void Mutate(Gene& c, std::mt19937& rng) {
        std::uniform_real_distribution<double> dist_prob(0.0, 1.0);
        std::uniform_int_distribution<int> dist_val(-2, 2);

        if (dist_prob(rng) < 0.1) c.fast = std::max(2, c.fast + dist_val(rng));
        if (dist_prob(rng) < 0.1) c.slow = std::max(c.fast + 5, c.slow + dist_val(rng));
        if (dist_prob(rng) < 0.1) c.signal = std::max(2, c.signal + dist_val(rng));
    }
};

#endif