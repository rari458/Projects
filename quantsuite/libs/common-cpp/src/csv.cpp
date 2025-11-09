#include "commons/csv.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>

using namespace std;

namespace commons {
vector<Row> read_csv(const string& path) {
    ifstream in(path);
    if(!in.is_open()) throw runtime_error("Cannot open: " + path);
    string line;
    getline(in, line);
    vector<Row> rows;
    while(getline(in, line)) {
        stringstream ss(line);
        string date, close_s;
        if (getline(ss, date, ',') && getline(ss, close_s, ',')) {
            rows.push_back({date, stod(close_s)});
        }
    }
    return rows;
}
}