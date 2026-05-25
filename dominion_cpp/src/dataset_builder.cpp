#include "dominion/noise.hpp"
#include "dominion/information.hpp"
#include "dominion/multifractal.hpp"
#include "dominion/microstructure_advanced.hpp"
#include "dominion/types.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <unordered_map>
#include <chrono>

#ifdef _OPENMP
#include <omp.h>
#endif

using namespace dominion;

struct DatasetRow {
    double time;
    std::unordered_map<std::string, double> features;
};

// Load CSV (simple parser)
std::vector<DatasetRow> load_csv(const std::string& path, int subsample = 1) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    std::string line;
    std::vector<std::string> headers;

    // Read header
    std::getline(file, line);
    std::stringstream ss(line);
    std::string col;
    while (std::getline(ss, col, ',')) {
        headers.push_back(col);
    }

    std::vector<DatasetRow> data;
    int row_num = 0;

    while (std::getline(file, line)) {
        if (row_num++ % subsample != 0) continue;

        std::stringstream ss(line);
        DatasetRow row;

        for (size_t i = 0; i < headers.size(); ++i) {
            std::string val;
            std::getline(ss, val, ',');

            if (headers[i] == "time") {
                row.time = std::stod(val);
            } else {
                try {
                    row.features[headers[i]] = std::stod(val);
                } catch (...) {
                    row.features[headers[i]] = std::nan("");
                }
            }
        }

        data.push_back(row);
    }

    return data;
}

// Reconstruct price from returns
PriceVec reconstruct_price(const std::vector<DatasetRow>& data, const std::string& return_col) {
    PriceVec prices;
    prices.reserve(data.size());

    double price = 1800.0;  // Starting price
    for (const auto& row : data) {
        auto it = row.features.find(return_col);
        if (it != row.features.end() && !std::isnan(it->second)) {
            price *= (1.0 + it->second);
        }
        prices.push_back(price);
    }

    return prices;
}

// Write CSV output
void write_csv(const std::string& path,
               const std::vector<DatasetRow>& original_data,
               const std::unordered_map<std::string, PriceVec>& new_features) {
    std::ofstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot write file: " + path);
    }

    // Write header
    file << "time";
    for (const auto& [name, _] : new_features) {
        file << "," << name;
    }
    for (const auto& [name, _] : original_data[0].features) {
        file << "," << name;
    }
    file << "\n";

    // Write data
    for (size_t i = 0; i < original_data.size(); ++i) {
        file << original_data[i].time;

        for (const auto& [name, vec] : new_features) {
            file << "," << (i < vec.size() ? std::to_string(vec[i]) : "");
        }

        for (const auto& [name, val] : original_data[i].features) {
            file << "," << val;
        }

        file << "\n";
    }
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input.csv> <output.csv> [subsample=1]\n";
        return 1;
    }

    std::string input_path = argv[1];
    std::string output_path = argv[2];
    int subsample = (argc > 3) ? std::stoi(argv[3]) : 1;

    auto start_time = std::chrono::high_resolution_clock::now();

    std::cout << "Loading dataset from " << input_path << "...\n";
    auto data = load_csv(input_path, subsample);
    std::cout << "Loaded " << data.size() << " rows\n";

    // Reconstruct price series
    std::cout << "Reconstructing price series...\n";
    auto prices = reconstruct_price(data, "pct_ret_1b");

    std::cout << "\n=== Computing advanced features ===\n";
    std::unordered_map<std::string, PriceVec> new_features;

    // 1. Hurst exponent
    std::cout << "1/10: Hurst exponent (R/S)...\n";
    new_features["hurst_60"] = multifractal::compute_hurst_rs(prices, 60);
    new_features["hurst_252"] = multifractal::compute_hurst_rs(prices, 252);

    // 2. Fractal dimension
    std::cout << "2/10: Fractal dimension...\n";
    new_features["fractal_dim_252"] = multifractal::compute_fractal_dimension(prices, 252);

    // 3. DFA
    std::cout << "3/10: Detrended fluctuation analysis...\n";
    new_features["dfa_252"] = multifractal::compute_dfa(prices, 252);

    // 4. Permutation entropy
    std::cout << "4/10: Permutation entropy...\n";
    new_features["perm_entropy_100"] = information::compute_permutation_entropy(prices, 3, 1, 100);

    // 5. Sample entropy
    std::cout << "5/10: Sample entropy...\n";
    new_features["sample_entropy_100"] = information::compute_sample_entropy(prices, 2, 0.2, 100);

    // 6. LZ complexity
    std::cout << "6/10: Lempel-Ziv complexity...\n";
    new_features["lz_complexity_100"] = information::compute_lz_complexity(prices, 100);

    // 7. Microstructure noise
    std::cout << "7/10: Microstructure noise models...\n";
    new_features["hansen_lunde_rv_60"] = microstructure::compute_hansen_lunde_rv(prices, 60);
    new_features["tsrv_60"] = microstructure::compute_tsrv(prices, 1, 5, 60);
    new_features["efficient_price_60"] = microstructure::estimate_efficient_price(prices, 60);
    new_features["noise_variance_60"] = microstructure::compute_noise_variance(prices, 60);
    new_features["micro_snr_60"] = microstructure::compute_microstructure_snr(prices, 60);

    // 8. SSA decomposition
    std::cout << "8/10: Singular spectrum analysis...\n";
    auto ssa_result = noise::compute_ssa(prices, 60, 3);
    new_features["ssa_trend"] = ssa_result.trend;
    new_features["ssa_noise"] = ssa_result.noise;
    if (!ssa_result.singular_values.empty()) {
        PriceVec sv0(prices.size(), ssa_result.singular_values[0]);
        new_features["ssa_sv0"] = sv0;
    }

    // 9. EMD
    std::cout << "9/10: Empirical mode decomposition...\n";
    auto emd_result = noise::compute_emd(prices, 5);
    if (!emd_result.imfs.empty()) {
        new_features["emd_imf0"] = emd_result.imfs[0];
    }
    if (emd_result.imfs.size() > 1) {
        new_features["emd_imf1"] = emd_result.imfs[1];
    }

    // 10. Wavelet decomposition
    std::cout << "10/10: Wavelet packet decomposition...\n";
    auto wavelet_result = noise::compute_wavelet_packet(prices, 5, "db4");
    if (!wavelet_result.details.empty()) {
        new_features["wavelet_d0_energy"] = PriceVec(prices.size(),
            wavelet_result.energies[0]);
    }

    std::cout << "\n=== Writing output ===\n";
    write_csv(output_path, data, new_features);

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);

    std::cout << "\n✅ Complete!\n";
    std::cout << "Output: " << output_path << "\n";
    std::cout << "Rows: " << data.size() << "\n";
    std::cout << "Original features: " << data[0].features.size() << "\n";
    std::cout << "New features: " << new_features.size() << "\n";
    std::cout << "Total features: " << (data[0].features.size() + new_features.size()) << "\n";
    std::cout << "Time: " << duration.count() << "s\n";

    return 0;
}
