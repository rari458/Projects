# ⚡ Financial Engine (C++20 & Python)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![C++](https://img.shields.io/badge/C++-20-blue)
![Python](https://img.shields.io/badge/Python-3.12-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

A high-performance derivative pricing engine built with **Modern C++ (C++20)**, featuring **Python bindings** for research flexibility. This project implements Monte Carlo simulations, Binomial Trees, and Black-Scholes formulas using industry-standard design patterns.

## 🚀 Key Features

* **Hybrid Architecture**: Core computation in C++ for speed, Interface in Python for productivity (via `pybind11`).
* **Design Patterns**:
    * **Factory Pattern**: Dynamic option creation via string IDs.
    * **Strategy Pattern**: Encapsulated Payoff algorithms (Call/Put).
    * **Singleton**: Centralized registration for Payoff types.
* **Pricing Models**:
    * **Monte Carlo Simulation**: For European options (Path-dependent ready).
    * **Binomial Tree**: For American options (supports early exercise).
    * **Black-Scholes Analytic**: For exact benchmarking and Greeks calculation.
* **Risk Management**:
    * Numerical Greeks Engine (Delta, Gamma).
    * Implied Volatility Solver (Newton-Raphson / Bisection).

## 🛠 Tech Stack

* **Language**: C++20, Python 3.12
* **Build System**: CMake (FetchContent), Make
* **Libraries**:
    * `pybind11`: Seamless C++/Python interoperability.
    * `fmt`: Modern string formatting.
    * `GoogleTest`: Unit testing framework.
* **Visualization**: Matplotlib, NumPy

## 📊 Performance Benchmark

Calculating 1,000 pricing requests:
* **Execution Time**: ~0.00104 sec
* **Throughput**: ~1,000,000 ops/sec

## 💻 Installation & Usage

### Prerequisites
* CMake 3.20+
* C++ Compiler (GCC 10+ or Clang 12+)
* Python 3.10+

### Build
```bash
# 1. Clone the repository
git clone [https://github.com/rari458/FinancialEngine.git](https://github.com/rari458/FinancialEngine.git)
cd FinancialEngine

# 2. Configure and Build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
