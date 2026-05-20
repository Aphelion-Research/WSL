#include "backtester.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace hydra {

static double kelly_size(double confidence, double capital,
                         double payoff_ratio, double kelly_frac, double pos_cap) {
    double p = confidence;
    double b = payoff_ratio;
    double edge = p * b - (1.0 - p);
    if (edge <= 0.0) return 0.0;
    double f_star = edge / b;
    double size = kelly_frac * f_star * capital;
    return std::min(size, pos_cap * capital);
}

BacktestResult run_backtest(
    const std::vector<double>& close,
    const std::vector<double>& high,
    const std::vector<double>& low,
    const std::vector<double>& atr,
    const std::vector<double>& signals,
    const std::vector<double>& confidences,
    const BacktestConfig& cfg)
{
    BacktestResult result;
    size_t n = close.size();
    double equity = cfg.capital;
    result.equity.reserve(n + 1);
    result.equity.push_back(equity);

    bool in_trade = false;
    int64_t entry_bar = 0;
    double entry_px = 0.0;
    int8_t direction = 0;
    double stop_px = 0.0;
    double target_px = 0.0;
    double trade_size = 0.0;
    double entry_atr = 0.0;
    bool stop_moved = false;

    double payoff_ratio = cfg.target_mult / cfg.stop_mult;

    for (size_t t = 0; t < n; ++t) {
        if (!in_trade) {
            int sig = (signals[t] > 0.5) ? 1 : (signals[t] < -0.5) ? -1 : 0;
            double conf = confidences[t];

            if (sig != 0 && conf > 0 && std::isfinite(atr[t]) && atr[t] > 0) {
                direction = sig;
                double cost = cfg.spread / 2.0 + cfg.slippage;
                entry_px = close[t] + direction * cost;
                entry_atr = atr[t];
                stop_px = entry_px - direction * cfg.stop_mult * entry_atr;
                target_px = entry_px + direction * cfg.target_mult * entry_atr;
                trade_size = kelly_size(conf, equity, payoff_ratio,
                                       cfg.kelly_frac, cfg.pos_cap);
                if (trade_size <= 0) {
                    result.equity.push_back(equity);
                    continue;
                }
                entry_bar = t;
                in_trade = true;
                stop_moved = false;
            }
        } else {
            double profit_ticks = direction * (close[t] - entry_px);
            if (!stop_moved && profit_ticks >= cfg.trailing_be_at * entry_atr) {
                stop_px = entry_px + direction * cfg.spread;
                stop_moved = true;
            }

            double exit_px = 0.0;
            bool should_exit = false;

            if (direction == 1) {
                if (low[t] <= stop_px) { exit_px = stop_px; should_exit = true; }
                else if (high[t] >= target_px) { exit_px = target_px; should_exit = true; }
            } else {
                if (high[t] >= stop_px) { exit_px = stop_px; should_exit = true; }
                else if (low[t] <= target_px) { exit_px = target_px; should_exit = true; }
            }

            if (!should_exit && (int64_t(t) - entry_bar) >= cfg.horizon) {
                exit_px = close[t] - direction * (cfg.spread / 2.0 + cfg.slippage);
                should_exit = true;
            }

            if (should_exit) {
                double raw_pnl = direction * (exit_px - entry_px) * trade_size / entry_atr;
                double pnl = raw_pnl - cfg.commission;
                equity += pnl;

                Trade trade;
                trade.entry_bar = entry_bar;
                trade.exit_bar = t;
                trade.direction = direction;
                trade.entry_px = entry_px;
                trade.exit_px = exit_px;
                trade.pnl = pnl;
                trade.bars_held = int32_t(t - entry_bar);
                trade.size = trade_size;
                result.trades.push_back(trade);

                in_trade = false;
            }
        }
        result.equity.push_back(equity);
    }

    // Compute metrics
    size_t n_trades = result.trades.size();
    if (n_trades > 0) {
        int winners = 0;
        double sum_win = 0, sum_loss = 0;
        for (auto& t : result.trades) {
            if (t.pnl > 0) { winners++; sum_win += t.pnl; }
            else { sum_loss += std::abs(t.pnl); }
        }
        result.win_rate = double(winners) / n_trades;
        double mean_win = winners > 0 ? sum_win / winners : 0;
        double mean_loss = (n_trades - winners) > 0 ?
                           sum_loss / (n_trades - winners) : 1;
        result.rr = mean_loss > 0 ? mean_win / mean_loss : 0;
    }
    result.profit = equity - cfg.capital;

    // Max drawdown
    double peak = cfg.capital;
    double max_dd = 0;
    for (double eq : result.equity) {
        peak = std::max(peak, eq);
        double dd = (peak - eq) / peak;
        max_dd = std::max(max_dd, dd);
    }
    result.max_dd = max_dd;

    // Sharpe (approximate from equity curve)
    if (result.equity.size() > 2) {
        std::vector<double> rets;
        rets.reserve(result.equity.size() - 1);
        for (size_t i = 1; i < result.equity.size(); ++i) {
            if (result.equity[i-1] > 0)
                rets.push_back((result.equity[i] - result.equity[i-1]) / result.equity[i-1]);
        }
        if (!rets.empty()) {
            double mean = std::accumulate(rets.begin(), rets.end(), 0.0) / rets.size();
            double sq_sum = 0;
            for (double r : rets) sq_sum += (r - mean) * (r - mean);
            double stddev = std::sqrt(sq_sum / (rets.size() - 1));
            result.sharpe = stddev > 1e-15 ? std::sqrt(252.0) * mean / stddev : 0;
        }
    }

    return result;
}

} // namespace hydra
