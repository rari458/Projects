// "csv.cpp"
#include "csv.hpp"

using namespace std;

namespace commons {

vector<CsvRow> read_csv(const string& path) {
    ifstream f(path);
    if (!f.is_open()) {
        throw runtime_error("Failed to open CSV: " + path);
    }
    
    vector<CsvRow> rows;
    string line;

    if (!getline(f, line)) {
        return rows;
    }

    {
        string lower = line;
        for (char& c : lower) c = static_cast<char>(tolower(static_cast<unsigned char>(c)));

        if (lower.find("date") != string::npos &&
            lower.find("close") != string::npos) {
            
        } else {
            stringstream ss(line);
            string dateStr, closeStr;
            if (getline(ss, dateStr, ',') && 
                getline(ss, closeStr, ',')) {
                try {
                    CsvRow row;
                    row.date  = dateStr;
                    row.close = stod(closeStr);
                    rows.push_back(row);
                } catch (...) {

                }
            }
        }
    }

    while (getline(f, line)) {
        if (line.size() < 3) continue;
        if (!line.empty() && line[0] == '#') continue;

        stringstream ss(line);
        string dateStr, closeStr;

        if (!getline(ss, dateStr, ',')) continue;
        if (!getline(ss, closeStr, ',')) continue;

        try {
            CsvRow row;
            row.date  = dateStr;
            row.close = stod(closeStr);
            rows.push_back(row);
        } catch (...) {

        }
    }

    return rows;
}

}