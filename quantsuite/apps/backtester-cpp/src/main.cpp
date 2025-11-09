#include <iostream>
#include <vector>
#include <string>
#include "metrics.hpp"
#include "commons/csv.hpp"

using namespace std;

int main(int argc, char** argv) {
    if(argc<2) {
        cerr << "Usage: backtester <csv_path>\n";
        return 1;
    }
    auto rows = commons::read_csv(argv[1]);
    vector<double> prices;
    prices.reserve(rows.size());
    for(auto& r: rows) prices.push_back(r.close);

    cout << "N=" << prices.size() << "\n";
    cout << "Total Return=" << total_return(prices) << "\n";
    cout << "CAGR252=" << cagr252(prices) << "\n";
    return 0;
}