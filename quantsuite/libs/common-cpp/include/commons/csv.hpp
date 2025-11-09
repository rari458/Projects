#pragma once
#include <string>
#include <vector>

using namespace std;

namespace commons {
    struct Row { string date; double close; };
    vector<Row> read_csv(const string& path);
}