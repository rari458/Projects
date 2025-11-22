// csv.hpp

#pragma once
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <stdexcept>

using namespace std;

namespace commons {

struct CsvRow {
    string date;
    double close;
};

vector<CsvRow> read_csv(const string& path);

} // namespace commons