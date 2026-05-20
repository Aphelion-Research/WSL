#pragma once

#include <vector>
#include <cstdint>

namespace hydra {

struct Trade {
    int64_t entry_bar;
    int64_t exit_bar;
    int8_t direction;
    double entry_px;
    double exit_px;
    double pnl;
    int32_t bars_held;
    double size;
};

struct BacktestConfig {
    double spread = 0.30;
    double slippage = 0.10;
    double commission = 2.00;
    double capital = 100000.0;
    double kelly_frac = 0.25;
    double pos_cap = 0.25;
    double stop_mult = 1.0;
    double target_mult = 2.0;
    int horizon = 20;
    double trailing_be_at = 1.0;
};

struct BacktestResult {
    std::vector<Trade> trades;
    std::vector<double> equity;
    double sharpe;
    double win_rate;
    double rr;
    double profit;
    double max_dd;
};

BacktestResult run_backtest(
    const std::vector<double>& close,
    const std::vector<double>& high,
    const std::vector<double>& low,
    const std::vector<double>& atr,
    const std::vector<double>& signals,
    const std::vector<double>& confidences,
    const BacktestConfig& cfg = BacktestConfig{}
);

} // namespace hydra
