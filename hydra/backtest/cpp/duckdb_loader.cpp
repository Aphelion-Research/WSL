#include <vector>
#include <string>

#ifdef HAS_DUCKDB
#include <duckdb.hpp>
#endif

namespace hydra {

struct BarData {
    std::vector<double> close;
    std::vector<double> high;
    std::vector<double> low;
    std::vector<double> volume;
};

BarData load_bars_from_duckdb([[maybe_unused]] const std::string& db_path,
                              [[maybe_unused]] const std::string& table) {
    BarData data;
#ifdef HAS_DUCKDB
    duckdb::DuckDB db(db_path);
    duckdb::Connection con(db);

    auto result = con.Query(
        "SELECT close, high, low, volume FROM " + table + " ORDER BY ts");

    if (result->HasError()) return data;

    for (size_t i = 0; i < result->RowCount(); ++i) {
        data.close.push_back(result->GetValue(0, i).GetValue<double>());
        data.high.push_back(result->GetValue(1, i).GetValue<double>());
        data.low.push_back(result->GetValue(2, i).GetValue<double>());
        data.volume.push_back(result->GetValue(3, i).GetValue<double>());
    }
#endif
    return data;
}

std::vector<std::vector<float>> load_features_from_duckdb(
    [[maybe_unused]] const std::string& db_path) {
    std::vector<std::vector<float>> features;
#ifdef HAS_DUCKDB
    duckdb::DuckDB db(db_path);
    duckdb::Connection con(db);

    auto cols_result = con.Query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'features' AND column_name NOT IN ('ts', 'symbol')");

    if (cols_result->HasError()) return features;

    std::string cols;
    for (size_t i = 0; i < cols_result->RowCount(); ++i) {
        if (i > 0) cols += ", ";
        cols += "\"" + cols_result->GetValue(0, i).ToString() + "\"";
    }

    auto result = con.Query("SELECT " + cols + " FROM features ORDER BY ts");
    if (result->HasError()) return features;

    size_t n_cols = result->ColumnCount();
    features.resize(result->RowCount());
    for (size_t i = 0; i < result->RowCount(); ++i) {
        features[i].resize(n_cols);
        for (size_t j = 0; j < n_cols; ++j) {
            features[i][j] = result->GetValue(j, i).GetValue<float>();
        }
    }
#endif
    return features;
}

} // namespace hydra
