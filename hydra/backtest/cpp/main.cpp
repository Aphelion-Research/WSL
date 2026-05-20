#include "backtester.hpp"
#include <iostream>
#include <chrono>
#include <string>

int main(int argc, char* argv[]) {
    std::string db_path = "data/dominion.duckdb";
    std::string model_path = "artifacts/hydra/hydra_fused.onnx";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--db" && i + 1 < argc) db_path = argv[++i];
        if (arg == "--model" && i + 1 < argc) model_path = argv[++i];
    }

    // Synthetic test data for validation
    size_t n = 10000;
    std::vector<double> close(n, 1800.0);
    std::vector<double> high(n, 1801.0);
    std::vector<double> low(n, 1799.0);
    std::vector<double> atr(n, 5.0);
    std::vector<double> signals(n, 0.0);
    std::vector<double> confidences(n, 0.0);

    for (size_t i = 0; i < n; i += 30) {
        signals[i] = 1.0;
        confidences[i] = 0.65;
        // Make price go up after signal
        for (size_t j = i + 1; j < std::min(i + 20, n); ++j) {
            close[j] = 1800.0 + (j - i) * 0.5;
            high[j] = close[j] + 1.0;
            low[j] = close[j] - 0.5;
        }
    }

    auto start = std::chrono::high_resolution_clock::now();

    auto result = hydra::run_backtest(close, high, low, atr, signals, confidences);

    auto end = std::chrono::high_resolution_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();

    std::cout << "Backtest complete:" << std::endl;
    std::cout << "  Trades:    " << result.trades.size() << std::endl;
    std::cout << "  Sharpe:    " << result.sharpe << std::endl;
    std::cout << "  Win Rate:  " << result.win_rate << std::endl;
    std::cout << "  RR:        " << result.rr << std::endl;
    std::cout << "  Profit:    $" << result.profit << std::endl;
    std::cout << "  Max DD:    " << result.max_dd * 100 << "%" << std::endl;
    std::cout << "  Time:      " << ms << " us" << std::endl;
    std::cout << "  Bars/sec:  " << (n * 1000000.0 / ms) << std::endl;

    return 0;
}
