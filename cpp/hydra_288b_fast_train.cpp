// HYDRA 288b Fast Training - C++ Accelerated Path (8-core optimized)
// Fixed commission only, no spread/slippage modeling

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <random>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <cstring>
#include <thread>
#include <mutex>

#ifdef _OPENMP
#include <omp.h>
#define HYDRA_OPENMP 1
#else
#define HYDRA_OPENMP 0
#endif

using namespace std;
using namespace std::chrono;

// ============================================================================
// TYPES
// ============================================================================

struct Config {
    string name;
    string model_type; // "logistic", "stump_ensemble", "conservative", "ftrl", "passive_aggressive", "rank_ensemble"
    int n_features;
    int n_epochs;
    double learning_rate;
    double l2_lambda;
    int n_stumps;
    vector<pair<double, double>> thresholds;

    // FTRL params
    double ftrl_alpha;
    double ftrl_beta;
    double ftrl_l1;
    double ftrl_l2;

    // PA params
    double pa_C;

    // Feature scoring
    string feature_score_method; // "pearson", "spearman", "mi", "stability", "composite"

    // Regime
    bool regime_aware;

    // Objective
    string objective; // "sharpe", "net_pnl", "calmar", "utility"
};

struct FoldResult {
    string config_name = "";
    string model_type = "";
    int fold = 0;
    int n_features = 0;
    double threshold_long = 0.0;
    double threshold_short = 0.0;

    // Classification metrics
    double auc = 0.0;
    double balanced_accuracy = 0.0;
    double accuracy = 0.0;
    double f1 = 0.0;
    double precision = 0.0;
    double recall = 0.0;
    double long_rate = 0.0;
    double short_rate = 0.0;
    double flat_rate = 0.0;

    // Trading metrics
    double gross_pnl = 0.0;
    double commission_paid = 0.0;
    double net_pnl = 0.0;
    double n_trades = 0.0;
    double sharpe = 0.0;
    double max_drawdown = 0.0;
    double calmar = 0.0;
    double utility = 0.0;

    // Feature scoring
    string feature_score_method = "";
    double avg_pearson_ic = 0.0;
    double avg_spearman_ic = 0.0;
    double avg_mi = 0.0;
    double avg_stability = 0.0;
    double avg_turnover = 0.0;

    // Regime
    bool regime_aware = false;
    string regime_breakdown_json = "";

    // Objective
    string objective = "";
};

struct Meta {
    int rows;
    int cols;
    string label;
    int horizon;
    double commission_per_lot;
    double gold_oz_per_lot;
};

// ============================================================================
// GLOBAL STATE
// ============================================================================

bool VERBOSE = false;
bool SMOKE = false;
bool BENCHMARK = false;
bool MATH_SWEEP = false;
int MAX_SWEEP_CONFIGS = 100;
int MAX_SWEEP_RUNTIME_MINUTES = 30;
int THREAD_COUNT = 1;
string PARALLEL_MODE = "inner";
auto RUN_START = high_resolution_clock::now();
ofstream PROGRESS_JSONL;
ofstream RUNTIME_LOG;
ofstream PARTIAL_CSV;
mutex OUTPUT_MUTEX;
bool DISABLE_RANK_ENSEMBLE = false;
string ONLY_MODEL = "";
int DEBUG_FOLD_TIMEOUT_SECONDS = 0;
string PROGRESS_JSONL_PATH = "";
bool QUIET_CONSOLE = false;

// OOS mode globals
string SPLIT_MODE = "";
double TRAIN_YEARS = 10.0;
double OOS_YEARS = 1.0;
double STARTING_BALANCE = 10000.0;
double MAX_DRAWDOWN_PCT = 0.10;
bool HARD_STOP_ON_DRAWDOWN = false;
string EQUITY_OUTPUT_PATH = "runs/hydra_cpp_288b_oos_equity.csv";

// Broker simulator globals
double LEVERAGE = 50.0;
double MAX_LOSS_PCT = 0.06;
double MAINTENANCE_MARGIN_RATIO = 0.5;
bool REQUIRE_BRACKET_ORDERS = true;
int MAX_OPEN_POSITIONS = 1;
int MAX_HOLDING_BARS = 288;
double DEFAULT_RR = 2.0;
double ATR_SL_MULT = 1.5;
bool TRAILING_STOP_ENABLED = false;
double TRAILING_ATR_MULT = 1.0;
bool USE_FIBONACCI_EXITS = false;
string TRADES_OUTPUT_PATH = "runs/hydra_cpp_288b_trades.csv";

// Confidence-based RR
bool CONFIDENCE_RR = false;
double MIN_RR = 1.0;
double MAX_RR = 3.0;

// Risk-based sizing
double RISK_PER_TRADE_PCT = 0.0025;
bool AUTO_SIZE_BY_RISK = false;

// R-based trailing stop
double TRAIL_ACTIVATE_R = 1.0;
double TRAIL_DISTANCE_R = 0.5;
double MOVE_SL_TO_BREAKEVEN_AT_R = 1.0;

// Kelly sizing
bool KELLY_SIZING = false;
string KELLY_MODE = "strict"; // strict, floor, off
double KELLY_FRACTION = 0.25;
int KELLY_LOOKBACK_TRADES = 100;
int KELLY_MIN_SAMPLES = 30;
double MAX_RISK_PER_TRADE_PCT = 0.0025;
double MIN_RISK_PER_TRADE_PCT = 0.00025;
double MAX_LOT_SIZE = 1.0;
double MIN_LOT_SIZE = 0.01;

// Drawdown risk throttle
bool DRAWDOWN_RISK_THROTTLE = false;

// Signal filters
double MIN_CONFIDENCE = 0.0;
int MAX_TRADES_PER_CONFIG = 0; // 0 = unlimited

// Signal sanity gate
bool REJECT_CONSTANT_PROBA = false;
double MAX_SATURATION_RATE = 0.95;
double MIN_PROBA_STD = 0.001;
bool NO_TRAILING_ABLATION = false;

// Feature normalization
bool NORMALIZE_FEATURES = true; // default ON for train-oos

// Probability calibration
bool CALIBRATE_PROBA = false;

// Regime filter
bool REGIME_FILTER = false;
bool STRICT_REGIME_DIRECTION = false;

// Direction control
bool ALLOW_LONG = true;
bool ALLOW_SHORT = true;
bool ALLOW_CLOSE_AND_REVERSE = false;
double MIN_LONG_CONFIDENCE = 0.02;
double MIN_SHORT_CONFIDENCE = 0.02;

// Direction mode
string DIRECTION_MODE = "both"; // both, long-only, short-only, dual-specialist
bool SAVE_MODELS = false;
bool SAVE_BEST_CANDIDATE = false;
string MODEL_DIR = "runs/models";
string LONG_MODEL_PATH = "";
string SHORT_MODEL_PATH = "";
string LOAD_LONG_MODEL_PATH = "";
string LOAD_SHORT_MODEL_PATH = "";
string DUAL_COMBINER = "edge"; // edge, confidence, probability
double MIN_EDGE_GAP = 0.0;
string DUAL_LONG_FALLBACK = "require-model"; // require-model, baseline_always_long

// ============================================================================
// UTILITIES
// ============================================================================

class ScopedTimer {
    string name;
    high_resolution_clock::time_point start;
public:
    ScopedTimer(const string& n) : name(n), start(high_resolution_clock::now()) {}
    ~ScopedTimer() {
        auto end = high_resolution_clock::now();
        auto ms = duration_cast<milliseconds>(end - start).count();
        if (VERBOSE) {
            cout << "  [TIMING] " << name << ": " << ms << " ms" << endl;
        }
    }
};

double elapsed_seconds() {
    auto now = high_resolution_clock::now();
    return duration_cast<milliseconds>(now - RUN_START).count() / 1000.0;
}

void log_event(const string& event, const string& extra = "") {
    lock_guard<mutex> lock(OUTPUT_MUTEX);

    auto now = system_clock::now();
    auto t = system_clock::to_time_t(now);

    stringstream ss;
    ss << "{\"timestamp\":\"" << put_time(localtime(&t), "%Y-%m-%dT%H:%M:%S")
       << "\",\"elapsed_seconds\":" << elapsed_seconds()
       << ",\"event\":\"" << event << "\"";

    if (!extra.empty()) {
        ss << "," << extra;
    }

    ss << "}\n";

    if (PROGRESS_JSONL.is_open()) {
        PROGRESS_JSONL << ss.str();
        PROGRESS_JSONL.flush();
    }

    if (RUNTIME_LOG.is_open()) {
        RUNTIME_LOG << ss.str();
        RUNTIME_LOG.flush();
    }
}

void print_progress(const string& msg, bool force = false) {
    if (!QUIET_CONSOLE && (VERBOSE || force)) {
        lock_guard<mutex> lock(OUTPUT_MUTEX);
        cout << msg << endl;
        cout.flush();
    }
}

string json_escape(const string& s) {
    string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c == '"') out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    return out;
}

void emit_progress_event(const string& json_line) {
    if (!PROGRESS_JSONL_PATH.empty() && PROGRESS_JSONL.is_open()) {
        lock_guard<mutex> lock(OUTPUT_MUTEX);
        PROGRESS_JSONL << json_line << "\n";
        PROGRESS_JSONL.flush();
    }
}

int get_thread_count(const string& requested) {
    if (requested == "auto") {
        int hw = thread::hardware_concurrency();
        return min(hw > 0 ? hw : 8, 8); // Cap at 8 by default
    }
    return stoi(requested);
}

void configure_threads(int n_threads) {
    THREAD_COUNT = n_threads;

    #if HYDRA_OPENMP
    omp_set_num_threads(THREAD_COUNT);
    #endif

    cout << "\n[THREAD CONFIG]" << endl;
    cout << "Hardware concurrency: " << thread::hardware_concurrency() << endl;
    cout << "Requested threads: " << n_threads << endl;
    cout << "Actual threads: " << THREAD_COUNT << endl;
    cout << "OpenMP enabled: " << (HYDRA_OPENMP ? "yes" : "no") << endl;
    cout << "Parallel mode: " << PARALLEL_MODE << endl;

    #if HYDRA_OPENMP
    cout << "OpenMP version: " << _OPENMP << endl;
    #else
    if (n_threads > 1) {
        cout << "WARNING: OpenMP disabled; hot loops may not use all cores." << endl;
    }
    #endif
}

// ============================================================================
// METRICS
// ============================================================================

double compute_auc(const vector<int>& y_true, const vector<double>& y_proba) {
    // Mann-Whitney U / Wilcoxon rank-sum AUC with proper tie handling
    size_t n = y_true.size();
    if (n == 0) return 0.5;

    long long n_pos = 0, n_neg = 0;
    for (size_t i = 0; i < n; ++i) {
        if (y_true[i] == 1) n_pos++;
        else n_neg++;
    }

    if (n_pos == 0 || n_neg == 0) {
        if (VERBOSE) cout << "  [WARN] AUC: n_pos=" << n_pos << " n_neg=" << n_neg << " → returning 0.5" << endl;
        return 0.5;
    }

    // Check if all probabilities are constant (common in degenerate models)
    bool all_equal = true;
    for (size_t i = 1; i < n; ++i) {
        if (abs(y_proba[i] - y_proba[0]) > 1e-12) {
            all_equal = false;
            break;
        }
    }
    if (all_equal) {
        if (VERBOSE) cout << "  [WARN] AUC: all probabilities constant → returning 0.5" << endl;
        return 0.5;
    }

    // Sort indices by predicted probability ascending
    vector<size_t> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&y_proba](size_t a, size_t b) {
        return y_proba[a] < y_proba[b];
    });

    // Assign average ranks (1-based) handling ties
    vector<double> ranks(n);
    size_t i = 0;
    while (i < n) {
        size_t j = i;
        while (j < n && y_proba[order[j]] == y_proba[order[i]]) {
            j++;
        }
        double avg_rank = (double)(i + 1 + j) / 2.0; // average of 1-based ranks i+1..j
        for (size_t k = i; k < j; ++k) {
            ranks[order[k]] = avg_rank;
        }
        i = j;
    }

    // Sum ranks for positive class
    double rank_sum_pos = 0.0;
    for (size_t idx = 0; idx < n; ++idx) {
        if (y_true[idx] == 1) {
            rank_sum_pos += ranks[idx];
        }
    }

    // AUC = (R_pos - n_pos*(n_pos+1)/2) / (n_pos * n_neg)
    double auc = (rank_sum_pos - (double)n_pos * (n_pos + 1) / 2.0) / ((double)n_pos * (double)n_neg);

    // Sanity assertion
    if (auc < 0.0 || auc > 1.0) {
        cerr << "VALIDATION_BUG_FOUND: AUC=" << auc << " outside [0,1]! n_pos=" << n_pos
             << " n_neg=" << n_neg << " rank_sum_pos=" << rank_sum_pos << endl;
        exit(1);
    }

    return auc;
}

double compute_accuracy(const vector<int>& y_true, const vector<int>& y_pred) {
    int correct = 0;
    #pragma omp parallel for reduction(+:correct) if (HYDRA_OPENMP)
    for (size_t i = 0; i < y_true.size(); ++i) {
        if (y_true[i] == y_pred[i]) correct++;
    }
    return (double)correct / y_true.size();
}

double compute_balanced_accuracy(const vector<int>& y_true, const vector<int>& y_pred) {
    int tp = 0, tn = 0, fp = 0, fn = 0;

    #pragma omp parallel for reduction(+:tp,tn,fp,fn) if (HYDRA_OPENMP)
    for (size_t i = 0; i < y_true.size(); ++i) {
        if (y_true[i] == 1 && y_pred[i] == 1) tp++;
        else if (y_true[i] == 0 && y_pred[i] == 0) tn++;
        else if (y_true[i] == 0 && y_pred[i] == 1) fp++;
        else fn++;
    }

    double sens = (tp + fn > 0) ? (double)tp / (tp + fn) : 0.0;
    double spec = (tn + fp > 0) ? (double)tn / (tn + fp) : 0.0;

    return (sens + spec) / 2.0;
}

double compute_f1(const vector<int>& y_true, const vector<int>& y_pred) {
    int tp = 0, fp = 0, fn = 0;

    #pragma omp parallel for reduction(+:tp,fp,fn) if (HYDRA_OPENMP)
    for (size_t i = 0; i < y_true.size(); ++i) {
        if (y_true[i] == 1 && y_pred[i] == 1) tp++;
        else if (y_true[i] == 0 && y_pred[i] == 1) fp++;
        else if (y_true[i] == 1 && y_pred[i] == 0) fn++;
    }

    double prec = (tp + fp > 0) ? (double)tp / (tp + fp) : 0.0;
    double rec = (tp + fn > 0) ? (double)tp / (tp + fn) : 0.0;

    if (prec + rec == 0) return 0.0;
    return 2 * prec * rec / (prec + rec);
}

// ============================================================================
// PNL CALCULATION — next-bar close-to-close delta
// ============================================================================

struct PnLResult {
    double gross_pnl;
    double commission;
    double net_pnl;
    int n_position_changes;
    double max_drawdown;
    double sharpe;
};

// PnL from sequential M5 bar moves (NOT horizon returns).
// gross[t] = position[t] * (close[t+1] - close[t]) * gold_oz_per_lot * lot_size
// commission[t] = |position[t] - position[t-1]| * lot_size * commission_per_lot
PnLResult calculate_pnl(
    const vector<int>& positions,
    const vector<double>& next_bar_delta, // precomputed close[t+1] - close[t]
    double lot_size,
    double commission_per_lot,
    double gold_oz_per_lot
) {
    PnLResult result = {0, 0, 0, 0, 0, 0};
    int n = positions.size();
    if (n == 0) return result;

    vector<double> net_pnl_series(n, 0.0);

    // Parallel per-bar PnL
    #pragma omp parallel for if (HYDRA_OPENMP)
    for (int i = 0; i < n; ++i) {
        double gross = positions[i] * next_bar_delta[i] * gold_oz_per_lot * lot_size;
        int prev_pos = (i == 0) ? 0 : positions[i-1];
        int pos_change = abs(positions[i] - prev_pos);
        double comm = pos_change * lot_size * commission_per_lot;
        net_pnl_series[i] = gross - comm;
    }

    // Sequential reduction
    for (int i = 0; i < n; ++i) {
        int prev_pos = (i == 0) ? 0 : positions[i-1];
        int pos_change = abs(positions[i] - prev_pos);
        double gross = positions[i] * next_bar_delta[i] * gold_oz_per_lot * lot_size;

        result.gross_pnl += gross;
        result.commission += pos_change * lot_size * commission_per_lot;
        result.net_pnl += net_pnl_series[i];
        result.n_position_changes += pos_change;
    }

    // Max drawdown
    double cum = 0.0, running_max = 0.0, max_dd = 0.0;
    for (int i = 0; i < n; ++i) {
        cum += net_pnl_series[i];
        running_max = max(running_max, cum);
        max_dd = max(max_dd, running_max - cum);
    }
    result.max_drawdown = max_dd;

    // Annualized Sharpe (M5 bars: 288 per trading day, 252 days/year)
    double mean_pnl = result.net_pnl / n;
    double var_pnl = 0.0;
    for (int i = 0; i < n; ++i) {
        double d = net_pnl_series[i] - mean_pnl;
        var_pnl += d * d;
    }
    double std_pnl = sqrt(var_pnl / n);

    if (std_pnl > 0) {
        result.sharpe = (mean_pnl / std_pnl) * sqrt(252.0 * 288.0);
    }

    return result;
}

// ============================================================================
// FEATURE SCORING ENGINE (MULTI-METHOD)
// ============================================================================

struct FeatureScore {
    int feature_idx = 0;
    double pearson_ic = 0.0;
    double spearman_ic = 0.0;
    double mutual_info = 0.0;
    double stability = 0.0;
    double turnover = 0.0;
    double composite = 0.0;
};

// Pearson correlation (same as old ranking)
double compute_pearson_ic(const vector<double>& feat, const vector<int>& y) {
    int n = feat.size();
    double mean_feat = 0.0, mean_label = 0.0;
    for (int i = 0; i < n; ++i) {
        mean_feat += feat[i];
        mean_label += y[i];
    }
    mean_feat /= n;
    mean_label /= n;

    double num = 0.0, denom_feat = 0.0, denom_label = 0.0;
    for (int i = 0; i < n; ++i) {
        double df = feat[i] - mean_feat;
        double dl = y[i] - mean_label;
        num += df * dl;
        denom_feat += df * df;
        denom_label += dl * dl;
    }

    if (denom_feat > 0 && denom_label > 0) {
        return num / (sqrt(denom_feat) * sqrt(denom_label));
    }
    return 0.0;
}

// Spearman rank correlation
double compute_spearman_ic(const vector<double>& feat, const vector<int>& y) {
    int n = feat.size();
    vector<pair<double, int>> feat_pairs(n), label_pairs(n);
    for (int i = 0; i < n; ++i) {
        feat_pairs[i] = {feat[i], i};
        label_pairs[i] = {(double)y[i], i};
    }

    sort(feat_pairs.begin(), feat_pairs.end());
    sort(label_pairs.begin(), label_pairs.end());

    vector<double> feat_rank(n), label_rank(n);
    for (int i = 0; i < n; ++i) {
        feat_rank[feat_pairs[i].second] = i + 1;
        label_rank[label_pairs[i].second] = i + 1;
    }

    return compute_pearson_ic(feat_rank, y); // Pearson on ranks
}

// Mutual information (discretized)
double compute_mutual_info(const vector<double>& feat, const vector<int>& y, int n_bins = 10) {
    int n = feat.size();
    if (n == 0) return 0.0;

    // Discretize feature into quantile bins
    vector<double> sorted_feat = feat;
    sort(sorted_feat.begin(), sorted_feat.end());

    vector<int> feat_bin(n);
    for (int i = 0; i < n; ++i) {
        auto it = lower_bound(sorted_feat.begin(), sorted_feat.end(), feat[i]);
        int bin = (it - sorted_feat.begin()) * n_bins / n;
        feat_bin[i] = min(bin, n_bins - 1);
    }

    // Compute joint counts
    vector<vector<int>> joint(n_bins, vector<int>(2, 0));
    vector<int> feat_count(n_bins, 0);
    vector<int> label_count(2, 0);

    for (int i = 0; i < n; ++i) {
        joint[feat_bin[i]][y[i]]++;
        feat_count[feat_bin[i]]++;
        label_count[y[i]]++;
    }

    // MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
    double mi = 0.0;
    for (int b = 0; b < n_bins; ++b) {
        for (int l = 0; l < 2; ++l) {
            if (joint[b][l] > 0) {
                double pxy = (double)joint[b][l] / n;
                double px = (double)feat_count[b] / n;
                double py = (double)label_count[l] / n;
                mi += pxy * log(pxy / (px * py + 1e-12));
            }
        }
    }

    return mi;
}

// Stability score (4-block chronological split, penalize sign flips)
double compute_stability(const vector<double>& feat, const vector<int>& y) {
    int n = feat.size();
    if (n < 400) return 0.0; // need enough samples

    int block_size = n / 4;
    vector<double> block_ics;

    for (int b = 0; b < 4; ++b) {
        int start = b * block_size;
        int end = (b == 3) ? n : start + block_size;

        vector<double> block_feat(feat.begin() + start, feat.begin() + end);
        vector<int> block_y(y.begin() + start, y.begin() + end);

        double ic = compute_pearson_ic(block_feat, block_y);
        block_ics.push_back(ic);
    }

    // Mean and std of ICs
    double mean_ic = 0.0;
    for (double ic : block_ics) mean_ic += ic;
    mean_ic /= block_ics.size();

    double std_ic = 0.0;
    for (double ic : block_ics) std_ic += (ic - mean_ic) * (ic - mean_ic);
    std_ic = sqrt(std_ic / block_ics.size());

    // Penalize sign flips
    int sign_flips = 0;
    for (size_t i = 1; i < block_ics.size(); ++i) {
        if ((block_ics[i] > 0) != (block_ics[i-1] > 0)) sign_flips++;
    }

    double stability = mean_ic / (std_ic + 0.01);
    stability -= sign_flips * 0.5; // penalty

    return stability;
}

// Turnover penalty (feature sign changes)
double compute_turnover(const vector<double>& feat) {
    int n = feat.size();
    if (n < 2) return 0.0;

    int sign_changes = 0;
    for (int i = 1; i < n; ++i) {
        if ((feat[i] > 0) != (feat[i-1] > 0)) sign_changes++;
    }

    return (double)sign_changes / n;
}

// Composite score
double compute_composite_score(const FeatureScore& fs) {
    return 0.30 * abs(fs.pearson_ic)
         + 0.20 * abs(fs.spearman_ic)
         + 0.20 * fs.mutual_info
         + 0.20 * abs(fs.stability)
         - 0.10 * fs.turnover;
}

// Score all features with given method
vector<FeatureScore> score_all_features(
    const vector<vector<float>>& X,
    const vector<int>& y,
    const string& method
) {
    ScopedTimer timer("Feature scoring: " + method);

    int n_samples = X.size();
    int n_total_features = X[0].size();
    vector<FeatureScore> scores(n_total_features);

    #pragma omp parallel for schedule(dynamic, 8) if (HYDRA_OPENMP)
    for (int j = 0; j < n_total_features; ++j) {
        vector<double> feat(n_samples);
        for (int i = 0; i < n_samples; ++i) {
            feat[i] = X[i][j];
        }

        FeatureScore fs;
        fs.feature_idx = j;

        if (method == "pearson" || method == "composite") {
            fs.pearson_ic = compute_pearson_ic(feat, y);
        }
        if (method == "spearman" || method == "composite") {
            fs.spearman_ic = compute_spearman_ic(feat, y);
        }
        if (method == "mi" || method == "composite") {
            fs.mutual_info = compute_mutual_info(feat, y);
        }
        if (method == "stability" || method == "composite") {
            fs.stability = compute_stability(feat, y);
        }
        if (method == "composite") {
            fs.turnover = compute_turnover(feat);
        }

        if (method == "pearson") fs.composite = abs(fs.pearson_ic);
        else if (method == "spearman") fs.composite = abs(fs.spearman_ic);
        else if (method == "mi") fs.composite = fs.mutual_info;
        else if (method == "stability") fs.composite = abs(fs.stability);
        else if (method == "composite") fs.composite = compute_composite_score(fs);

        scores[j] = fs;
    }

    return scores;
}

// Rank and select top N features
vector<int> rank_features_by_score(
    const vector<FeatureScore>& scores,
    int n_features
) {
    vector<int> indices(scores.size());
    iota(indices.begin(), indices.end(), 0);

    sort(indices.begin(), indices.end(), [&scores](int a, int b) {
        return scores[a].composite > scores[b].composite;
    });

    int n = min(n_features, (int)scores.size());
    vector<int> top(indices.begin(), indices.begin() + n);

    print_progress("  Scored " + to_string(scores.size()) + " features → top " + to_string(n));

    return top;
}

// ============================================================================
// LOGISTIC REGRESSION (SGD with parallel gradient)
// ============================================================================

class LogisticRegression {
public:
    vector<double> weights;
    double bias;
    double learning_rate;
    double l2_lambda;
    int n_epochs;
    bool training_failed = false;

    LogisticRegression(int n_features, double lr = 0.01, double l2 = 0.001, int epochs = 50)
        : learning_rate(lr), l2_lambda(l2), n_epochs(epochs) {
        weights.resize(n_features, 0.0);
        bias = 0.0;
    }

    double sigmoid(double z) {
        z = max(-20.0, min(20.0, z));
        return 1.0 / (1.0 + exp(-z));
    }

    void fit(const vector<vector<float>>& X, const vector<int>& y) {
        ScopedTimer timer("Logistic training");

        int n_samples = X.size();
        int n_features = X[0].size();
        const double GRAD_CLIP = 5.0;

        for (int epoch = 0; epoch < n_epochs; ++epoch) {
            double grad_bias = 0.0;
            vector<double> grad_weights(n_features, 0.0);

            #pragma omp parallel if (HYDRA_OPENMP)
            {
                double local_grad_bias = 0.0;
                vector<double> local_grad_weights(n_features, 0.0);

                #pragma omp for nowait
                for (int i = 0; i < n_samples; ++i) {
                    double z = bias;
                    for (int j = 0; j < n_features; ++j) {
                        z += weights[j] * X[i][j];
                    }
                    z = max(-20.0, min(20.0, z));

                    double pred = 1.0 / (1.0 + exp(-z));
                    double error = pred - y[i];

                    local_grad_bias += error;
                    for (int j = 0; j < n_features; ++j) {
                        local_grad_weights[j] += error * X[i][j];
                    }
                }

                #pragma omp critical
                {
                    grad_bias += local_grad_bias;
                    for (int j = 0; j < n_features; ++j) {
                        grad_weights[j] += local_grad_weights[j];
                    }
                }
            }

            // Gradient clipping
            double grad_norm = grad_bias * grad_bias;
            for (int j = 0; j < n_features; ++j) grad_norm += grad_weights[j] * grad_weights[j];
            grad_norm = sqrt(grad_norm);
            if (grad_norm > GRAD_CLIP * n_samples) {
                double scale = GRAD_CLIP * n_samples / grad_norm;
                grad_bias *= scale;
                for (int j = 0; j < n_features; ++j) grad_weights[j] *= scale;
            }

            // NaN/Inf check
            if (!isfinite(grad_norm)) {
                training_failed = true;
                break;
            }

            bias -= learning_rate * grad_bias / n_samples;
            for (int j = 0; j < n_features; ++j) {
                grad_weights[j] = grad_weights[j] / n_samples + l2_lambda * weights[j];
                weights[j] -= learning_rate * grad_weights[j];
            }
        }
    }

    vector<double> predict_proba(const vector<vector<float>>& X) {
        ScopedTimer timer("Logistic prediction");

        int n_samples = X.size();
        int n_features = X[0].size();
        vector<double> probas(n_samples);

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int i = 0; i < n_samples; ++i) {
            double z = bias;
            for (int j = 0; j < n_features; ++j) {
                z += weights[j] * X[i][j];
            }
            z = max(-20.0, min(20.0, z));
            probas[i] = 1.0 / (1.0 + exp(-z));
        }

        return probas;
    }
};

// ============================================================================
// FTRL-PROXIMAL LOGISTIC REGRESSION
// ============================================================================

class FTRLLogistic {
public:
    vector<double> z;
    vector<double> n;
    double alpha, beta, l1, l2;
    int n_features;

    FTRLLogistic(int n_feat, double a = 0.1, double b = 1.0, double L1 = 1.0, double L2 = 1.0)
        : alpha(a), beta(b), l1(L1), l2(L2), n_features(n_feat) {
        z.resize(n_feat, 0.0);
        n.resize(n_feat, 0.0);
    }

    double sigmoid(double x) {
        return 1.0 / (1.0 + exp(-x));
    }

    double get_weight(int j) {
        if (abs(z[j]) <= l1) return 0.0;
        return -(z[j] - (z[j] > 0 ? l1 : -l1)) / ((beta + sqrt(n[j])) / alpha + l2);
    }

    void fit(const vector<vector<float>>& X, const vector<int>& y) {
        ScopedTimer timer("FTRL training");

        int n_samples = X.size();
        for (int epoch = 0; epoch < 1; ++epoch) {
            for (int i = 0; i < n_samples; ++i) {
                double wx = 0.0;
                for (int j = 0; j < n_features; ++j) {
                    wx += get_weight(j) * X[i][j];
                }
                wx = max(-20.0, min(20.0, wx));
                double pred = sigmoid(wx);
                double grad = pred - y[i];

                for (int j = 0; j < n_features; ++j) {
                    double g = grad * X[i][j];
                    g = max(-5.0, min(5.0, g));
                    double sigma = (sqrt(n[j] + g * g) - sqrt(n[j])) / alpha;
                    z[j] += g - sigma * get_weight(j);
                    n[j] += g * g;
                }
            }
        }
    }

    vector<double> predict_proba(const vector<vector<float>>& X) {
        ScopedTimer timer("FTRL prediction");

        int n_samples = X.size();
        vector<double> probas(n_samples);

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int i = 0; i < n_samples; ++i) {
            double wx = 0.0;
            for (int j = 0; j < n_features; ++j) {
                wx += get_weight(j) * X[i][j];
            }
            wx = max(-20.0, min(20.0, wx));
            probas[i] = sigmoid(wx);
        }

        return probas;
    }
};

// ============================================================================
// PASSIVE-AGGRESSIVE CLASSIFIER
// ============================================================================

class PassiveAggressive {
public:
    vector<double> weights;
    double bias;
    double C;
    int n_epochs;

    PassiveAggressive(int n_features, double c = 1.0, int epochs = 10)
        : C(c), n_epochs(epochs) {
        weights.resize(n_features, 0.0);
        bias = 0.0;
    }

    double sigmoid(double z) {
        return 1.0 / (1.0 + exp(-z));
    }

    void fit(const vector<vector<float>>& X, const vector<int>& y) {
        ScopedTimer timer("PA training");

        int n_samples = X.size();
        int n_features = X[0].size();

        for (int epoch = 0; epoch < n_epochs; ++epoch) {
            for (int i = 0; i < n_samples; ++i) {
                // Forward
                double z = bias;
                for (int j = 0; j < n_features; ++j) {
                    z += weights[j] * X[i][j];
                }

                int y_pred = (z >= 0) ? 1 : -1;
                int y_true = (y[i] == 1) ? 1 : -1;

                if (y_true * z < 1.0) { // hinge loss
                    // Compute norm
                    double norm_sq = 0.0;
                    for (int j = 0; j < n_features; ++j) {
                        norm_sq += X[i][j] * X[i][j];
                    }
                    norm_sq += 1.0; // bias

                    double loss = max(0.0, 1.0 - y_true * z);
                    double tau = loss / norm_sq;
                    tau = min(tau, C); // cap

                    // Update
                    for (int j = 0; j < n_features; ++j) {
                        weights[j] += tau * y_true * X[i][j];
                    }
                    bias += tau * y_true;
                }
            }
        }
    }

    vector<double> predict_proba(const vector<vector<float>>& X) {
        ScopedTimer timer("PA prediction");

        int n_samples = X.size();
        int n_features = X[0].size();
        vector<double> probas(n_samples);

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int i = 0; i < n_samples; ++i) {
            double z = bias;
            for (int j = 0; j < n_features; ++j) {
                z += weights[j] * X[i][j];
            }
            probas[i] = sigmoid(z);
        }

        return probas;
    }
};

// ============================================================================
// RANK ENSEMBLE (IC-weighted rank aggregation)
// ============================================================================

class RankEnsemble {
public:
    vector<int> feature_indices;
    vector<double> feature_weights;
    vector<double> feature_signs;
    double sigmoid_a, sigmoid_b;

    RankEnsemble() : sigmoid_a(1.0), sigmoid_b(0.0) {}

    void fit(const vector<vector<float>>& X, const vector<int>& y, const vector<FeatureScore>& scores, const vector<int>& top_features) {
        ScopedTimer timer("Rank ensemble training");

        int n_samples = X.size();
        feature_indices = top_features;

        // Store weights and signs from feature scores
        feature_weights.resize(top_features.size());
        feature_signs.resize(top_features.size());

        double total_weight = 0.0;
        for (size_t i = 0; i < top_features.size(); ++i) {
            int feat_idx = top_features[i];
            const auto& fs = scores[feat_idx];

            feature_weights[i] = fs.composite;
            feature_signs[i] = (fs.pearson_ic >= 0) ? 1.0 : -1.0;
            total_weight += fs.composite;
        }

        // Safety: if total_weight too small, fall back to uniform
        if (total_weight < 1e-9) {
            if (VERBOSE) print_progress("  [WARN] RankEnsemble: total_weight near zero, using uniform weights");
            for (size_t i = 0; i < feature_weights.size(); ++i) {
                feature_weights[i] = 1.0;
            }
            total_weight = (double)feature_weights.size();
        }

        // Fit sigmoid calibration on train data
        vector<double> raw_scores = compute_raw_scores(X);

        // Simple linear fit: minimize (y - sigmoid(a*raw + b))^2
        // Use train labels for calibration
        double sum_y = 0.0, sum_raw = 0.0;
        for (int i = 0; i < n_samples; ++i) {
            sum_y += y[i];
            sum_raw += raw_scores[i];
        }
        double mean_y = sum_y / n_samples;
        double mean_raw = sum_raw / n_samples;

        double num = 0.0, denom = 0.0;
        for (int i = 0; i < n_samples; ++i) {
            num += (raw_scores[i] - mean_raw) * (y[i] - mean_y);
            denom += (raw_scores[i] - mean_raw) * (raw_scores[i] - mean_raw);
        }

        // Safety: if denom too small, fallback to logit(mean_y)
        if (denom < 1e-9) {
            if (VERBOSE) print_progress("  [WARN] RankEnsemble: raw score variance near zero, using constant prob");
            sigmoid_a = 0.0;
            // Logit transform of mean_y (clamped to avoid infinity)
            double p = max(1e-6, min(1.0 - 1e-6, mean_y));
            sigmoid_b = log(p / (1.0 - p));
        } else {
            sigmoid_a = num / denom;
            sigmoid_b = mean_y - sigmoid_a * mean_raw;
        }

        print_progress("  Rank ensemble: " + to_string(top_features.size()) + " features, sigmoid_a=" + to_string(sigmoid_a).substr(0, 5));
    }

    vector<double> compute_raw_scores(const vector<vector<float>>& X) {
        int n_samples = X.size();
        vector<double> raw_scores(n_samples, 0.0);

        // Compute rolling quantile rank per feature (on train only, approximate with local zscore)
        double total_weight = 0.0;
        for (double w : feature_weights) total_weight += w;

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int i = 0; i < n_samples; ++i) {
            double score = 0.0;
            for (size_t f = 0; f < feature_indices.size(); ++f) {
                int feat_idx = feature_indices[f];
                double val = X[i][feat_idx];

                // Simple zscore approximation (train mean/std computed per feature)
                double rank_zscore = val; // TODO: proper rank transform if needed

                score += feature_signs[f] * rank_zscore * feature_weights[f];
            }
            raw_scores[i] = score / (total_weight + 1e-12);
        }

        return raw_scores;
    }

    vector<double> predict_proba(const vector<vector<float>>& X) {
        ScopedTimer timer("Rank ensemble prediction");

        vector<double> raw_scores = compute_raw_scores(X);

        vector<double> probas(raw_scores.size());
        #pragma omp parallel for if (HYDRA_OPENMP)
        for (size_t i = 0; i < raw_scores.size(); ++i) {
            double z = sigmoid_a * raw_scores[i] + sigmoid_b;
            // Clamp z to avoid overflow in exp(-z)
            z = max(-30.0, min(30.0, z));
            probas[i] = 1.0 / (1.0 + exp(-z));
        }

        return probas;
    }
};

// ============================================================================
// STUMP ENSEMBLE (parallel stump training)
// ============================================================================

struct Stump {
    int feature_idx;
    double threshold;
    int left_class;
    int right_class;
    double weight;
};

class StumpEnsemble {
public:
    vector<Stump> stumps;
    int n_stumps;

    StumpEnsemble(int n = 50) : n_stumps(n) {}

    void fit(const vector<vector<float>>& X, const vector<int>& y) {
        ScopedTimer timer("Stump ensemble training");

        int n_samples = X.size();
        int n_features = X[0].size();

        stumps.resize(n_stumps);

        random_device rd;
        mt19937 gen(42);
        uniform_int_distribution<> feat_dist(0, n_features - 1);

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int s = 0; s < n_stumps; ++s) {
            // Random feature (deterministic seed + offset)
            mt19937 local_gen(42 + s);
            uniform_int_distribution<> local_feat_dist(0, n_features - 1);
            int feat_idx = local_feat_dist(local_gen);

            // Extract feature values
            vector<double> feat_vals(n_samples);
            for (int i = 0; i < n_samples; ++i) {
                feat_vals[i] = X[i][feat_idx];
            }

            // Median threshold
            vector<double> sorted_vals = feat_vals;
            nth_element(sorted_vals.begin(), sorted_vals.begin() + sorted_vals.size() / 2, sorted_vals.end());
            double threshold = sorted_vals[sorted_vals.size() / 2];

            // Predict left/right
            int left_pos = 0, left_neg = 0, right_pos = 0, right_neg = 0;
            for (int i = 0; i < n_samples; ++i) {
                if (feat_vals[i] <= threshold) {
                    if (y[i] == 1) left_pos++;
                    else left_neg++;
                } else {
                    if (y[i] == 1) right_pos++;
                    else right_neg++;
                }
            }

            int left_class = (left_pos > left_neg) ? 1 : 0;
            int right_class = (right_pos > right_neg) ? 1 : 0;

            stumps[s] = {feat_idx, threshold, left_class, right_class, 1.0};
        }
    }

    vector<double> predict_proba(const vector<vector<float>>& X) {
        ScopedTimer timer("Stump ensemble prediction");

        int n_samples = X.size();
        vector<double> probas(n_samples, 0.0);

        #pragma omp parallel for if (HYDRA_OPENMP)
        for (int i = 0; i < n_samples; ++i) {
            double vote = 0.0;
            for (const auto& stump : stumps) {
                int pred_class = (X[i][stump.feature_idx] <= stump.threshold)
                    ? stump.left_class
                    : stump.right_class;
                vote += pred_class * stump.weight;
            }
            probas[i] = vote / stumps.size();
        }

        return probas;
    }
};

// ============================================================================
// FEATURE NORMALIZATION (train mean/std, applied to both train and OOS)
// ============================================================================

struct FeatureNormalizer {
    vector<double> means;
    vector<double> stds;
    int n_features = 0;

    void fit(const vector<vector<float>>& X_train) {
        if (X_train.empty()) return;
        n_features = X_train[0].size();
        means.resize(n_features, 0.0);
        stds.resize(n_features, 0.0);
        int n = X_train.size();
        for (int j = 0; j < n_features; ++j) {
            double sum = 0.0;
            for (int i = 0; i < n; ++i) sum += X_train[i][j];
            means[j] = sum / n;
            double var = 0.0;
            for (int i = 0; i < n; ++i) {
                double d = X_train[i][j] - means[j];
                var += d * d;
            }
            stds[j] = sqrt(var / n);
        }
    }

    void transform(vector<vector<float>>& X) {
        for (auto& row : X) {
            for (int j = 0; j < n_features; ++j) {
                if (stds[j] < 1e-9) row[j] = 0.0f;
                else row[j] = (float)((row[j] - means[j]) / stds[j]);
            }
        }
    }
};

// ============================================================================
// PLATT CALIBRATION (logistic fit on raw probabilities)
// ============================================================================

struct PlattCalibrator {
    double a = 0.0;
    double b = 0.0;
    bool fitted = false;

    void fit(const vector<double>& raw_proba, const vector<int>& y) {
        int n = raw_proba.size();
        if (n < 50) return;

        a = 0.0; b = 0.0;
        double lr = 0.01;
        for (int epoch = 0; epoch < 100; ++epoch) {
            double grad_a = 0.0, grad_b = 0.0;
            for (int i = 0; i < n; ++i) {
                double z = a * raw_proba[i] + b;
                z = max(-20.0, min(20.0, z));
                double p = 1.0 / (1.0 + exp(-z));
                double err = p - y[i];
                grad_a += err * raw_proba[i];
                grad_b += err;
            }
            a -= lr * grad_a / n;
            b -= lr * grad_b / n;
        }
        fitted = true;
    }

    vector<double> transform(const vector<double>& raw_proba) {
        vector<double> cal(raw_proba.size());
        for (size_t i = 0; i < raw_proba.size(); ++i) {
            double z = a * raw_proba[i] + b;
            z = max(-20.0, min(20.0, z));
            cal[i] = 1.0 / (1.0 + exp(-z));
        }
        return cal;
    }
};

// ============================================================================
// REGIME COMPUTATION
// ============================================================================

struct RegimeInfo {
    vector<int> regime; // per-bar: +1 bullish, -1 bearish, 0 neutral
    double train_median_vol = 0.0;
};

RegimeInfo compute_regime(const vector<double>& closes, int start, int end, int window = 288) {
    RegimeInfo info;
    int n = end - start;
    info.regime.resize(n, 0);

    vector<double> vols;
    for (int i = 0; i < n; ++i) {
        int abs_i = start + i;
        if (abs_i < window) { info.regime[i] = 0; continue; }

        // Trend slope: linear regression slope over window
        double sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0;
        for (int k = 0; k < window; ++k) {
            double x = k;
            double y = closes[abs_i - window + 1 + k];
            sum_x += x; sum_y += y; sum_xy += x * y; sum_xx += x * x;
        }
        double slope = (window * sum_xy - sum_x * sum_y) / (window * sum_xx - sum_x * sum_x);

        // Volatility: std of returns over window
        double ret_sum = 0.0, ret_sum_sq = 0.0;
        int ret_count = 0;
        for (int k = 1; k < window; ++k) {
            double ret = closes[abs_i - window + 1 + k] - closes[abs_i - window + k];
            ret_sum += ret; ret_sum_sq += ret * ret; ret_count++;
        }
        double vol = 0.0;
        if (ret_count > 1) {
            double mean_ret = ret_sum / ret_count;
            vol = sqrt((ret_sum_sq / ret_count) - mean_ret * mean_ret);
        }
        vols.push_back(vol);

        info.regime[i] = (slope > 0) ? 1 : -1;
    }

    // Compute median vol for train
    if (!vols.empty()) {
        vector<double> sorted_vols = vols;
        sort(sorted_vols.begin(), sorted_vols.end());
        info.train_median_vol = sorted_vols[sorted_vols.size() / 2];
    }

    return info;
}

// ============================================================================
// THRESHOLD SEARCH (multi-objective: sharpe/net_pnl/calmar/utility/excess_utility)
// ============================================================================

pair<double, double> find_best_threshold(
    const vector<double>& y_proba,
    const vector<double>& next_bar_delta,
    const vector<pair<double, double>>& candidates,
    double lot_size,
    double commission_per_lot,
    double gold_oz_per_lot,
    const string& objective
) {
    ScopedTimer timer("Threshold search: " + objective);

    int n_candidates = candidates.size();
    vector<double> objectives(n_candidates, -1e9);

    #pragma omp parallel for if (HYDRA_OPENMP)
    for (int c = 0; c < n_candidates; ++c) {
        double long_th = candidates[c].first;
        double short_th = candidates[c].second;

        int n = y_proba.size();
        vector<int> positions(n);
        for (int i = 0; i < n; ++i) {
            if (y_proba[i] >= long_th) positions[i] = 1;
            else if (y_proba[i] <= short_th) positions[i] = -1;
            else positions[i] = 0;
        }

        // Per-bar net PnL using next-bar delta
        vector<double> net_pnl_series(n, 0.0);
        double total_commission = 0.0;
        int total_turnover = 0;

        for (int i = 0; i < n; ++i) {
            double gross = positions[i] * next_bar_delta[i] * gold_oz_per_lot * lot_size;
            int prev_pos = (i == 0) ? 0 : positions[i-1];
            int pos_change = abs(positions[i] - prev_pos);
            double comm = pos_change * lot_size * commission_per_lot;
            net_pnl_series[i] = gross - comm;
            total_commission += comm;
            total_turnover += pos_change;
        }

        // Sharpe
        double sum = 0.0;
        for (int i = 0; i < n; ++i) sum += net_pnl_series[i];
        double net_pnl = sum;
        double mean_pnl = sum / n;

        double var = 0.0;
        for (int i = 0; i < n; ++i) {
            double d = net_pnl_series[i] - mean_pnl;
            var += d * d;
        }
        double std_pnl = sqrt(var / n);

        double sharpe = 0.0;
        if (std_pnl > 0) {
            sharpe = (mean_pnl / std_pnl) * sqrt(252.0 * 288.0);
        }

        // Max drawdown
        double cum = 0.0, running_max = 0.0, max_dd = 0.0;
        for (int i = 0; i < n; ++i) {
            cum += net_pnl_series[i];
            running_max = max(running_max, cum);
            max_dd = max(max_dd, running_max - cum);
        }

        double calmar = (max_dd > 0) ? (net_pnl / max_dd) : 0.0;

        // Utility
        double utility = net_pnl
                       - 0.5 * max_dd
                       - 2.0 * total_commission
                       - 1000.0 * ((double)total_turnover / n);

        // Baseline PnL (always-long) for excess_utility
        double baseline_pnl = 0.0;
        double baseline_cum = 0.0, baseline_max = 0.0, baseline_dd = 0.0;
        for (int i = 0; i < n; ++i) {
            double bl_gross = 1.0 * next_bar_delta[i] * gold_oz_per_lot * lot_size;
            int bl_prev = 1;
            int bl_change = (i == 0) ? 1 : 0;
            double bl_comm = bl_change * lot_size * commission_per_lot;
            double bl_net = bl_gross - bl_comm;
            baseline_pnl += bl_net;
            baseline_cum += bl_net;
            baseline_max = max(baseline_max, baseline_cum);
            baseline_dd = max(baseline_dd, baseline_max - baseline_cum);
        }

        double excess_return = net_pnl - baseline_pnl;
        double excess_utility = excess_return
                              - 0.5 * max(0.0, max_dd - baseline_dd)
                              - 2.0 * total_commission
                              - 1000.0 * ((double)total_turnover / n);
        // Only positive excess counts
        if (excess_return <= 0) excess_utility = -1e6;

        // Select objective
        double obj_val = 0.0;
        if (objective == "sharpe") obj_val = sharpe;
        else if (objective == "net_pnl") obj_val = net_pnl;
        else if (objective == "calmar") obj_val = calmar;
        else if (objective == "utility") obj_val = utility;
        else if (objective == "excess_utility") obj_val = excess_utility;
        else obj_val = sharpe; // default

        objectives[c] = obj_val;
    }

    // Find best
    int best_idx = 0;
    for (int c = 1; c < n_candidates; ++c) {
        if (objectives[c] > objectives[best_idx]) {
            best_idx = c;
        }
    }

    print_progress("  Best threshold: (" + to_string(candidates[best_idx].first) + ", " + to_string(candidates[best_idx].second) + ") | " + objective + "=" + to_string(objectives[best_idx]).substr(0, 5));

    return candidates[best_idx];
}

// ============================================================================
// FOLD TRAINING
// ============================================================================

FoldResult train_fold(
    const Config& config,
    int fold_idx,
    const vector<vector<float>>& X,
    const vector<int>& y,
    const vector<double>& next_bar_delta, // close[t+1] - close[t]
    const vector<int>& train_indices,
    const vector<int>& test_indices,
    double lot_size,
    double commission_per_lot,
    double gold_oz_per_lot
) {
    FoldResult result;
    result.config_name = config.name;
    result.model_type = config.model_type;
    result.fold = fold_idx;
    result.n_features = config.n_features;

    // Extract train/test
    vector<vector<float>> X_train, X_test;
    vector<int> y_train, y_test;
    vector<double> delta_train, delta_test;

    X_train.reserve(train_indices.size());
    y_train.reserve(train_indices.size());
    delta_train.reserve(train_indices.size());
    for (int idx : train_indices) {
        X_train.push_back(X[idx]);
        y_train.push_back(y[idx]);
        delta_train.push_back(next_bar_delta[idx]);
    }

    X_test.reserve(test_indices.size());
    y_test.reserve(test_indices.size());
    delta_test.reserve(test_indices.size());
    for (int idx : test_indices) {
        X_test.push_back(X[idx]);
        y_test.push_back(y[idx]);
        delta_test.push_back(next_bar_delta[idx]);
    }

    // Feature scoring on train only
    string score_method = config.feature_score_method.empty() ? "pearson" : config.feature_score_method;
    vector<FeatureScore> feature_scores = score_all_features(X_train, y_train, score_method);
    vector<int> top_features = rank_features_by_score(feature_scores, config.n_features);

    // Populate result metadata
    result.feature_score_method = score_method;
    double sum_pearson = 0.0, sum_spearman = 0.0, sum_mi = 0.0, sum_stab = 0.0, sum_turn = 0.0;
    for (int idx : top_features) {
        sum_pearson += abs(feature_scores[idx].pearson_ic);
        sum_spearman += abs(feature_scores[idx].spearman_ic);
        sum_mi += feature_scores[idx].mutual_info;
        sum_stab += abs(feature_scores[idx].stability);
        sum_turn += feature_scores[idx].turnover;
    }
    int n_top = top_features.size();
    result.avg_pearson_ic = sum_pearson / n_top;
    result.avg_spearman_ic = sum_spearman / n_top;
    result.avg_mi = sum_mi / n_top;
    result.avg_stability = sum_stab / n_top;
    result.avg_turnover = sum_turn / n_top;

    // Select features
    auto select_features = [&](const vector<vector<float>>& data) {
        vector<vector<float>> selected;
        selected.reserve(data.size());
        for (const auto& row : data) {
            vector<float> new_row;
            new_row.reserve(top_features.size());
            for (int idx : top_features) {
                new_row.push_back(row[idx]);
            }
            selected.push_back(new_row);
        }
        return selected;
    };

    X_train = select_features(X_train);
    X_test = select_features(X_test);

    // Train model
    vector<double> y_proba_train, y_proba_test;

    if (config.model_type == "logistic" || config.model_type == "conservative") {
        LogisticRegression model(config.n_features, config.learning_rate, config.l2_lambda, config.n_epochs);
        model.fit(X_train, y_train);
        y_proba_train = model.predict_proba(X_train);
        y_proba_test = model.predict_proba(X_test);
    } else if (config.model_type == "stump_ensemble") {
        StumpEnsemble model(config.n_stumps);
        model.fit(X_train, y_train);
        y_proba_train = model.predict_proba(X_train);
        y_proba_test = model.predict_proba(X_test);
    } else if (config.model_type == "ftrl") {
        FTRLLogistic model(config.n_features, config.ftrl_alpha, config.ftrl_beta, config.ftrl_l1, config.ftrl_l2);
        model.fit(X_train, y_train);
        y_proba_train = model.predict_proba(X_train);
        y_proba_test = model.predict_proba(X_test);
    } else if (config.model_type == "passive_aggressive") {
        PassiveAggressive model(config.n_features, config.pa_C, config.n_epochs);
        model.fit(X_train, y_train);
        y_proba_train = model.predict_proba(X_train);
        y_proba_test = model.predict_proba(X_test);
    } else if (config.model_type == "rank_ensemble") {
        RankEnsemble model;
        model.fit(X_train, y_train, feature_scores, top_features);
        y_proba_train = model.predict_proba(X_train);
        y_proba_test = model.predict_proba(X_test);
    }

    // Find best threshold on train using next-bar delta PnL
    string objective = config.objective.empty() ? "sharpe" : config.objective;
    result.objective = objective;

    auto best_th = find_best_threshold(
        y_proba_train, delta_train,
        config.thresholds, lot_size, commission_per_lot, gold_oz_per_lot, objective
    );

    result.threshold_long = best_th.first;
    result.threshold_short = best_th.second;

    print_progress("  [POST_THRESHOLD_START]");
    cout.flush();

    // Sanitize test probabilities before metrics
    print_progress("  [PROBA_SANITIZE_START]");
    cout.flush();

    bool proba_invalid = false;
    for (size_t i = 0; i < y_proba_test.size(); ++i) {
        if (!isfinite(y_proba_test[i])) {
            proba_invalid = true;
            break;
        }
    }

    if (proba_invalid) {
        print_progress("  [PROBA_SANITY_FAIL] NaN/Inf detected in probabilities, marking fold invalid", true);
        // Set all metrics to 0 and return early
        result.auc = 0.5;
        result.balanced_accuracy = 0.0;
        result.accuracy = 0.0;
        result.f1 = 0.0;
        result.long_rate = 0.0;
        result.short_rate = 0.0;
        result.flat_rate = 1.0;
        result.gross_pnl = 0.0;
        result.commission_paid = 0.0;
        result.net_pnl = 0.0;
        result.n_trades = 0.0;
        result.sharpe = 0.0;
        result.max_drawdown = 0.0;
        result.calmar = 0.0;
        result.utility = 0.0;
        print_progress("  [FOLD_RESULT_READY] (invalid probabilities)");
        cout.flush();
        return result;
    }

    // Clamp probabilities to avoid numerical issues
    for (size_t i = 0; i < y_proba_test.size(); ++i) {
        y_proba_test[i] = max(1e-6, min(1.0 - 1e-6, y_proba_test[i]));
    }
    print_progress("  [PROBA_SANITIZE_DONE]");
    cout.flush();

    // Apply trading thresholds → positions (-1/0/+1)
    print_progress("  [COMPUTE_POSITIONS_START]");
    cout.flush();

    vector<int> positions_test(y_test.size());
    #pragma omp parallel for if (HYDRA_OPENMP)
    for (size_t i = 0; i < y_test.size(); ++i) {
        if (y_proba_test[i] >= best_th.first) positions_test[i] = 1;
        else if (y_proba_test[i] <= best_th.second) positions_test[i] = -1;
        else positions_test[i] = 0;
    }
    print_progress("  [COMPUTE_POSITIONS_DONE]");
    cout.flush();

    // Binary classification predictions: proba >= 0.5 → class 1, else 0
    vector<int> y_pred_test(y_test.size());
    #pragma omp parallel for if (HYDRA_OPENMP)
    for (size_t i = 0; i < y_test.size(); ++i) {
        y_pred_test[i] = (y_proba_test[i] >= 0.5) ? 1 : 0;
    }

    // Classification metrics (use probabilities for AUC, binary pred for accuracy/F1)
    print_progress("  [COMPUTE_CLASSIFICATION_METRICS_START]");
    cout.flush();

    result.auc = compute_auc(y_test, y_proba_test);
    result.balanced_accuracy = compute_balanced_accuracy(y_test, y_pred_test);
    result.accuracy = compute_accuracy(y_test, y_pred_test);
    result.f1 = compute_f1(y_test, y_pred_test);

    print_progress("  [COMPUTE_CLASSIFICATION_METRICS_DONE]");
    cout.flush();

    int long_count = 0, short_count = 0, flat_count = 0;
    #pragma omp parallel for reduction(+:long_count,short_count,flat_count) if (HYDRA_OPENMP)
    for (size_t i = 0; i < positions_test.size(); ++i) {
        if (positions_test[i] == 1) long_count++;
        else if (positions_test[i] == -1) short_count++;
        else flat_count++;
    }

    result.long_rate = (double)long_count / positions_test.size();
    result.short_rate = (double)short_count / positions_test.size();
    result.flat_rate = (double)flat_count / positions_test.size();

    // Trading metrics — sequential next-bar PnL
    print_progress("  [COMPUTE_PNL_START]");
    cout.flush();

    auto pnl = calculate_pnl(positions_test, delta_test, lot_size, commission_per_lot, gold_oz_per_lot);

    print_progress("  [COMPUTE_PNL_DONE]");
    cout.flush();

    result.gross_pnl = pnl.gross_pnl;
    result.commission_paid = pnl.commission;
    result.net_pnl = pnl.net_pnl;
    result.n_trades = pnl.n_position_changes / 2.0;
    result.sharpe = pnl.sharpe;
    result.max_drawdown = pnl.max_drawdown;

    // Calmar and utility
    result.calmar = (pnl.max_drawdown > 0) ? (pnl.net_pnl / pnl.max_drawdown) : 0.0;
    result.utility = pnl.net_pnl
                   - 0.5 * pnl.max_drawdown
                   - 2.0 * pnl.commission
                   - 1000.0 * ((double)pnl.n_position_changes / delta_test.size());

    // Regime breakdown (placeholder for now)
    result.regime_aware = config.regime_aware;
    result.regime_breakdown_json = "{}";

    print_progress("  [FOLD_RESULT_READY]");
    cout.flush();

    return result;
}

// ============================================================================
// BROKER SIMULATOR (prop-firm account engine with Kelly + trailing + throttle)
// ============================================================================

struct TradeIntent {
    string config_name = "";
    int direction = 0; // +1 long, -1 short, 0 none
    double probability = 0.0;
    double confidence = 0.0;
    double requested_lot_size = 0.01;
    double final_lot_size = 0.01;
    double entry_price = 0.0;
    double stop_loss_price = 0.0;
    double take_profit_price = 0.0;
    double rr = 2.0;
    double risk_dollars = 0.0;
    double risk_pct = 0.0;
    double kelly_raw = 0.0;
    double kelly_risk_pct = 0.0;
    double drawdown_risk_multiplier = 1.0;
    int max_holding_bars = 0;
    bool trailing_stop_enabled = false;
    bool kelly_fallback_used = false;
    string reject_reason = "";
};

struct BrokerPosition {
    int id = 0;
    string config_name = "";
    int direction = 0;
    double entry_price = 0.0;
    double current_price = 0.0;
    double lot_size = 0.0;
    double gold_oz_per_lot = 100.0;
    double notional = 0.0;
    double required_margin = 0.0;
    double stop_loss_price = 0.0;
    double initial_stop_loss_price = 0.0;
    double take_profit_price = 0.0;
    bool trailing_stop_enabled = false;
    double trailing_distance = 0.0;
    double trailing_stop_price = 0.0;
    int entry_bar = 0;
    int exit_bar = -1;
    bool is_open = true;
    double unrealized_pnl = 0.0;
    double realized_pnl = 0.0;
    string exit_reason = "";
    double confidence = 0.0;
    double rr = 0.0;
    double kelly_raw = 0.0;
    double kelly_risk_pct = 0.0;
    double final_risk_pct = 0.0;
    double risk_dollars = 0.0;
    double drawdown_risk_multiplier = 1.0;
    bool kelly_fallback_used = false;
    double signal_probability = 0.0;
    int regime_at_entry = 0;
    bool was_counter_regime = false;
};

struct AccountState {
    double starting_balance = 0.0;
    double balance = 0.0;
    double equity = 0.0;
    double realized_pnl = 0.0;
    double unrealized_pnl = 0.0;
    double used_margin = 0.0;
    double free_margin = 0.0;
    double leverage = 50.0;
    double max_loss_pct = 0.06;
    double stopout_equity = 0.0;
    double peak_equity = 0.0;
    double max_drawdown_dollars = 0.0;
    double max_drawdown_pct = 0.0;
    bool is_failed = false;
    string fail_reason = "";
    double max_used_margin = 0.0;
    double min_free_margin = 0.0;
};

struct TradeRecord {
    string config = "";
    int trade_id = 0;
    int entry_bar = 0;
    int exit_bar = 0;
    int direction = 0;
    double lot_size = 0.0;
    double entry_price = 0.0;
    double exit_price = 0.0;
    double stop_loss_price = 0.0;
    double take_profit_price = 0.0;
    double trailing_stop_price = 0.0;
    double gross_pnl = 0.0;
    double commission = 0.0;
    double net_pnl = 0.0;
    double required_margin = 0.0;
    double balance_after = 0.0;
    double equity_after = 0.0;
    int holding_bars = 0;
    string exit_reason = "";
    double confidence = 0.0;
    double rr = 0.0;
    double kelly_raw = 0.0;
    double kelly_risk_pct = 0.0;
    double final_risk_pct = 0.0;
    double lot_by_risk = 0.0;
    double lot_by_margin = 0.0;
    double final_lot_size = 0.0;
    double risk_dollars = 0.0;
    double drawdown_risk_multiplier = 1.0;
    bool kelly_fallback_used = false;
    double signal_probability = 0.0;
    int regime_at_entry = 0;
    bool was_counter_regime = false;
};

struct BrokerEquityRow {
    string config = "";
    int bar_index = 0;
    double close_price = 0.0;
    double balance = 0.0;
    double equity = 0.0;
    double unrealized_pnl = 0.0;
    double realized_pnl = 0.0;
    double used_margin = 0.0;
    double free_margin = 0.0;
    int open_positions = 0;
    double drawdown_dollars = 0.0;
    double drawdown_pct = 0.0;
    bool account_failed = false;
    string fail_reason = "";
};

struct BrokerStats {
    int total_trades = 0;
    int wins = 0;
    int losses = 0;
    double win_rate = 0.0;
    double avg_win = 0.0;
    double avg_loss = 0.0;
    double profit_factor = 0.0;
    double avg_holding_bars = 0.0;
    int tp_hits = 0;
    int sl_hits = 0;
    int trailing_stop_hits = 0;
    int time_stop_hits = 0;
    int orders_attempted = 0;
    int orders_opened = 0;
    int rejected_orders = 0;
    int margin_rejections = 0;
    int no_sl_rejections = 0;
    int kelly_negative_rejections = 0;
    int kelly_invalid_sample_rejections = 0;
    int kelly_too_small_rejections = 0;
    int drawdown_throttle_rejections = 0;
    int max_trades_rejections = 0;
    int max_open_pos_rejections = 0;
    double avg_rr = 0.0;
    double avg_confidence = 0.0;
    double avg_kelly_risk_pct = 0.0;
    double avg_lot_size = 0.0;
    double max_lot_size_used = 0.0;
    double min_lot_size_used = 1e18;
    int drawdown_throttle_events = 0;
    int kelly_fallback_trades = 0;
    int long_trades = 0;
    int short_trades = 0;
    int long_wins = 0;
    int short_wins = 0;
    double long_net_pnl = 0.0;
    double short_net_pnl = 0.0;
    int reverse_exits = 0;
    int ignored_opposite_signals = 0;
    int blocked_long_signals = 0;
    int blocked_short_signals = 0;
    int blocked_counter_regime_signals = 0;
};

struct KellyEstimate {
    double win_rate = 0.0;
    double avg_win = 0.0;
    double avg_loss = 0.0;
    double payoff_ratio = 0.0;
    double kelly_raw = 0.0;
    int sample_count = 0;
    bool valid = false;
};

struct ProbaDiagnostics {
    double proba_min = 1.0;
    double proba_max = 0.0;
    double proba_mean = 0.0;
    double proba_std = 0.0;
    double proba_p01 = 0.0;
    double proba_p05 = 0.0;
    double proba_p50 = 0.0;
    double proba_p95 = 0.0;
    double proba_p99 = 0.0;
    int count_long = 0;
    int count_short = 0;
    int count_flat = 0;
    int saturated_low = 0;
    int saturated_high = 0;
    bool constant_proba = false;
    string signal_verdict = "PASS_SIGNAL_SANITY";
    double confidence_cap = 1.0;
};

ProbaDiagnostics compute_proba_diagnostics(const vector<double>& proba, int n,
    double th_long, double th_short, double auc) {
    ProbaDiagnostics d;
    if (n == 0) return d;

    vector<double> sorted_p(proba.begin(), proba.begin() + n);
    double sum = 0.0, sum_sq = 0.0;
    for (int i = 0; i < n; ++i) {
        double p = proba[i];
        d.proba_min = min(d.proba_min, p);
        d.proba_max = max(d.proba_max, p);
        sum += p;
        sum_sq += p * p;
        if (p >= th_long) d.count_long++;
        else if (p <= th_short) d.count_short++;
        else d.count_flat++;
        if (p <= 0.001) d.saturated_low++;
        if (p >= 0.999) d.saturated_high++;
    }
    d.proba_mean = sum / n;
    double variance = (sum_sq / n) - (d.proba_mean * d.proba_mean);
    d.proba_std = (variance > 0) ? sqrt(variance) : 0.0;
    d.constant_proba = (d.proba_std < 1e-9);

    sort(sorted_p.begin(), sorted_p.end());
    auto percentile = [&](double pct) {
        int idx = (int)(pct * (n - 1));
        idx = max(0, min(n - 1, idx));
        return sorted_p[idx];
    };
    d.proba_p01 = percentile(0.01);
    d.proba_p05 = percentile(0.05);
    d.proba_p50 = percentile(0.50);
    d.proba_p95 = percentile(0.95);
    d.proba_p99 = percentile(0.99);

    double saturation_rate = (double)(d.saturated_low + d.saturated_high) / n;

    if (REJECT_CONSTANT_PROBA && d.constant_proba) {
        d.signal_verdict = "FAILED_CONSTANT_PROBA";
    } else if (saturation_rate > MAX_SATURATION_RATE) {
        d.signal_verdict = "FAILED_PROBA_SATURATION";
    } else if (d.proba_std < MIN_PROBA_STD) {
        d.signal_verdict = "FAILED_LOW_PROBA_STD";
    }

    // Confidence cap based on model quality
    if (auc <= 0.505) d.confidence_cap = 0.05;
    if (d.proba_std < MIN_PROBA_STD) d.confidence_cap = 0.0;
    if (saturation_rate > MAX_SATURATION_RATE) d.confidence_cap = 0.0;

    return d;
}

struct BaselineResult {
    string name = "";
    double return_pct = 0.0;
    int total_trades = 0;
    double profit_factor = 0.0;
    double max_drawdown_pct = 0.0;
};

class BrokerSimulator {
public:
    AccountState account;
    vector<BrokerPosition> open_positions;
    vector<TradeRecord> trade_ledger;
    vector<BrokerEquityRow> equity_curve;
    BrokerStats stats;
    double commission_per_lot;
    double gold_oz_per_lot;
    int next_trade_id = 1;
    KellyEstimate kelly_est;

    BrokerSimulator(double starting_balance, double leverage, double max_loss_pct,
                    double comm_per_lot, double oz_per_lot) {
        account.starting_balance = starting_balance;
        account.balance = starting_balance;
        account.equity = starting_balance;
        account.free_margin = starting_balance;
        account.leverage = leverage;
        account.max_loss_pct = max_loss_pct;
        account.stopout_equity = starting_balance * (1.0 - max_loss_pct);
        account.peak_equity = starting_balance;
        account.min_free_margin = starting_balance;
        commission_per_lot = comm_per_lot;
        gold_oz_per_lot = oz_per_lot;
    }

    double compute_notional(double price, double lot_size) {
        return price * gold_oz_per_lot * lot_size;
    }

    double compute_margin(double notional) {
        return notional / account.leverage;
    }

    double get_drawdown_risk_multiplier() {
        if (!DRAWDOWN_RISK_THROTTLE) return 1.0;
        double current_dd_pct = (account.peak_equity - account.equity) / account.starting_balance;
        if (current_dd_pct < 0.02) return 1.0;
        if (current_dd_pct < 0.04) return 0.5;
        if (current_dd_pct < 0.05) return 0.25;
        return 0.0; // stop opening new trades
    }

    void update_account_state() {
        account.unrealized_pnl = 0.0;
        account.used_margin = 0.0;
        for (auto& pos : open_positions) {
            double pnl = pos.direction * (pos.current_price - pos.entry_price) * gold_oz_per_lot * pos.lot_size;
            pos.unrealized_pnl = pnl;
            account.unrealized_pnl += pnl;
            account.used_margin += pos.required_margin;
        }
        account.equity = account.balance + account.unrealized_pnl;
        account.free_margin = account.equity - account.used_margin;
        account.max_used_margin = max(account.max_used_margin, account.used_margin);
        account.min_free_margin = min(account.min_free_margin, account.free_margin);
        account.peak_equity = max(account.peak_equity, account.equity);
        double dd = account.peak_equity - account.equity;
        account.max_drawdown_dollars = max(account.max_drawdown_dollars, dd);
        account.max_drawdown_pct = account.max_drawdown_dollars / account.starting_balance;
    }

    bool check_risk_stop() {
        if (account.equity <= account.stopout_equity) {
            account.is_failed = true;
            account.fail_reason = "RISK_STOP_OUT";
            return true;
        }
        if (account.used_margin > 0 && account.equity <= account.used_margin * MAINTENANCE_MARGIN_RATIO) {
            account.is_failed = true;
            account.fail_reason = "MARGIN_CALL";
            return true;
        }
        if (!isfinite(account.equity) || !isfinite(account.used_margin)) {
            account.is_failed = true;
            account.fail_reason = "INVALID_ACCOUNT_STATE";
            return true;
        }
        return false;
    }

    void liquidate_all(int bar, double price) {
        for (auto& pos : open_positions) {
            close_position(pos, bar, price, account.fail_reason);
        }
        open_positions.clear();
    }

    void close_position(BrokerPosition& pos, int bar, double exit_price, const string& reason) {
        pos.is_open = false;
        pos.exit_bar = bar;
        pos.current_price = exit_price;
        double gross = pos.direction * (exit_price - pos.entry_price) * gold_oz_per_lot * pos.lot_size;
        double comm = pos.lot_size * commission_per_lot;
        double net = gross - comm;
        pos.realized_pnl = net;
        pos.exit_reason = reason;

        account.balance += net;
        account.realized_pnl += net;

        TradeRecord rec;
        rec.config = pos.config_name;
        rec.trade_id = pos.id;
        rec.entry_bar = pos.entry_bar;
        rec.exit_bar = bar;
        rec.direction = pos.direction;
        rec.lot_size = pos.lot_size;
        rec.entry_price = pos.entry_price;
        rec.exit_price = exit_price;
        rec.stop_loss_price = pos.stop_loss_price;
        rec.take_profit_price = pos.take_profit_price;
        rec.trailing_stop_price = pos.trailing_stop_price;
        rec.gross_pnl = gross;
        rec.commission = comm;
        rec.net_pnl = net;
        rec.required_margin = pos.required_margin;
        rec.balance_after = account.balance;
        rec.equity_after = account.equity;
        rec.holding_bars = bar - pos.entry_bar;
        rec.exit_reason = reason;
        rec.confidence = pos.confidence;
        rec.rr = pos.rr;
        rec.kelly_raw = pos.kelly_raw;
        rec.kelly_risk_pct = pos.kelly_risk_pct;
        rec.final_risk_pct = pos.final_risk_pct;
        rec.lot_by_risk = 0.0;
        rec.lot_by_margin = 0.0;
        rec.final_lot_size = pos.lot_size;
        rec.risk_dollars = pos.risk_dollars;
        rec.drawdown_risk_multiplier = pos.drawdown_risk_multiplier;
        rec.kelly_fallback_used = pos.kelly_fallback_used;
        rec.signal_probability = pos.signal_probability;
        rec.regime_at_entry = pos.regime_at_entry;
        rec.was_counter_regime = pos.was_counter_regime;
        trade_ledger.push_back(rec);

        // Update stats
        stats.total_trades++;
        if (net > 0) { stats.wins++; stats.avg_win += net; }
        else { stats.losses++; stats.avg_loss += net; }

        if (pos.direction == 1) {
            stats.long_trades++;
            stats.long_net_pnl += net;
            if (net > 0) stats.long_wins++;
        } else if (pos.direction == -1) {
            stats.short_trades++;
            stats.short_net_pnl += net;
            if (net > 0) stats.short_wins++;
        }

        if (reason == "REVERSE_EXIT") stats.reverse_exits++;

        if (reason == "TAKE_PROFIT") stats.tp_hits++;
        else if (reason == "STOP_LOSS") stats.sl_hits++;
        else if (reason == "TRAILING_STOP") stats.trailing_stop_hits++;
        else if (reason == "TIME_STOP") stats.time_stop_hits++;

        stats.avg_rr += pos.rr;
        stats.avg_confidence += pos.confidence;
        stats.avg_kelly_risk_pct += pos.kelly_risk_pct;
        stats.avg_lot_size += pos.lot_size;
        stats.max_lot_size_used = max(stats.max_lot_size_used, pos.lot_size);
        stats.min_lot_size_used = min(stats.min_lot_size_used, pos.lot_size);
    }

    bool try_open_position(const TradeIntent& intent, int bar, double entry_price) {
        if (account.is_failed) return false;
        if (intent.direction == 0) return false;
        if ((int)open_positions.size() >= MAX_OPEN_POSITIONS) return false;

        // Validate bracket orders
        if (REQUIRE_BRACKET_ORDERS) {
            if (intent.stop_loss_price <= 0 || intent.take_profit_price <= 0) {
                stats.rejected_orders++;
                stats.no_sl_rejections++;
                return false;
            }
            if (intent.direction == 1 && intent.stop_loss_price >= entry_price) {
                stats.rejected_orders++;
                return false;
            }
            if (intent.direction == -1 && intent.stop_loss_price <= entry_price) {
                stats.rejected_orders++;
                return false;
            }
            if (intent.direction == 1 && intent.take_profit_price <= entry_price) {
                stats.rejected_orders++;
                return false;
            }
            if (intent.direction == -1 && intent.take_profit_price >= entry_price) {
                stats.rejected_orders++;
                return false;
            }
        }

        double notional = compute_notional(entry_price, intent.final_lot_size);
        double req_margin = compute_margin(notional);

        if (req_margin > account.free_margin) {
            stats.rejected_orders++;
            stats.margin_rejections++;
            return false;
        }

        BrokerPosition pos;
        pos.id = next_trade_id++;
        pos.config_name = intent.config_name;
        pos.direction = intent.direction;
        pos.entry_price = entry_price;
        pos.current_price = entry_price;
        pos.lot_size = intent.final_lot_size;
        pos.gold_oz_per_lot = gold_oz_per_lot;
        pos.notional = notional;
        pos.required_margin = req_margin;
        pos.stop_loss_price = intent.stop_loss_price;
        pos.initial_stop_loss_price = intent.stop_loss_price;
        pos.take_profit_price = intent.take_profit_price;
        pos.trailing_stop_enabled = intent.trailing_stop_enabled;
        pos.entry_bar = bar;
        pos.is_open = true;
        pos.confidence = intent.confidence;
        pos.rr = intent.rr;
        pos.kelly_raw = intent.kelly_raw;
        pos.kelly_risk_pct = intent.kelly_risk_pct;
        pos.final_risk_pct = intent.risk_pct;
        pos.risk_dollars = intent.risk_dollars;
        pos.drawdown_risk_multiplier = intent.drawdown_risk_multiplier;
        pos.kelly_fallback_used = intent.kelly_fallback_used;
        pos.signal_probability = intent.probability;
        pos.regime_at_entry = 0; // set by caller
        pos.was_counter_regime = false; // set by caller

        // R-based trailing: compute trailing_distance from R
        double R = abs(entry_price - intent.stop_loss_price);
        pos.trailing_distance = TRAIL_DISTANCE_R * R;
        pos.trailing_stop_price = intent.stop_loss_price; // start at initial SL

        open_positions.push_back(pos);
        stats.orders_opened++;
        update_account_state();
        return true;
    }

    void tick(int bar, double current_close) {
        if (account.is_failed) return;

        vector<int> to_close;
        for (size_t i = 0; i < open_positions.size(); ++i) {
            auto& pos = open_positions[i];
            pos.current_price = current_close;

            // Check SL first (conservative: SL before TP if both hit)
            if (pos.direction == 1 && current_close <= pos.stop_loss_price) {
                string reason = (pos.stop_loss_price > pos.initial_stop_loss_price) ? "TRAILING_STOP" : "STOP_LOSS";
                close_position(pos, bar, pos.stop_loss_price, reason);
                to_close.push_back(i);
                continue;
            }
            if (pos.direction == -1 && current_close >= pos.stop_loss_price) {
                string reason = (pos.stop_loss_price < pos.initial_stop_loss_price) ? "TRAILING_STOP" : "STOP_LOSS";
                close_position(pos, bar, pos.stop_loss_price, reason);
                to_close.push_back(i);
                continue;
            }

            // Check TP
            if (pos.direction == 1 && current_close >= pos.take_profit_price) {
                close_position(pos, bar, pos.take_profit_price, "TAKE_PROFIT");
                to_close.push_back(i);
                continue;
            }
            if (pos.direction == -1 && current_close <= pos.take_profit_price) {
                close_position(pos, bar, pos.take_profit_price, "TAKE_PROFIT");
                to_close.push_back(i);
                continue;
            }

            // R-based breakeven and trailing stop
            if (pos.trailing_stop_enabled) {
                double R = abs(pos.entry_price - pos.initial_stop_loss_price);
                if (R > 0) {
                    if (pos.direction == 1) {
                        // Move SL to breakeven
                        if (current_close >= pos.entry_price + MOVE_SL_TO_BREAKEVEN_AT_R * R) {
                            pos.stop_loss_price = max(pos.stop_loss_price, pos.entry_price);
                        }
                        // Activate trailing
                        if (current_close >= pos.entry_price + TRAIL_ACTIVATE_R * R) {
                            double new_trail = current_close - TRAIL_DISTANCE_R * R;
                            pos.stop_loss_price = max(pos.stop_loss_price, new_trail);
                        }
                    } else {
                        // Move SL to breakeven (short)
                        if (current_close <= pos.entry_price - MOVE_SL_TO_BREAKEVEN_AT_R * R) {
                            pos.stop_loss_price = min(pos.stop_loss_price, pos.entry_price);
                        }
                        // Activate trailing (short)
                        if (current_close <= pos.entry_price - TRAIL_ACTIVATE_R * R) {
                            double new_trail = current_close + TRAIL_DISTANCE_R * R;
                            pos.stop_loss_price = min(pos.stop_loss_price, new_trail);
                        }
                    }
                }
            }

            // Time stop
            if (MAX_HOLDING_BARS > 0 && (bar - pos.entry_bar) >= MAX_HOLDING_BARS) {
                close_position(pos, bar, current_close, "TIME_STOP");
                to_close.push_back(i);
                continue;
            }
        }

        // Remove closed positions (reverse order)
        sort(to_close.rbegin(), to_close.rend());
        for (int idx : to_close) {
            open_positions.erase(open_positions.begin() + idx);
        }

        update_account_state();

        // Check risk stop
        if (check_risk_stop()) {
            liquidate_all(bar, current_close);
        }
    }

    void end_of_test(int bar, double price) {
        for (auto& pos : open_positions) {
            close_position(pos, bar, price, "END_OF_TEST");
        }
        open_positions.clear();
        update_account_state();
    }

    void finalize_stats() {
        if (stats.wins > 0) stats.avg_win /= stats.wins;
        if (stats.losses > 0) stats.avg_loss /= stats.losses;
        if (stats.total_trades > 0) {
            stats.win_rate = (double)stats.wins / stats.total_trades;
            double total_holding = 0;
            for (auto& t : trade_ledger) total_holding += t.holding_bars;
            stats.avg_holding_bars = total_holding / stats.total_trades;
            stats.avg_rr /= stats.total_trades;
            stats.avg_confidence /= stats.total_trades;
            stats.avg_kelly_risk_pct /= stats.total_trades;
            stats.avg_lot_size /= stats.total_trades;
        }
        double gross_wins = 0, gross_losses = 0;
        for (auto& t : trade_ledger) {
            if (t.net_pnl > 0) gross_wins += t.net_pnl;
            else gross_losses += abs(t.net_pnl);
        }
        stats.profit_factor = (gross_losses > 0) ? (gross_wins / gross_losses) : 0.0;
        if (stats.min_lot_size_used > 1e17) stats.min_lot_size_used = 0.0;
    }

    BrokerEquityRow make_equity_row(const string& cfg, int bar, double close_price) {
        BrokerEquityRow row;
        row.config = cfg;
        row.bar_index = bar;
        row.close_price = close_price;
        row.balance = account.balance;
        row.equity = account.equity;
        row.unrealized_pnl = account.unrealized_pnl;
        row.realized_pnl = account.realized_pnl;
        row.used_margin = account.used_margin;
        row.free_margin = account.free_margin;
        row.open_positions = (int)open_positions.size();
        row.drawdown_dollars = account.peak_equity - account.equity;
        row.drawdown_pct = row.drawdown_dollars / account.starting_balance;
        row.account_failed = account.is_failed;
        row.fail_reason = account.fail_reason;
        return row;
    }

    void compute_kelly_from_trades(int lookback) {
        kelly_est = KellyEstimate{};
        int n = (int)trade_ledger.size();
        int start = max(0, n - lookback);
        int count = n - start;
        if (count < KELLY_MIN_SAMPLES) {
            kelly_est.valid = false;
            kelly_est.sample_count = count;
            return;
        }

        int w = 0;
        double sum_win = 0.0, sum_loss = 0.0;
        int loss_count = 0;
        for (int i = start; i < n; ++i) {
            if (trade_ledger[i].net_pnl > 0) { w++; sum_win += trade_ledger[i].net_pnl; }
            else { loss_count++; sum_loss += trade_ledger[i].net_pnl; }
        }

        kelly_est.sample_count = count;
        kelly_est.win_rate = (double)w / count;
        kelly_est.avg_win = (w > 0) ? (sum_win / w) : 0.0;
        kelly_est.avg_loss = (loss_count > 0) ? (sum_loss / loss_count) : 0.0;

        if (kelly_est.avg_loss >= 0.0) { kelly_est.kelly_raw = 0.0; kelly_est.valid = false; return; }
        kelly_est.payoff_ratio = kelly_est.avg_win / abs(kelly_est.avg_loss);
        if (kelly_est.payoff_ratio <= 0.0) { kelly_est.kelly_raw = 0.0; kelly_est.valid = false; return; }

        kelly_est.kelly_raw = kelly_est.win_rate - ((1.0 - kelly_est.win_rate) / kelly_est.payoff_ratio);
        kelly_est.kelly_raw = max(0.0, min(1.0, kelly_est.kelly_raw));
        kelly_est.valid = true;
    }
};

BaselineResult run_baseline_broker(const string& baseline_name, const vector<int>& signals,
    const vector<double>& oos_closes, double lot_size, double commission_per_lot,
    double gold_oz_per_lot, bool trailing_enabled) {
    int oos_n = (int)oos_closes.size();
    BrokerSimulator broker(STARTING_BALANCE, LEVERAGE, MAX_LOSS_PCT, commission_per_lot, gold_oz_per_lot);

    for (int i = 0; i < oos_n; ++i) {
        double price = oos_closes[i];
        broker.tick(i, price);
        if (broker.account.is_failed) break;

        do {
            if ((int)broker.open_positions.size() >= MAX_OPEN_POSITIONS) break;
            int sig = signals[i];
            if (sig == 0) break;

            double confidence = 0.5;
            double rr = DEFAULT_RR;
            if (CONFIDENCE_RR) {
                rr = MIN_RR + confidence * (MAX_RR - MIN_RR);
                rr = max(MIN_RR, min(MAX_RR, rr));
            }

            double risk_pct = RISK_PER_TRADE_PCT;
            double dd_mult = broker.get_drawdown_risk_multiplier();
            if (dd_mult <= 0.0) break;
            risk_pct *= dd_mult;

            double risk_dollars = broker.account.equity * risk_pct;
            double dollars_per_point = lot_size * gold_oz_per_lot;
            double stop_distance = risk_dollars / dollars_per_point;
            if (stop_distance < 0.01) break;
            double tp_distance = stop_distance * rr;
            if (tp_distance < 0.01) break;

            double lot_by_risk = risk_dollars / (stop_distance * gold_oz_per_lot);
            double lot_by_margin = broker.account.free_margin * broker.account.leverage /
                                   (price * gold_oz_per_lot);
            double final_lot = min({lot_size, lot_by_risk, lot_by_margin, MAX_LOT_SIZE});
            if (AUTO_SIZE_BY_RISK) {
                final_lot = min({lot_by_risk, lot_by_margin, MAX_LOT_SIZE});
            }
            final_lot = max(final_lot, MIN_LOT_SIZE);
            if (final_lot < MIN_LOT_SIZE) break;

            TradeIntent intent;
            intent.config_name = baseline_name;
            intent.direction = sig;
            intent.confidence = confidence;
            intent.final_lot_size = final_lot;
            intent.entry_price = price;
            intent.rr = rr;
            intent.risk_dollars = risk_dollars;
            intent.risk_pct = risk_pct;
            intent.drawdown_risk_multiplier = dd_mult;
            intent.max_holding_bars = MAX_HOLDING_BARS;
            intent.trailing_stop_enabled = trailing_enabled;

            if (sig == 1) {
                intent.stop_loss_price = price - stop_distance;
                intent.take_profit_price = price + tp_distance;
            } else {
                intent.stop_loss_price = price + stop_distance;
                intent.take_profit_price = price - tp_distance;
            }

            broker.try_open_position(intent, i, price);
        } while (false);
    }

    if (!broker.account.is_failed && !broker.open_positions.empty()) {
        broker.end_of_test(oos_n - 1, oos_closes.back());
    }
    broker.finalize_stats();

    BaselineResult res;
    res.name = baseline_name;
    res.return_pct = (broker.account.balance - broker.account.starting_balance) / broker.account.starting_balance;
    res.total_trades = broker.stats.total_trades;
    res.profit_factor = broker.stats.profit_factor;
    res.max_drawdown_pct = broker.account.max_drawdown_pct;
    return res;
}

// Compute rolling volatility for SL/TP
double compute_rolling_volatility(const vector<double>& closes, int end_idx, int window) {
    if (end_idx < window) return 0.0;
    double sum = 0.0;
    int count = 0;
    for (int i = end_idx - window + 1; i <= end_idx; ++i) {
        if (i > 0) {
            sum += abs(closes[i] - closes[i-1]);
            count++;
        }
    }
    return (count > 0) ? (sum / count) : 0.0;
}

// Broker self-tests (14 tests)
struct BrokerSelfTestResult {
    bool pass;
    string msg;
};

BrokerSelfTestResult run_broker_self_tests() {
    double oz = 100.0;
    double comm = 5.0;

    // Test 1: RR confidence
    {
        double p = 0.5;
        double conf = abs(p - 0.5) * 2.0;
        double rr = MIN_RR + conf * (MAX_RR - MIN_RR);
        if (abs(rr - MIN_RR) > 1e-9) return {false, "RR confidence test FAIL: p=0.5 should give min_rr"};
        p = 1.0;
        conf = abs(p - 0.5) * 2.0;
        rr = MIN_RR + conf * (MAX_RR - MIN_RR);
        if (abs(rr - MAX_RR) > 1e-9) return {false, "RR confidence test FAIL: p=1.0 should give max_rr"};
    }

    // Test 2: Risk SL
    {
        double equity = 10000.0;
        double risk_pct = 0.0025;
        double lot = 0.01;
        double risk_dollars = equity * risk_pct; // 25
        double dollars_per_point = lot * oz; // 1
        double stop_distance = risk_dollars / dollars_per_point; // 25
        if (abs(risk_dollars - 25.0) > 1e-6) return {false, "Risk SL test FAIL: risk_dollars=" + to_string(risk_dollars)};
        if (abs(stop_distance - 25.0) > 1e-6) return {false, "Risk SL test FAIL: stop_distance=" + to_string(stop_distance)};
    }

    // Test 3: Long bracket
    {
        double entry = 2000.0, sl = 1975.0, rr = 2.0;
        double tp = entry + (entry - sl) * rr; // 2050
        if (abs(tp - 2050.0) > 1e-6) return {false, "Long bracket test FAIL: tp=" + to_string(tp)};
    }

    // Test 4: Long TP hit
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 0.01;
        intent.stop_loss_price = 1990;
        intent.take_profit_price = 2010;
        intent.config_name = "test";
        broker.try_open_position(intent, 0, 2000.0);
        broker.tick(1, 2005.0);
        if (broker.open_positions.empty()) return {false, "Long TP test FAIL: closed too early at 2005"};
        broker.tick(2, 2011.0);
        if (!broker.open_positions.empty()) return {false, "Long TP test FAIL: should have hit TP at 2011"};
        if (broker.trade_ledger.back().exit_reason != "TAKE_PROFIT")
            return {false, "Long TP test FAIL: reason=" + broker.trade_ledger.back().exit_reason};
    }

    // Test 5: Long SL hit
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 0.01;
        intent.stop_loss_price = 1990;
        intent.take_profit_price = 2010;
        intent.config_name = "test";
        broker.try_open_position(intent, 0, 2000.0);
        broker.tick(1, 1995.0);
        if (broker.open_positions.empty()) return {false, "Long SL test FAIL: closed too early at 1995"};
        broker.tick(2, 1989.0);
        if (!broker.open_positions.empty()) return {false, "Long SL test FAIL: should have hit SL at 1989"};
        if (broker.trade_ledger.back().exit_reason != "STOP_LOSS")
            return {false, "Long SL test FAIL: reason=" + broker.trade_ledger.back().exit_reason};
    }

    // Test 6: Breakeven
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 0.01;
        intent.stop_loss_price = 1975;
        intent.take_profit_price = 2100;
        intent.trailing_stop_enabled = true;
        intent.config_name = "test";
        broker.try_open_position(intent, 0, 2000.0);
        // R = 25. breakeven at entry + 1.0*R = 2025
        broker.tick(1, 2025.0);
        if (broker.open_positions.empty()) return {false, "Breakeven test FAIL: position closed"};
        if (broker.open_positions[0].stop_loss_price < 2000.0)
            return {false, "Breakeven test FAIL: SL not moved to entry. SL=" + to_string(broker.open_positions[0].stop_loss_price)};
    }

    // Test 7: Trailing stop
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 0.01;
        intent.stop_loss_price = 1975;
        intent.take_profit_price = 2100;
        intent.trailing_stop_enabled = true;
        intent.config_name = "test";
        broker.try_open_position(intent, 0, 2000.0);
        // R = 25, trail_activate_r=1.0 → activate at 2025, trail_distance_r=0.5 → 12.5 pts trail
        broker.tick(1, 2025.0); // activate, trail = 2025 - 12.5 = 2012.5, SL = max(2000, 2012.5) = 2012.5
        broker.tick(2, 2030.0); // trail = 2030 - 12.5 = 2017.5
        if (broker.open_positions.empty()) return {false, "Trailing test FAIL: closed too early"};
        broker.tick(3, 2010.0); // below 2017.5 → trailing stop
        if (!broker.open_positions.empty()) return {false, "Trailing test FAIL: should have closed by trailing stop"};
        string reason = broker.trade_ledger.back().exit_reason;
        if (reason != "TRAILING_STOP")
            return {false, "Trailing test FAIL: reason=" + reason};
    }

    // Test 8: Account stopout
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 1.0;
        intent.stop_loss_price = 1900;
        intent.take_profit_price = 2100;
        intent.config_name = "test";
        broker.try_open_position(intent, 0, 2000.0);
        // unrealized = (1993-2000)*100*1 = -700, equity = 9300 < 9400
        broker.tick(1, 1993.0);
        if (!broker.account.is_failed) return {false, "Stopout test FAIL: should have triggered"};
        if (broker.account.fail_reason != "RISK_STOP_OUT")
            return {false, "Stopout test FAIL: reason=" + broker.account.fail_reason};
    }

    // Test 9: Margin validation
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        TradeIntent intent;
        intent.direction = 1;
        intent.final_lot_size = 1.0;
        intent.stop_loss_price = 1990;
        intent.take_profit_price = 2010;
        intent.config_name = "test";
        bool ok = broker.try_open_position(intent, 0, 2000.0);
        if (!ok) return {false, "Margin test FAIL: should accept 1 lot (margin=4000, free=10000)"};

        TradeIntent intent2;
        intent2.direction = 1;
        intent2.final_lot_size = 5.0;
        intent2.stop_loss_price = 1990;
        intent2.take_profit_price = 2010;
        intent2.config_name = "test";
        bool ok2 = broker.try_open_position(intent2, 1, 2000.0);
        if (ok2) return {false, "Margin test FAIL: should reject 5 lots (margin=20000 > free=6000)"};
    }

    // Test 10: Positive Kelly
    {
        double win_rate = 0.55;
        double payoff_ratio = 2.0;
        double kelly = win_rate - ((1.0 - win_rate) / payoff_ratio); // 0.55 - 0.225 = 0.325
        double kelly_risk = kelly * 0.25; // 0.08125
        double final_risk = min(kelly_risk, MAX_RISK_PER_TRADE_PCT); // capped to 0.0025
        if (abs(kelly - 0.325) > 1e-6) return {false, "Kelly+ test FAIL: kelly=" + to_string(kelly)};
        if (final_risk > MAX_RISK_PER_TRADE_PCT + 1e-9)
            return {false, "Kelly+ test FAIL: final_risk not capped"};
    }

    // Test 11: Negative Kelly
    {
        double win_rate = 0.40;
        double payoff_ratio = 1.0;
        double kelly = win_rate - ((1.0 - win_rate) / payoff_ratio); // -0.20
        if (kelly >= 0) return {false, "Kelly- test FAIL: should be negative"};
    }

    // Test 12: Drawdown throttle
    {
        bool saved = DRAWDOWN_RISK_THROTTLE;
        DRAWDOWN_RISK_THROTTLE = true;
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        broker.account.peak_equity = 10000;
        broker.account.equity = 9550; // DD = 450/10000 = 4.5%
        double mult = broker.get_drawdown_risk_multiplier();
        DRAWDOWN_RISK_THROTTLE = saved;
        if (abs(mult - 0.25) > 1e-9) return {false, "Throttle test FAIL: DD=4.5% mult should be 0.25, got " + to_string(mult)};
    }

    // Test 13: Margin cap (Kelly wants more than margin allows)
    {
        BrokerSimulator broker(10000, 50, 0.06, comm, oz);
        // lot_by_margin = free_margin * leverage / (price * oz) = 10000*50/(2000*100) = 2.5
        double lot_by_margin = 10000.0 * 50.0 / (2000.0 * 100.0);
        double kelly_wants = 5.0;
        double final_lot = min(kelly_wants, lot_by_margin);
        if (final_lot > lot_by_margin + 1e-9)
            return {false, "Margin cap test FAIL: final_lot exceeds margin capacity"};
    }

    // Test 14: Compound sizing
    {
        double eq1 = 10000, eq2 = 12000;
        double rpct = 0.0025;
        double r1 = eq1 * rpct; // 25
        double r2 = eq2 * rpct; // 30
        if (abs(r1 - 25.0) > 1e-6 || abs(r2 - 30.0) > 1e-6)
            return {false, "Compound test FAIL: r1=" + to_string(r1) + " r2=" + to_string(r2)};
    }

    return {true, "All 14 broker self-tests passed"};
}

// ============================================================================
// OOS RISK-GATED BACKTEST
// ============================================================================

struct OOSResult {
    string config_name = "";
    string model_type = "";
    double starting_balance = 0.0;
    double ending_balance = 0.0;
    double net_profit = 0.0;
    double return_pct = 0.0;
    double max_drawdown_dollars = 0.0;
    double max_drawdown_pct = 0.0;
    double stopout_equity = 0.0;
    bool stopped_out = false;
    int stopout_bar = -1;
    string stopout_reason = "";
    int bars_survived = 0;
    int oos_bars_total = 0;
    string risk_verdict = "";

    // Also include classification metrics from the OOS fold
    double auc = 0.0;
    double sharpe = 0.0;
    double utility = 0.0;
};

struct EquityCurveRow {
    string config = "";
    int bar_index = 0;
    double equity = 0.0;
    double gross_pnl = 0.0;
    double commission = 0.0;
    double net_pnl = 0.0;
    int position = 0;
    double drawdown_dollars = 0.0;
    double drawdown_pct = 0.0;
    bool stopped_out = false;
};

struct RiskSelfTestResult {
    bool pass;
    string msg;
};

RiskSelfTestResult run_risk_self_test() {
    // Test 1: should stop out
    {
        double bal = 10000.0;
        double max_dd_pct = 0.10;
        double stopout_eq = bal * (1.0 - max_dd_pct);
        vector<double> pnl = {-200, -300, -600};

        double equity = bal;
        double peak = bal;
        bool stopped = false;
        int stop_bar = -1;

        for (int i = 0; i < (int)pnl.size(); ++i) {
            equity += pnl[i];
            peak = max(peak, equity);
            double dd = peak - equity;
            double dd_pct = dd / bal;

            if (equity <= stopout_eq || dd_pct >= max_dd_pct) {
                stopped = true;
                stop_bar = i;
                break;
            }
        }

        if (!stopped) {
            return {false, "Risk self-test FAIL: expected stop-out on [-200,-300,-600] but did not stop"};
        }
        if (equity > stopout_eq + 1e-6) {
            return {false, "Risk self-test FAIL: equity=" + to_string(equity) + " should be <= " + to_string(stopout_eq)};
        }
    }

    // Test 2: should NOT stop out
    {
        double bal = 10000.0;
        double max_dd_pct = 0.10;
        double stopout_eq = bal * (1.0 - max_dd_pct);
        vector<double> pnl = {100, -50, 200};

        double equity = bal;
        double peak = bal;
        bool stopped = false;

        for (int i = 0; i < (int)pnl.size(); ++i) {
            equity += pnl[i];
            peak = max(peak, equity);
            double dd = peak - equity;
            double dd_pct = dd / bal;

            if (equity <= stopout_eq || dd_pct >= max_dd_pct) {
                stopped = true;
                break;
            }
        }

        if (stopped) {
            return {false, "Risk self-test FAIL: should not stop out on [100,-50,200]"};
        }
    }

    return {true, "Risk self-test passed"};
}

OOSResult run_oos_backtest(
    const string& config_name,
    const string& model_type,
    const vector<int>& positions,
    const vector<double>& next_bar_delta,
    double lot_size,
    double commission_per_lot,
    double gold_oz_per_lot,
    double starting_balance,
    double max_drawdown_pct,
    bool hard_stop,
    vector<EquityCurveRow>& equity_curve
) {
    OOSResult res;
    res.config_name = config_name;
    res.model_type = model_type;
    res.starting_balance = starting_balance;
    res.stopout_equity = starting_balance * (1.0 - max_drawdown_pct);
    res.oos_bars_total = (int)positions.size();

    double equity = starting_balance;
    double peak_equity = starting_balance;
    double max_dd = 0.0;

    for (int i = 0; i < (int)positions.size(); ++i) {
        int prev_pos = (i == 0) ? 0 : positions[i-1];
        int pos_change = abs(positions[i] - prev_pos);

        double gross = positions[i] * next_bar_delta[i] * gold_oz_per_lot * lot_size;
        double comm = pos_change * lot_size * commission_per_lot;
        double net = gross - comm;

        equity += net;
        peak_equity = max(peak_equity, equity);
        double dd = peak_equity - equity;
        double dd_pct = dd / starting_balance;
        max_dd = max(max_dd, dd);

        EquityCurveRow row;
        row.config = config_name;
        row.bar_index = i;
        row.equity = equity;
        row.gross_pnl = gross;
        row.commission = comm;
        row.net_pnl = net;
        row.position = positions[i];
        row.drawdown_dollars = dd;
        row.drawdown_pct = dd_pct;
        row.stopped_out = false;

        // Check risk stop
        if (hard_stop && (equity <= res.stopout_equity || dd_pct >= max_drawdown_pct)) {
            row.stopped_out = true;
            equity_curve.push_back(row);

            res.stopped_out = true;
            res.stopout_bar = i;
            res.stopout_reason = (equity <= res.stopout_equity) ? "equity_below_stopout" : "drawdown_pct_exceeded";
            res.bars_survived = i;
            res.ending_balance = equity;
            res.net_profit = equity - starting_balance;
            res.return_pct = res.net_profit / starting_balance;
            res.max_drawdown_dollars = max_dd;
            res.max_drawdown_pct = max_dd / starting_balance;
            res.risk_verdict = "RISK_STOPPED_OUT";
            return res;
        }

        equity_curve.push_back(row);
    }

    res.stopped_out = false;
    res.bars_survived = (int)positions.size();
    res.ending_balance = equity;
    res.net_profit = equity - starting_balance;
    res.return_pct = res.net_profit / starting_balance;
    res.max_drawdown_dollars = max_dd;
    res.max_drawdown_pct = max_dd / starting_balance;
    res.risk_verdict = "PASS_RISK";
    return res;
}

// ============================================================================
// BENCHMARK
// ============================================================================

void run_benchmark(const vector<vector<float>>& X, const vector<int>& y, const vector<double>& close, const vector<double>& next_bar_delta) {
    cout << "\n[BENCHMARK MODE]" << endl;

    // Feature scoring benchmark
    {
        auto start = high_resolution_clock::now();
        vector<FeatureScore> scores = score_all_features(X, y, "pearson");
        vector<int> top = rank_features_by_score(scores, 100);
        auto end = high_resolution_clock::now();
        auto ms = duration_cast<milliseconds>(end - start).count();
        double feature_scores_per_sec = (X[0].size() * 1000.0) / ms;
        cout << "Feature scoring (pearson): " << ms << " ms (" << (int)feature_scores_per_sec << " feature-scores/sec)" << endl;
    }

    // Logistic one epoch
    {
        vector<int> train_idx(X.size() / 2);
        iota(train_idx.begin(), train_idx.end(), 0);
        vector<vector<float>> X_train;
        vector<int> y_train;
        for (int idx : train_idx) {
            X_train.push_back(X[idx]);
            y_train.push_back(y[idx]);
        }

        LogisticRegression model(X[0].size(), 0.01, 0.001, 1);
        auto start = high_resolution_clock::now();
        model.fit(X_train, y_train);
        auto end = high_resolution_clock::now();
        auto ms = duration_cast<milliseconds>(end - start).count();
        double rows_per_sec = (X_train.size() * 1000.0) / ms;
        cout << "Logistic 1 epoch: " << ms << " ms (" << (int)rows_per_sec << " rows/sec)" << endl;
    }

    // Prediction benchmark
    {
        LogisticRegression model(X[0].size(), 0.01, 0.001, 1);
        vector<int> y_sub(X.size() / 2);
        vector<vector<float>> X_sub(X.begin(), X.begin() + X.size() / 2);
        for (size_t i = 0; i < y_sub.size(); ++i) y_sub[i] = y[i];
        model.fit(X_sub, y_sub);

        auto start = high_resolution_clock::now();
        auto probas = model.predict_proba(X);
        auto end = high_resolution_clock::now();
        auto ms = duration_cast<milliseconds>(end - start).count();
        double rows_per_sec = (X.size() * 1000.0) / ms;
        cout << "Prediction: " << ms << " ms (" << (int)rows_per_sec << " predictions/sec)" << endl;
    }

    cout << "\nBenchmark complete. Threads used: " << THREAD_COUNT << endl;
}

// ============================================================================
// MODEL SERIALIZATION
// ============================================================================

struct ModelMetadata {
    string model_name;
    string model_type;
    string direction_mode;
    int n_features = 0;
    vector<int> selected_feature_indices;
    vector<double> normalization_means;
    vector<double> normalization_stds;
    double threshold_long = 0.5;
    double threshold_short = 0.5;
    double train_years = 0;
    double oos_years = 0;
    int horizon = 0;
    double train_auc = 0;
    double oos_auc = 0;
    string signal_verdict;
    string model_edge_verdict;
    double baseline_return_pct = 0;
    double model_excess_return_pct = 0;
    string created_at;
};

string get_timestamp() {
    time_t now = time(nullptr);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", localtime(&now));
    return string(buf);
}

bool save_model_metadata(const string& path, const ModelMetadata& meta) {
    ofstream f(path);
    if (!f.is_open()) return false;

    f << "{\n";
    f << "  \"model_name\": \"" << json_escape(meta.model_name) << "\",\n";
    f << "  \"model_type\": \"" << json_escape(meta.model_type) << "\",\n";
    f << "  \"direction_mode\": \"" << json_escape(meta.direction_mode) << "\",\n";
    f << "  \"n_features\": " << meta.n_features << ",\n";
    f << "  \"selected_feature_indices\": [";
    for (size_t i = 0; i < meta.selected_feature_indices.size(); ++i) {
        f << meta.selected_feature_indices[i];
        if (i + 1 < meta.selected_feature_indices.size()) f << ",";
    }
    f << "],\n";
    f << "  \"normalization_means\": [";
    for (size_t i = 0; i < meta.normalization_means.size(); ++i) {
        f << meta.normalization_means[i];
        if (i + 1 < meta.normalization_means.size()) f << ",";
    }
    f << "],\n";
    f << "  \"normalization_stds\": [";
    for (size_t i = 0; i < meta.normalization_stds.size(); ++i) {
        f << meta.normalization_stds[i];
        if (i + 1 < meta.normalization_stds.size()) f << ",";
    }
    f << "],\n";
    f << "  \"threshold_long\": " << meta.threshold_long << ",\n";
    f << "  \"threshold_short\": " << meta.threshold_short << ",\n";
    f << "  \"train_years\": " << meta.train_years << ",\n";
    f << "  \"oos_years\": " << meta.oos_years << ",\n";
    f << "  \"horizon\": " << meta.horizon << ",\n";
    f << "  \"train_auc\": " << meta.train_auc << ",\n";
    f << "  \"oos_auc\": " << meta.oos_auc << ",\n";
    f << "  \"signal_verdict\": \"" << json_escape(meta.signal_verdict) << "\",\n";
    f << "  \"model_edge_verdict\": \"" << json_escape(meta.model_edge_verdict) << "\",\n";
    f << "  \"baseline_return_pct\": " << meta.baseline_return_pct << ",\n";
    f << "  \"model_excess_return_pct\": " << meta.model_excess_return_pct << ",\n";
    f << "  \"created_at\": \"" << json_escape(meta.created_at) << "\"\n";
    f << "}\n";
    f.close();
    return true;
}

bool save_logistic_weights(const string& path, const LogisticRegression& model) {
    ofstream f(path);
    if (!f.is_open()) return false;
    f << model.bias << "\n";
    for (double w : model.weights) f << w << "\n";
    f.close();
    return true;
}

bool load_logistic_weights(const string& path, LogisticRegression& model) {
    ifstream f(path);
    if (!f.is_open()) return false;
    f >> model.bias;
    for (size_t i = 0; i < model.weights.size(); ++i) {
        if (!(f >> model.weights[i])) return false;
    }
    f.close();
    return true;
}

struct LoadedSpecialistModel {
    string model_type;
    string direction_mode;
    int n_features = 0;
    vector<double> weights;
    double bias = 0;
    vector<int> selected_feature_indices;
    vector<double> normalization_means;
    vector<double> normalization_stds;
    double threshold_long = 0.5;
    double threshold_short = 0.5;
    double min_confidence = 0.02;
    double model_excess_return_pct = 0;
    double baseline_return_pct = 0;
    string model_edge_verdict;
    bool valid = false;
};

LoadedSpecialistModel load_specialist_model(const string& model_path, const string& meta_path) {
    LoadedSpecialistModel loaded;

    // Load metadata
    ifstream meta_file(meta_path);
    if (!meta_file.is_open()) {
        cerr << "ERROR: Cannot open metadata: " << meta_path << endl;
        return loaded;
    }

    string line;
    while (getline(meta_file, line)) {
        // Simple JSON parser for our exact format
        if (line.find("\"model_type\":") != string::npos) {
            size_t start = line.find("\"", line.find(":") + 1) + 1;
            size_t end = line.find("\"", start);
            loaded.model_type = line.substr(start, end - start);
        } else if (line.find("\"direction_mode\":") != string::npos) {
            size_t start = line.find("\"", line.find(":") + 1) + 1;
            size_t end = line.find("\"", start);
            loaded.direction_mode = line.substr(start, end - start);
        } else if (line.find("\"n_features\":") != string::npos) {
            size_t start = line.find(":") + 1;
            loaded.n_features = stoi(line.substr(start));
        } else if (line.find("\"selected_feature_indices\":") != string::npos) {
            // Parse array
            size_t bracket_start = line.find("[");
            size_t bracket_end = line.find("]");
            if (bracket_start != string::npos && bracket_end != string::npos) {
                string arr = line.substr(bracket_start + 1, bracket_end - bracket_start - 1);
                stringstream ss(arr);
                string item;
                while (getline(ss, item, ',')) {
                    loaded.selected_feature_indices.push_back(stoi(item));
                }
            }
        } else if (line.find("\"threshold_long\":") != string::npos) {
            size_t start = line.find(":") + 1;
            loaded.threshold_long = stod(line.substr(start));
        } else if (line.find("\"threshold_short\":") != string::npos) {
            size_t start = line.find(":") + 1;
            loaded.threshold_short = stod(line.substr(start));
        } else if (line.find("\"model_excess_return_pct\":") != string::npos) {
            size_t start = line.find(":") + 1;
            loaded.model_excess_return_pct = stod(line.substr(start));
        } else if (line.find("\"baseline_return_pct\":") != string::npos) {
            size_t start = line.find(":") + 1;
            loaded.baseline_return_pct = stod(line.substr(start));
        } else if (line.find("\"model_edge_verdict\":") != string::npos) {
            size_t start = line.find("\"", line.find(":") + 1) + 1;
            size_t end = line.find("\"", start);
            loaded.model_edge_verdict = line.substr(start, end - start);
        }
    }
    meta_file.close();

    // Metadata does not include normalization arrays in simple format
    // Load from separate lines if present, or infer from selected features
    // For now, require normalization to be disabled for loaded models
    // or read from extended metadata

    // Load weights
    ifstream wf(model_path);
    if (!wf.is_open()) {
        cerr << "ERROR: Cannot open model weights: " << model_path << endl;
        return loaded;
    }

    wf >> loaded.bias;
    double w;
    while (wf >> w) {
        loaded.weights.push_back(w);
    }
    wf.close();

    // Validate
    if (loaded.weights.size() != loaded.selected_feature_indices.size()) {
        cerr << "ERROR: Weight count (" << loaded.weights.size() << ") != feature count (" << loaded.selected_feature_indices.size() << ")" << endl;
        return loaded;
    }

    if (loaded.model_type.empty() || loaded.direction_mode.empty()) {
        cerr << "ERROR: Missing model_type or direction_mode in metadata" << endl;
        return loaded;
    }

    loaded.valid = true;
    return loaded;
}

double predict_loaded_specialist(const LoadedSpecialistModel& model, const vector<float>& X_row_full,
                                   const vector<double>& norm_means, const vector<double>& norm_stds) {
    if (!model.valid || model.weights.size() != model.selected_feature_indices.size()) {
        return 0.5;
    }

    double dot = model.bias;
    for (size_t i = 0; i < model.selected_feature_indices.size(); ++i) {
        int feat_idx = model.selected_feature_indices[i];
        if (feat_idx < 0 || feat_idx >= (int)X_row_full.size()) continue;

        double x = X_row_full[feat_idx];

        // Normalize if means/stds provided
        if (i < norm_means.size() && i < norm_stds.size()) {
            if (norm_stds[i] > 1e-9) {
                x = (x - norm_means[i]) / norm_stds[i];
            }
        }

        dot += model.weights[i] * x;
    }

    // Clip logit
    dot = max(-20.0, min(20.0, dot));

    // Sigmoid
    return 1.0 / (1.0 + exp(-dot));
}

// ============================================================================
// MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    // Parse args
    string data_dir = "data/hydra_binary_288b";
    int n_folds = 5;
    int horizon = 288;
    double commission_per_lot = 5.0;
    double lot_size = 1.0;
    string n_threads_str = "auto";
    string progress_jsonl_path = "reports/hydra_cpp_288b_progress.jsonl";
    string output_csv_path = "runs/hydra_cpp_288b_results.csv";
    string output_json_path = "reports/hydra_cpp_288b_summary.json";
    string runtime_log_path = "reports/hydra_cpp_288b_runtime.log";

    string feature_score_method = "pearson";
    string objective = "sharpe";
    bool regime_aware = false;

    for (int i = 1; i < argc; ++i) {
        string arg = argv[i];
        if (arg == "--data-dir" && i + 1 < argc) data_dir = argv[++i];
        else if (arg == "--folds" && i + 1 < argc) n_folds = stoi(argv[++i]);
        else if (arg == "--horizon" && i + 1 < argc) horizon = stoi(argv[++i]);
        else if (arg == "--commission-per-lot" && i + 1 < argc) commission_per_lot = stod(argv[++i]);
        else if (arg == "--lot-size" && i + 1 < argc) lot_size = stod(argv[++i]);
        else if (arg == "--threads" && i + 1 < argc) n_threads_str = argv[++i];
        else if (arg == "--parallel-mode" && i + 1 < argc) PARALLEL_MODE = argv[++i];
        else if (arg == "--feature-score-method" && i + 1 < argc) feature_score_method = argv[++i];
        else if (arg == "--objective" && i + 1 < argc) objective = argv[++i];
        else if (arg == "--regime-aware") regime_aware = true;
        else if (arg == "--math-sweep") MATH_SWEEP = true;
        else if (arg == "--max-configs" && i + 1 < argc) MAX_SWEEP_CONFIGS = stoi(argv[++i]);
        else if (arg == "--max-runtime-minutes" && i + 1 < argc) MAX_SWEEP_RUNTIME_MINUTES = stoi(argv[++i]);
        else if (arg == "--smoke") SMOKE = true;
        else if (arg == "--verbose") VERBOSE = true;
        else if (arg == "--benchmark") BENCHMARK = true;
        else if (arg == "--progress-jsonl" && i + 1 < argc) progress_jsonl_path = argv[++i];
        else if (arg == "--output-csv" && i + 1 < argc) output_csv_path = argv[++i];
        else if (arg == "--disable-rank-ensemble") DISABLE_RANK_ENSEMBLE = true;
        else if (arg == "--only-model" && i + 1 < argc) ONLY_MODEL = argv[++i];
        else if (arg == "--debug-fold-timeout-seconds" && i + 1 < argc) DEBUG_FOLD_TIMEOUT_SECONDS = stoi(argv[++i]);
        else if (arg == "--split-mode" && i + 1 < argc) SPLIT_MODE = argv[++i];
        else if (arg == "--train-years" && i + 1 < argc) TRAIN_YEARS = stod(argv[++i]);
        else if (arg == "--oos-years" && i + 1 < argc) OOS_YEARS = stod(argv[++i]);
        else if (arg == "--starting-balance" && i + 1 < argc) STARTING_BALANCE = stod(argv[++i]);
        else if (arg == "--max-drawdown-pct" && i + 1 < argc) MAX_DRAWDOWN_PCT = stod(argv[++i]);
        else if (arg == "--hard-stop-on-drawdown") HARD_STOP_ON_DRAWDOWN = true;
        else if (arg == "--equity-output" && i + 1 < argc) EQUITY_OUTPUT_PATH = argv[++i];
        else if (arg == "--leverage" && i + 1 < argc) LEVERAGE = stod(argv[++i]);
        else if (arg == "--max-loss-pct" && i + 1 < argc) MAX_LOSS_PCT = stod(argv[++i]);
        else if (arg == "--maintenance-margin-ratio" && i + 1 < argc) MAINTENANCE_MARGIN_RATIO = stod(argv[++i]);
        else if (arg == "--require-bracket-orders") REQUIRE_BRACKET_ORDERS = true;
        else if (arg == "--max-open-positions" && i + 1 < argc) MAX_OPEN_POSITIONS = stoi(argv[++i]);
        else if (arg == "--max-holding-bars" && i + 1 < argc) MAX_HOLDING_BARS = stoi(argv[++i]);
        else if (arg == "--default-rr" && i + 1 < argc) DEFAULT_RR = stod(argv[++i]);
        else if (arg == "--atr-sl-mult" && i + 1 < argc) ATR_SL_MULT = stod(argv[++i]);
        else if (arg == "--trailing-stop") TRAILING_STOP_ENABLED = true;
        else if (arg == "--trailing-atr-mult" && i + 1 < argc) TRAILING_ATR_MULT = stod(argv[++i]);
        else if (arg == "--use-fibonacci-exits") USE_FIBONACCI_EXITS = true;
        else if (arg == "--confidence-rr") CONFIDENCE_RR = true;
        else if (arg == "--min-rr" && i + 1 < argc) MIN_RR = stod(argv[++i]);
        else if (arg == "--max-rr" && i + 1 < argc) MAX_RR = stod(argv[++i]);
        else if (arg == "--risk-per-trade-pct" && i + 1 < argc) RISK_PER_TRADE_PCT = stod(argv[++i]);
        else if (arg == "--auto-size-by-risk") AUTO_SIZE_BY_RISK = true;
        else if (arg == "--trail-activate-r" && i + 1 < argc) TRAIL_ACTIVATE_R = stod(argv[++i]);
        else if (arg == "--trail-distance-r" && i + 1 < argc) TRAIL_DISTANCE_R = stod(argv[++i]);
        else if (arg == "--move-sl-to-breakeven-at-r" && i + 1 < argc) MOVE_SL_TO_BREAKEVEN_AT_R = stod(argv[++i]);
        else if (arg == "--kelly-sizing") KELLY_SIZING = true;
        else if (arg == "--kelly-fraction" && i + 1 < argc) KELLY_FRACTION = stod(argv[++i]);
        else if (arg == "--kelly-lookback-trades" && i + 1 < argc) KELLY_LOOKBACK_TRADES = stoi(argv[++i]);
        else if (arg == "--kelly-min-samples" && i + 1 < argc) KELLY_MIN_SAMPLES = stoi(argv[++i]);
        else if (arg == "--max-risk-per-trade-pct" && i + 1 < argc) MAX_RISK_PER_TRADE_PCT = stod(argv[++i]);
        else if (arg == "--min-risk-per-trade-pct" && i + 1 < argc) MIN_RISK_PER_TRADE_PCT = stod(argv[++i]);
        else if (arg == "--max-lot-size" && i + 1 < argc) MAX_LOT_SIZE = stod(argv[++i]);
        else if (arg == "--min-lot-size" && i + 1 < argc) MIN_LOT_SIZE = stod(argv[++i]);
        else if (arg == "--drawdown-risk-throttle") DRAWDOWN_RISK_THROTTLE = true;
        else if (arg == "--kelly-mode" && i + 1 < argc) KELLY_MODE = argv[++i];
        else if (arg == "--min-confidence" && i + 1 < argc) MIN_CONFIDENCE = stod(argv[++i]);
        else if (arg == "--max-trades-per-config" && i + 1 < argc) MAX_TRADES_PER_CONFIG = stoi(argv[++i]);
        else if (arg == "--reject-constant-proba") REJECT_CONSTANT_PROBA = true;
        else if (arg == "--max-saturation-rate" && i + 1 < argc) MAX_SATURATION_RATE = stod(argv[++i]);
        else if (arg == "--min-proba-std" && i + 1 < argc) MIN_PROBA_STD = stod(argv[++i]);
        else if (arg == "--no-trailing-ablation") NO_TRAILING_ABLATION = true;
        else if (arg == "--normalize-features") NORMALIZE_FEATURES = true;
        else if (arg == "--no-normalize-features") NORMALIZE_FEATURES = false;
        else if (arg == "--calibrate-proba") CALIBRATE_PROBA = true;
        else if (arg == "--regime-filter") REGIME_FILTER = true;
        else if (arg == "--strict-regime-direction") STRICT_REGIME_DIRECTION = true;
        else if (arg == "--allow-long") ALLOW_LONG = true;
        else if (arg == "--no-allow-long") ALLOW_LONG = false;
        else if (arg == "--allow-short") ALLOW_SHORT = true;
        else if (arg == "--no-allow-short") ALLOW_SHORT = false;
        else if (arg == "--allow-close-and-reverse") ALLOW_CLOSE_AND_REVERSE = true;
        else if (arg == "--min-long-confidence") { if (++i < argc) MIN_LONG_CONFIDENCE = atof(argv[i]); }
        else if (arg == "--min-short-confidence") { if (++i < argc) MIN_SHORT_CONFIDENCE = atof(argv[i]); }
        else if (arg == "--progress-jsonl") { if (++i < argc) PROGRESS_JSONL_PATH = argv[i]; }
        else if (arg == "--quiet-console") QUIET_CONSOLE = true;
        else if (arg == "--direction-mode") { if (++i < argc) DIRECTION_MODE = argv[i]; }
        else if (arg == "--save-models") SAVE_MODELS = true;
        else if (arg == "--save-best-candidate") SAVE_BEST_CANDIDATE = true;
        else if (arg == "--model-dir") { if (++i < argc) MODEL_DIR = argv[i]; }
        else if (arg == "--long-model-path") { if (++i < argc) LONG_MODEL_PATH = argv[i]; }
        else if (arg == "--short-model-path") { if (++i < argc) SHORT_MODEL_PATH = argv[i]; }
        else if (arg == "--load-long-model") { if (++i < argc) LOAD_LONG_MODEL_PATH = argv[i]; }
        else if (arg == "--load-short-model") { if (++i < argc) LOAD_SHORT_MODEL_PATH = argv[i]; }
        else if (arg == "--dual-combiner") { if (++i < argc) DUAL_COMBINER = argv[i]; }
        else if (arg == "--min-edge-gap") { if (++i < argc) MIN_EDGE_GAP = atof(argv[i]); }
        else if (arg == "--dual-long-fallback") { if (++i < argc) DUAL_LONG_FALLBACK = argv[i]; }
    }

    // Validate direction mode
    if (DIRECTION_MODE != "both" && DIRECTION_MODE != "long-only" &&
        DIRECTION_MODE != "short-only" && DIRECTION_MODE != "dual-specialist") {
        cerr << "Error: Invalid --direction-mode. Must be: both, long-only, short-only, dual-specialist" << endl;
        return 1;
    }

    // Enforce direction mode constraints
    if (DIRECTION_MODE == "long-only") {
        ALLOW_LONG = true;
        ALLOW_SHORT = false;
    } else if (DIRECTION_MODE == "short-only") {
        ALLOW_LONG = false;
        ALLOW_SHORT = true;
    } else if (DIRECTION_MODE == "dual-specialist") {
        if (LOAD_LONG_MODEL_PATH.empty() || LOAD_SHORT_MODEL_PATH.empty()) {
            cerr << "Error: dual-specialist mode requires --load-long-model and --load-short-model" << endl;
            return 1;
        }
        ALLOW_LONG = true;
        ALLOW_SHORT = true;
    }

    // Configure threads
    int n_threads = get_thread_count(n_threads_str);
    configure_threads(n_threads);

    // Open logs
    PROGRESS_JSONL.open(progress_jsonl_path, ios::app);
    RUNTIME_LOG.open(runtime_log_path, ios::app);

    if (!PROGRESS_JSONL_PATH.empty()) {
        ofstream progress_file(PROGRESS_JSONL_PATH, ios::trunc);
        PROGRESS_JSONL.swap(progress_file);
    }

    // Open partial CSV (overwrite)
    string partial_csv_path = "runs/hydra_cpp_288b_partial.csv";
    PARTIAL_CSV.open(partial_csv_path, ios::trunc);
    PARTIAL_CSV << "config,model_type,fold,n_features,threshold_long,threshold_short,"
                << "auc,balanced_accuracy,accuracy,f1,long_rate,short_rate,flat_rate,"
                << "gross_pnl,commission_paid,net_pnl,n_trades,sharpe,max_drawdown,calmar,utility,"
                << "feature_score_method,avg_pearson_ic,avg_spearman_ic,avg_mi,avg_stability,avg_turnover,"
                << "objective,regime_aware\n";
    PARTIAL_CSV.flush();

    print_progress("================================================================================", true);
    print_progress("HYDRA C++ FAST TRAINING (8-CORE OPTIMIZED)", true);
    print_progress("================================================================================", true);

    log_event("run_start", "\"mode\":\"" + string(SMOKE ? "smoke" : BENCHMARK ? "benchmark" : "full") + "\",\"threads\":" + to_string(THREAD_COUNT));

    emit_progress_event("{\"event\":\"run_start\",\"timestamp\":" + to_string(duration_cast<milliseconds>(RUN_START.time_since_epoch()).count()) +
        ",\"threads\":" + to_string(THREAD_COUNT) +
        ",\"openmp_enabled\":" + string(HYDRA_OPENMP ? "true" : "false") +
        ",\"split_mode\":\"" + SPLIT_MODE + "\"" +
        ",\"train_years\":" + to_string(TRAIN_YEARS) +
        ",\"oos_years\":" + to_string(OOS_YEARS) +
        ",\"starting_balance\":" + to_string(STARTING_BALANCE) +
        ",\"leverage\":" + to_string(LEVERAGE) +
        ",\"max_loss_pct\":" + to_string(MAX_LOSS_PCT) + "}");

    // Load meta
    string meta_path = data_dir + "/meta.json";
    ifstream meta_file(meta_path);
    if (!meta_file.is_open()) {
        cerr << "Error: Cannot open " << meta_path << endl;
        return 1;
    }

    Meta meta;
    string line;
    while (getline(meta_file, line)) {
        if (line.find("\"rows\"") != string::npos) {
            sscanf(line.c_str(), "  \"rows\": %d,", &meta.rows);
        } else if (line.find("\"cols\"") != string::npos) {
            sscanf(line.c_str(), "  \"cols\": %d,", &meta.cols);
        } else if (line.find("\"horizon\"") != string::npos) {
            sscanf(line.c_str(), "  \"horizon\": %d,", &meta.horizon);
        } else if (line.find("\"commission_per_lot\"") != string::npos) {
            sscanf(line.c_str(), "  \"commission_per_lot\": %lf,", &meta.commission_per_lot);
        } else if (line.find("\"gold_oz_per_lot\"") != string::npos) {
            sscanf(line.c_str(), "  \"gold_oz_per_lot\": %lf", &meta.gold_oz_per_lot);
        }
    }
    meta_file.close();

    print_progress("\n[LOAD DATA]", true);
    print_progress("Rows: " + to_string(meta.rows), true);
    print_progress("Cols: " + to_string(meta.cols), true);

    log_event("dataset_loaded", "\"rows\":" + to_string(meta.rows) + ",\"cols\":" + to_string(meta.cols));

    // Load X — single bulk read into contiguous buffer
    auto load_start = high_resolution_clock::now();

    string X_path = data_dir + "/X_float32.bin";
    ifstream X_file(X_path, ios::binary | ios::ate);
    if (!X_file.is_open()) {
        cerr << "Error: Cannot open " << X_path << endl;
        return 1;
    }

    size_t X_file_size = X_file.tellg();
    size_t X_expected = (size_t)meta.rows * meta.cols * sizeof(float);
    if (X_file_size < X_expected) {
        cerr << "Error: X file too small. Expected " << X_expected << " got " << X_file_size << endl;
        return 1;
    }

    // Allocate flat buffer, single read
    vector<float> X_flat(meta.rows * (long long)meta.cols);
    X_file.seekg(0);
    X_file.read(reinterpret_cast<char*>(X_flat.data()), X_expected);
    X_file.close();

    // Wrap as row pointers for existing API compatibility
    vector<vector<float>> X(meta.rows);
    #pragma omp parallel for if (HYDRA_OPENMP)
    for (int i = 0; i < meta.rows; ++i) {
        X[i].assign(X_flat.data() + (long long)i * meta.cols,
                    X_flat.data() + (long long)(i + 1) * meta.cols);
    }
    X_flat.clear();
    X_flat.shrink_to_fit();

    auto x_done = high_resolution_clock::now();
    double x_ms = duration_cast<milliseconds>(x_done - load_start).count();
    double x_mb = X_expected / (1024.0 * 1024.0);
    print_progress("✓ X loaded: " + to_string((int)x_mb) + " MB in " + to_string((int)x_ms) + " ms (" + to_string((int)(x_mb / (x_ms / 1000.0))) + " MB/s)", true);

    emit_progress_event("{\"event\":\"data_loaded\",\"load_ms\":" + to_string((int)x_ms) +
        ",\"rows\":" + to_string(meta.rows) +
        ",\"cols\":" + to_string(meta.cols) +
        ",\"mb_loaded\":" + to_string((int)x_mb) +
        ",\"mb_per_second\":" + to_string((int)(x_mb / (x_ms / 1000.0))) + "}");

    // Load y — single read
    string y_path = data_dir + "/y_int8.bin";
    ifstream y_file(y_path, ios::binary);
    if (!y_file.is_open()) {
        cerr << "Error: Cannot open " << y_path << endl;
        return 1;
    }

    vector<int> y(meta.rows);
    vector<int8_t> y_buf(meta.rows);
    y_file.read(reinterpret_cast<char*>(y_buf.data()), meta.rows);
    y_file.close();

    for (int i = 0; i < meta.rows; ++i) {
        y[i] = y_buf[i];
    }

    auto y_done = high_resolution_clock::now();
    double y_ms = duration_cast<milliseconds>(y_done - x_done).count();
    double y_mb = meta.rows / (1024.0 * 1024.0);
    print_progress("✓ y loaded: " + to_string((int)(y_mb * 1024)) + " KB in " + to_string((int)y_ms) + " ms", true);

    // Load close — single bulk read
    string close_path = data_dir + "/close_float64.bin";
    ifstream close_file(close_path, ios::binary);
    if (!close_file.is_open()) {
        cerr << "Error: Cannot open " << close_path << endl;
        return 1;
    }

    vector<double> close(meta.rows);
    close_file.read(reinterpret_cast<char*>(close.data()), meta.rows * sizeof(double));
    close_file.close();

    auto close_done = high_resolution_clock::now();
    double close_ms = duration_cast<milliseconds>(close_done - y_done).count();
    double close_mb = meta.rows * sizeof(double) / (1024.0 * 1024.0);
    print_progress("✓ close loaded: " + to_string((int)close_mb) + " MB in " + to_string((int)close_ms) + " ms (" + to_string((int)(close_mb / (close_ms / 1000.0))) + " MB/s)", true);

    double total_load_ms = duration_cast<milliseconds>(close_done - load_start).count();
    double total_mb = x_mb + y_mb + close_mb;
    print_progress("  Total load: " + to_string((int)total_mb) + " MB in " + to_string((int)total_load_ms) + " ms (" + to_string((int)(total_mb / (total_load_ms / 1000.0))) + " MB/s)", true);

    // Compute next-bar delta: close[t+1] - close[t] (sequential M5 bar move)
    vector<double> next_bar_delta(meta.rows, 0.0);
    #pragma omp parallel for if (HYDRA_OPENMP)
    for (int i = 0; i < meta.rows - 1; ++i) {
        next_bar_delta[i] = close[i + 1] - close[i];
    }

    print_progress("✓ next-bar deltas computed (M5 close-to-close)", true);

    log_event("validation_passed");

    // Benchmark mode
    if (BENCHMARK) {
        run_benchmark(X, y, close, next_bar_delta);
        PROGRESS_JSONL.close();
        RUNTIME_LOG.close();
        return 0;
    }

    // AUC self-test before any training
    {
        print_progress("\n[AUC SELF-TEST]", true);
        vector<int> test_y = {0, 0, 1, 1};
        vector<double> proba_perfect = {0.1, 0.2, 0.8, 0.9};
        vector<double> proba_worst = {0.9, 0.8, 0.2, 0.1};
        vector<double> proba_random = {0.5, 0.5, 0.5, 0.5};

        double auc_perfect = compute_auc(test_y, proba_perfect);
        double auc_worst = compute_auc(test_y, proba_worst);
        double auc_random = compute_auc(test_y, proba_random);

        print_progress("  Perfect AUC: " + to_string(auc_perfect) + " (expect 1.0)", true);
        print_progress("  Worst AUC:   " + to_string(auc_worst) + " (expect 0.0)", true);
        print_progress("  Random AUC:  " + to_string(auc_random) + " (expect 0.5)", true);

        bool pass = (abs(auc_perfect - 1.0) < 1e-9) &&
                    (abs(auc_worst - 0.0) < 1e-9) &&
                    (abs(auc_random - 0.5) < 1e-9);

        if (!pass) {
            cerr << "FATAL: AUC self-test FAILED. Implementation is broken." << endl;
            return 1;
        }
        print_progress("  ✓ All AUC self-tests passed", true);
    }

    // PnL self-test before training
    {
        print_progress("\n[PNL SELF-TEST]", true);
        // close = [2000, 2001, 2002]
        // positions = [1, 1, 0]  (long, long, flat)
        // next_bar_delta = [1, 1, 0] (2001-2000, 2002-2001, no next bar)
        // gold_oz_per_lot = 100
        // lot_size = 1, commission_per_lot = 5
        //
        // gross = 1*1*100 + 1*1*100 + 0*0*100 = 200
        // commission: flat->long |1-0|=1 → $5, long->long |1-1|=0, long->flat |0-1|=1 → $5 = $10 total
        // net = 200 - 10 = 190

        vector<int> test_pos = {1, 1, 0};
        vector<double> test_delta = {1.0, 1.0, 0.0};
        double test_lot = 1.0;
        double test_comm = 5.0;
        double test_oz = 100.0;

        auto pnl_result = calculate_pnl(test_pos, test_delta, test_lot, test_comm, test_oz);

        print_progress("  Gross PnL: " + to_string(pnl_result.gross_pnl) + " (expect 200.0)", true);
        print_progress("  Commission: " + to_string(pnl_result.commission) + " (expect 10.0)", true);
        print_progress("  Net PnL:   " + to_string(pnl_result.net_pnl) + " (expect 190.0)", true);

        bool pnl_pass = (abs(pnl_result.gross_pnl - 200.0) < 1e-6) &&
                        (abs(pnl_result.commission - 10.0) < 1e-6) &&
                        (abs(pnl_result.net_pnl - 190.0) < 1e-6);

        if (!pnl_pass) {
            cerr << "FATAL: PnL self-test FAILED." << endl;
            cerr << "  gross=" << pnl_result.gross_pnl << " commission=" << pnl_result.commission
                 << " net=" << pnl_result.net_pnl << endl;
            return 1;
        }
        print_progress("  ✓ PnL self-test passed", true);
    }

    // Print trading model description
    print_progress("\n[TRADING MODEL]", true);
    print_progress("  Classification target: label_288b (288-bar forward return sign)", true);
    print_progress("  Trading return stream: next M5 close-to-close delta (sequential)", true);
    print_progress("  Commission: fixed $" + to_string(commission_per_lot) + "/lot per position change", true);
    print_progress("  Spread/slippage: not modeled (prop firm covers)", true);
    print_progress("  Gold oz/lot: " + to_string(meta.gold_oz_per_lot), true);

    // ============================================================================
    // TRAIN-OOS SPLIT MODE (prop-firm broker simulator)
    // ============================================================================
    if (SPLIT_MODE == "train-oos") {
        print_progress("\n[SPLIT MODE: train-oos (BROKER SIMULATOR)]", true);

        // Broker self-tests
        {
            print_progress("\n[BROKER SELF-TESTS]", true);
            auto bst = run_broker_self_tests();
            if (!bst.pass) {
                cerr << "FATAL: " << bst.msg << endl;
                emit_progress_event("{\"event\":\"self_test\",\"name\":\"broker\",\"passed\":false,\"details\":\"" + json_escape(bst.msg) + "\"}");
                return 1;
            }
            print_progress("  " + bst.msg, true);
            emit_progress_event("{\"event\":\"self_test\",\"name\":\"broker\",\"passed\":true,\"details\":\"" + json_escape(bst.msg) + "\"}");
        }

        // Risk self-test (legacy)
        {
            print_progress("\n[RISK SELF-TEST]", true);
            auto rst = run_risk_self_test();
            if (!rst.pass) {
                cerr << "FATAL: " << rst.msg << endl;
                emit_progress_event("{\"event\":\"self_test\",\"name\":\"risk\",\"passed\":false,\"details\":\"" + json_escape(rst.msg) + "\"}");
                return 1;
            }
            print_progress("  " + rst.msg, true);
            emit_progress_event("{\"event\":\"self_test\",\"name\":\"risk\",\"passed\":true,\"details\":\"" + json_escape(rst.msg) + "\"}");
        }

        // Dual-specialist path
        if (DIRECTION_MODE == "dual-specialist") {
            print_progress("\n[DUAL-SPECIALIST MODE]", true);

            // Truncate output files before running dual inference
            print_progress("  Truncating output CSVs for dual-specialist isolation", true);
            ofstream trunc_results(output_csv_path, ios::trunc);
            trunc_results << "config,direction_mode,model_type,starting_balance,ending_balance,net_profit,return_pct,"
                         << "leverage,max_loss_pct,stopout_equity,max_dd_dollars,max_dd_pct,max_used_margin,min_free_margin,"
                         << "margin_call,account_failed,risk_verdict,total_trades,wins,losses,win_rate,avg_win,avg_loss,"
                         << "profit_factor,avg_holding_bars,tp_hits,sl_hits,trailing_stop_hits,time_stop_hits,rejected_orders,"
                         << "margin_rejections,no_sl_rejections,kelly_too_small_rejections,kelly_negative_rejections,"
                         << "drawdown_throttle_rejections,kelly_invalid_sample_rejections,max_trades_rejections,max_open_pos_rejections,"
                         << "orders_attempted,orders_opened,avg_rr,avg_confidence,kelly_enabled,kelly_mode,kelly_fraction,"
                         << "avg_kelly_raw,avg_kelly_risk_pct,avg_final_risk_pct,kelly_fallback_count,train_long_precision,"
                         << "train_short_precision,train_auc,train_samples,oos_long_precision,oos_short_precision,oos_auc,oos_samples,"
                         << "baseline_always_long,baseline_always_short,baseline_random_50_50,baseline_flat_no_trade,"
                         << "best_baseline_return_pct,best_baseline_name,model_excess_return_pct,edge_confirmed_train,"
                         << "signal_verdict,proba_saturation_rate,proba_source,reject_reason,training_signal_valid,model_edge_verdict,"
                         << "reject_constant_proba,reject_saturated_proba,proba_mean,proba_std,kelly_invalid_sample,drawdown_throttle_events,"
                         << "kelly_too_small_events,kelly_negative_events,allow_long,allow_short,allow_close_and_reverse,"
                         << "strict_regime_direction,long_trades,short_trades,long_win_rate,short_win_rate,long_net_pnl,short_net_pnl,"
                         << "reverse_exits,ignored_opposite_signals,blocked_long_signals,blocked_short_signals,"
                         << "blocked_counter_regime_signals,regime_tag,regime_applied,baseline_return_baseline,"
                         << "loaded_long_model,loaded_short_model,hedge_violations,"
                         << "long_specialist_edge_verdict,short_specialist_edge_verdict,long_model_excess_pct,short_model_excess_pct,"
                         << "combined_return_pct,best_baseline_return_pct_dual,best_baseline_name_dual,combined_excess_pct,"
                         << "combiner_long_choices,combiner_short_choices,combiner_flat_choices,combiner_conflicts,"
                         << "long_model_validated,short_model_validated\n";
            trunc_results.close();

            ofstream trunc_equity(EQUITY_OUTPUT_PATH, ios::trunc);
            trunc_equity << "config,bar_index,close_price,balance,equity,unrealized_pnl,realized_pnl,"
                        << "used_margin,free_margin,open_positions,drawdown_dollars,drawdown_pct,account_failed,fail_reason\n";
            trunc_equity.close();

            ofstream trunc_trades(TRADES_OUTPUT_PATH, ios::trunc);
            trunc_trades << "config,trade_id,entry_bar,exit_bar,direction,lot_size,entry_price,exit_price,"
                        << "stop_loss_price,take_profit_price,trailing_stop_price,gross_pnl,commission,net_pnl,"
                        << "required_margin,balance_after,equity_after,holding_bars,exit_reason,confidence,rr,"
                        << "kelly_raw,kelly_risk_pct,final_risk_pct,lot_by_risk,lot_by_margin,final_lot_size,"
                        << "risk_dollars,drawdown_risk_multiplier,kelly_fallback_used,signal_probability,regime_at_entry,"
                        << "was_counter_regime\n";
            trunc_trades.close();

            // Load long specialist
            print_progress("  Loading long specialist: " + LOAD_LONG_MODEL_PATH, true);
            LoadedSpecialistModel long_model = load_specialist_model(LOAD_LONG_MODEL_PATH, LOAD_LONG_MODEL_PATH + ".meta.json");
            if (!long_model.valid) {
                cerr << "FATAL: Failed to load long specialist: " << LOAD_LONG_MODEL_PATH << endl;
                return 1;
            }
            print_progress("    Model: " + long_model.model_type + " | Features: " + to_string(long_model.selected_feature_indices.size()) + " | Excess: " + to_string(long_model.model_excess_return_pct * 100).substr(0, 6) + "%", true);
            bool long_validated = (long_model.model_edge_verdict == "EDGE_CONFIRMED");
            if (!long_validated) {
                print_progress("    WARNING: long specialist is candidate only, not validated edge (verdict: " + long_model.model_edge_verdict + ")", true);
            }

            // Load short specialist
            print_progress("  Loading short specialist: " + LOAD_SHORT_MODEL_PATH, true);
            LoadedSpecialistModel short_model = load_specialist_model(LOAD_SHORT_MODEL_PATH, LOAD_SHORT_MODEL_PATH + ".meta.json");
            if (!short_model.valid) {
                cerr << "FATAL: Failed to load short specialist: " << LOAD_SHORT_MODEL_PATH << endl;
                return 1;
            }
            print_progress("    Model: " + short_model.model_type + " | Features: " + to_string(short_model.selected_feature_indices.size()) + " | Excess: " + to_string(short_model.model_excess_return_pct * 100).substr(0, 6) + "%", true);
            bool short_validated = (short_model.model_edge_verdict == "EDGE_CONFIRMED");

            print_progress("  Short specialist convention: probability_of_up=true (low p => short signal)", true);

            // Load normalization from metadata if present, else disable
            vector<double> long_norm_means = long_model.normalization_means;
            vector<double> long_norm_stds = long_model.normalization_stds;
            vector<double> short_norm_means = short_model.normalization_means;
            vector<double> short_norm_stds = short_model.normalization_stds;

            // OOS split
            double bars_per_year = (double)meta.rows / 11.4;
            int train_rows = (int)(TRAIN_YEARS * bars_per_year);
            int oos_rows = (int)(OOS_YEARS * bars_per_year);
            if (train_rows + horizon + oos_rows > meta.rows) {
                oos_rows = meta.rows - train_rows - horizon;
            }
            int train_start = 0, train_end = train_rows;
            int oos_start = train_end + horizon;
            int oos_end = min(oos_start + oos_rows, meta.rows);
            int oos_n = oos_end - oos_start;

            print_progress("  OOS: rows [" + to_string(oos_start) + ".." + to_string(oos_end) + "] (" + to_string(oos_n) + " bars)", true);

            // Prepare OOS data
            vector<double> oos_closes(oos_n);
            for (int i = 0; i < oos_n; ++i) {
                oos_closes[i] = close[oos_start + i];
            }

            // Open output files
            ofstream results_csv(output_csv_path, ios::app);
            ofstream equity_csv(EQUITY_OUTPUT_PATH, ios::app);
            ofstream trades_csv(TRADES_OUTPUT_PATH, ios::app);

            // Create broker
            BrokerSimulator broker(STARTING_BALANCE, LEVERAGE, MAX_LOSS_PCT, meta.commission_per_lot, meta.gold_oz_per_lot);

            // Combiner stats
            int combiner_long_choices = 0;
            int combiner_short_choices = 0;
            int combiner_flat_choices = 0;
            int combiner_conflicts = 0;
            double combiner_edge_gap_sum = 0;
            int hedge_violations = 0;

            print_progress("\n[DUAL COMBINER INFERENCE]", true);
            print_progress("  Combiner: " + DUAL_COMBINER, true);
            print_progress("  Min edge gap: " + to_string(MIN_EDGE_GAP), true);

            // Run broker with dual combiner
            for (int i = 0; i < oos_n; ++i) {
                double current_close_price = oos_closes[i];
                broker.tick(i, current_close_price);

                if (broker.account.is_failed) {
                    broker.equity_curve.push_back(broker.make_equity_row("dual_specialist_combined", i, current_close_price));
                    break;
                }

                do {
                    if ((int)broker.open_positions.size() >= MAX_OPEN_POSITIONS) {
                        broker.stats.rejected_orders++;
                        broker.stats.max_open_pos_rejections++;
                        break;
                    }
                    if (MAX_TRADES_PER_CONFIG > 0 && broker.stats.total_trades >= MAX_TRADES_PER_CONFIG) {
                        broker.stats.rejected_orders++;
                        broker.stats.max_trades_rejections++;
                        break;
                    }

                    // Predict both specialists
                    double long_p = predict_loaded_specialist(long_model, X[oos_start + i], long_norm_means, long_norm_stds);
                    double short_p = predict_loaded_specialist(short_model, X[oos_start + i], short_norm_means, short_norm_stds);

                    double long_conf = abs(long_p - 0.5) * 2.0;
                    double short_conf = abs(short_p - 0.5) * 2.0;

                    // Check pass conditions
                    bool long_pass = (long_p >= long_model.threshold_long) && (long_conf >= MIN_LONG_CONFIDENCE) && ALLOW_LONG;
                    bool short_pass = (short_p <= short_model.threshold_short) && (short_conf >= MIN_SHORT_CONFIDENCE) && ALLOW_SHORT;

                    int chosen_signal = 0;
                    double chosen_conf = 0;
                    double chosen_p = 0.5;

                    if (!long_pass && !short_pass) {
                        combiner_flat_choices++;
                        break;
                    } else if (long_pass && !short_pass) {
                        chosen_signal = 1;
                        chosen_conf = long_conf;
                        chosen_p = long_p;
                        combiner_long_choices++;
                    } else if (short_pass && !long_pass) {
                        chosen_signal = -1;
                        chosen_conf = short_conf;
                        chosen_p = short_p;
                        combiner_short_choices++;
                    } else {
                        // Both pass - use combiner
                        combiner_conflicts++;
                        double long_score = 0, short_score = 0;

                        if (DUAL_COMBINER == "confidence") {
                            long_score = long_conf;
                            short_score = short_conf;
                        } else if (DUAL_COMBINER == "probability") {
                            long_score = long_p - long_model.threshold_long;
                            short_score = short_model.threshold_short - short_p;
                        } else { // edge
                            long_score = long_model.model_excess_return_pct * long_conf;
                            short_score = short_model.model_excess_return_pct * short_conf;
                        }

                        double edge_gap = abs(long_score - short_score);
                        combiner_edge_gap_sum += edge_gap;

                        if (edge_gap < MIN_EDGE_GAP) {
                            combiner_flat_choices++;
                            break;
                        }

                        if (long_score > short_score) {
                            chosen_signal = 1;
                            chosen_conf = long_conf;
                            chosen_p = long_p;
                            combiner_long_choices++;
                        } else {
                            chosen_signal = -1;
                            chosen_conf = short_conf;
                            chosen_p = short_p;
                            combiner_short_choices++;
                        }
                    }

                    // Position state machine (no hedging)
                    if (broker.open_positions.size() > 0) {
                        int existing_dir = broker.open_positions[0].direction;
                        if (existing_dir == chosen_signal) {
                            broker.stats.ignored_opposite_signals++;
                            break;
                        } else {
                            if (!ALLOW_CLOSE_AND_REVERSE) {
                                broker.stats.ignored_opposite_signals++;
                                break;
                            }
                            broker.close_position(broker.open_positions[0], i, current_close_price, "REVERSE_EXIT");
                            broker.open_positions.clear();
                        }
                    }

                    // Check hedge violation (should never happen with above logic)
                    if (broker.open_positions.size() > 0) {
                        hedge_violations++;
                        break;
                    }

                    // Build trade intent
                    broker.stats.orders_attempted++;

                    double rr = DEFAULT_RR;
                    if (CONFIDENCE_RR) {
                        rr = MIN_RR + chosen_conf * (MAX_RR - MIN_RR);
                        rr = max(MIN_RR, min(MAX_RR, rr));
                    }

                    double risk_pct = RISK_PER_TRADE_PCT;
                    double dd_mult = broker.get_drawdown_risk_multiplier();
                    if (dd_mult <= 0.0) {
                        broker.stats.rejected_orders++;
                        broker.stats.drawdown_throttle_rejections++;
                        broker.stats.drawdown_throttle_events++;
                        break;
                    }
                    if (dd_mult < 1.0) broker.stats.drawdown_throttle_events++;
                    risk_pct *= dd_mult;

                    double risk_dollars = broker.account.equity * risk_pct;
                    double dollars_per_point = lot_size * meta.gold_oz_per_lot;
                    double stop_distance = risk_dollars / dollars_per_point;
                    if (stop_distance < 0.01) break;
                    double tp_distance = stop_distance * rr;
                    if (tp_distance < 0.01) break;

                    double final_lot = lot_size;
                    if (AUTO_SIZE_BY_RISK) {
                        double lot_by_risk = risk_dollars / (stop_distance * meta.gold_oz_per_lot);
                        double lot_by_margin = broker.account.free_margin * broker.account.leverage / (current_close_price * meta.gold_oz_per_lot);
                        final_lot = min({lot_by_risk, lot_by_margin, MAX_LOT_SIZE});
                    }
                    final_lot = max(final_lot, MIN_LOT_SIZE);
                    if (final_lot < MIN_LOT_SIZE) break;

                    TradeIntent intent;
                    intent.config_name = "dual_specialist_combined";
                    intent.direction = chosen_signal;
                    intent.probability = chosen_p;
                    intent.confidence = chosen_conf;
                    intent.requested_lot_size = lot_size;
                    intent.final_lot_size = final_lot;
                    intent.entry_price = current_close_price;
                    intent.rr = rr;
                    intent.risk_dollars = risk_dollars;
                    intent.risk_pct = risk_pct;
                    intent.kelly_raw = 0;
                    intent.kelly_risk_pct = 0;
                    intent.drawdown_risk_multiplier = dd_mult;
                    intent.max_holding_bars = MAX_HOLDING_BARS;
                    intent.trailing_stop_enabled = TRAILING_STOP_ENABLED;
                    intent.kelly_fallback_used = false;

                    if (chosen_signal == 1) {
                        intent.stop_loss_price = current_close_price - stop_distance;
                        intent.take_profit_price = current_close_price + tp_distance;
                    } else {
                        intent.stop_loss_price = current_close_price + stop_distance;
                        intent.take_profit_price = current_close_price - tp_distance;
                    }

                    broker.try_open_position(intent, i, current_close_price);
                } while (false);

                broker.equity_curve.push_back(broker.make_equity_row("dual_specialist_combined", i, current_close_price));
            }

            if (!broker.account.is_failed && !broker.open_positions.empty()) {
                broker.end_of_test(oos_n - 1, oos_closes.back());
            }

            broker.finalize_stats();

            double combined_return = (broker.account.balance - broker.account.starting_balance) / broker.account.starting_balance;

            // Compute baselines
            print_progress("\n[COMPUTING BASELINES]", true);

            double baseline_always_long = 0.0;
            {
                BrokerSimulator bl(STARTING_BALANCE, LEVERAGE, MAX_LOSS_PCT, meta.commission_per_lot, meta.gold_oz_per_lot);
                for (int i = 0; i < oos_n; ++i) {
                    bl.tick(i, oos_closes[i]);
                    if (bl.account.is_failed) break;
                    if (bl.open_positions.empty() && !bl.account.is_failed) {
                        TradeIntent ti;
                        ti.config_name = "baseline_always_long";
                        ti.direction = 1;
                        ti.probability = 0.5;
                        ti.confidence = 0.0;
                        ti.requested_lot_size = lot_size;
                        ti.final_lot_size = lot_size;
                        ti.entry_price = oos_closes[i];
                        ti.rr = DEFAULT_RR;
                        ti.risk_dollars = bl.account.equity * RISK_PER_TRADE_PCT;
                        ti.risk_pct = RISK_PER_TRADE_PCT;
                        ti.kelly_raw = 0; ti.kelly_risk_pct = 0;
                        ti.drawdown_risk_multiplier = 1.0;
                        ti.max_holding_bars = MAX_HOLDING_BARS;
                        ti.trailing_stop_enabled = TRAILING_STOP_ENABLED;
                        ti.kelly_fallback_used = false;
                        double stop_dist = (ti.risk_dollars / (lot_size * meta.gold_oz_per_lot));
                        ti.stop_loss_price = oos_closes[i] - stop_dist;
                        ti.take_profit_price = oos_closes[i] + stop_dist * DEFAULT_RR;
                        bl.try_open_position(ti, i, oos_closes[i]);
                    }
                }
                if (!bl.open_positions.empty()) bl.end_of_test(oos_n - 1, oos_closes.back());
                bl.finalize_stats();
                baseline_always_long = (bl.account.balance - bl.account.starting_balance) / bl.account.starting_balance;
            }

            double baseline_always_short = 0.0;
            {
                BrokerSimulator bs(STARTING_BALANCE, LEVERAGE, MAX_LOSS_PCT, meta.commission_per_lot, meta.gold_oz_per_lot);
                for (int i = 0; i < oos_n; ++i) {
                    bs.tick(i, oos_closes[i]);
                    if (bs.account.is_failed) break;
                    if (bs.open_positions.empty() && !bs.account.is_failed) {
                        TradeIntent ti;
                        ti.config_name = "baseline_always_short";
                        ti.direction = -1;
                        ti.probability = 0.5;
                        ti.confidence = 0.0;
                        ti.requested_lot_size = lot_size;
                        ti.final_lot_size = lot_size;
                        ti.entry_price = oos_closes[i];
                        ti.rr = DEFAULT_RR;
                        ti.risk_dollars = bs.account.equity * RISK_PER_TRADE_PCT;
                        ti.risk_pct = RISK_PER_TRADE_PCT;
                        ti.kelly_raw = 0; ti.kelly_risk_pct = 0;
                        ti.drawdown_risk_multiplier = 1.0;
                        ti.max_holding_bars = MAX_HOLDING_BARS;
                        ti.trailing_stop_enabled = TRAILING_STOP_ENABLED;
                        ti.kelly_fallback_used = false;
                        double stop_dist = (ti.risk_dollars / (lot_size * meta.gold_oz_per_lot));
                        ti.stop_loss_price = oos_closes[i] + stop_dist;
                        ti.take_profit_price = oos_closes[i] - stop_dist * DEFAULT_RR;
                        bs.try_open_position(ti, i, oos_closes[i]);
                    }
                }
                if (!bs.open_positions.empty()) bs.end_of_test(oos_n - 1, oos_closes.back());
                bs.finalize_stats();
                baseline_always_short = (bs.account.balance - bs.account.starting_balance) / bs.account.starting_balance;
            }

            double baseline_flat = 0.0;

            double best_baseline_return = max({baseline_always_long, baseline_always_short, baseline_flat});
            string best_baseline_name = "flat";
            if (baseline_always_long == best_baseline_return) best_baseline_name = "always_long";
            else if (baseline_always_short == best_baseline_return) best_baseline_name = "always_short";

            double combined_excess = combined_return - best_baseline_return;

            print_progress("  Baseline always-long: " + to_string(baseline_always_long * 100).substr(0, 6) + "%", true);
            print_progress("  Baseline always-short: " + to_string(baseline_always_short * 100).substr(0, 6) + "%", true);
            print_progress("  Best baseline: " + best_baseline_name + " (" + to_string(best_baseline_return * 100).substr(0, 6) + "%)", true);

            // Compute edge verdict
            string risk_verdict = broker.account.is_failed ? "RISK_STOPPED_OUT" : "PASS_RISK";
            string model_edge_verdict = "NO_TRADE";
            if (risk_verdict == "PASS_RISK" && hedge_violations == 0 && broker.stats.total_trades > 0 && combined_excess > 0) {
                model_edge_verdict = "EDGE_CONFIRMED";
            } else if (risk_verdict == "PASS_RISK" && broker.stats.total_trades > 0) {
                model_edge_verdict = "BASELINE_DOMINATED";
            } else if (risk_verdict != "PASS_RISK") {
                model_edge_verdict = "RISK_STOPPED_OUT";
            }

            print_progress("\n[DUAL-SPECIALIST RESULTS]", true);
            print_progress("  Balance: $" + to_string((int)broker.account.starting_balance) + " -> $" + to_string((int)broker.account.balance), true);
            print_progress("  Combined return: " + to_string(combined_return * 100).substr(0, 6) + "%", true);
            print_progress("  Combined excess: " + to_string(combined_excess * 100).substr(0, 6) + "%", true);
            print_progress("  Edge verdict: " + model_edge_verdict, true);
            print_progress("  Trades: " + to_string(broker.stats.total_trades) + " | Long: " + to_string(broker.stats.long_trades) + " | Short: " + to_string(broker.stats.short_trades), true);
            print_progress("  Combiner: long=" + to_string(combiner_long_choices) + " short=" + to_string(combiner_short_choices) + " flat=" + to_string(combiner_flat_choices) + " conflicts=" + to_string(combiner_conflicts), true);
            print_progress("  Hedge violations: " + to_string(hedge_violations), true);

            // Write dedicated dual specialist results CSV
            string dual_results_path = "runs/hydra_dual_specialist_results.csv";
            ofstream dual_results(dual_results_path);

            // Build header
            vector<string> header = {
                "config", "direction_mode", "starting_balance", "ending_balance", "net_profit", "return_pct",
                "baseline_always_long_return_pct", "baseline_always_short_return_pct",
                "baseline_random_50_50_return_pct", "baseline_flat_return_pct",
                "best_baseline_name", "best_baseline_return_pct", "combined_excess_pct",
                "model_edge_verdict", "risk_verdict", "total_trades", "long_trades", "short_trades",
                "win_rate", "profit_factor", "max_drawdown_pct",
                "tp_hits", "sl_hits", "trailing_stop_hits", "time_stop_hits",
                "hedge_violations", "combiner_long_choices", "combiner_short_choices",
                "combiner_flat_choices", "combiner_conflicts",
                "loaded_long_model_path", "loaded_short_model_path",
                "long_specialist_model_type", "short_specialist_model_type",
                "long_specialist_edge_verdict", "short_specialist_edge_verdict",
                "long_model_excess_pct", "short_model_excess_pct",
                "long_model_validated", "short_model_validated"
            };

            // Build row
            vector<string> row = {
                "dual_specialist_combined",
                "dual-specialist",
                to_string(broker.account.starting_balance),
                to_string(broker.account.balance),
                to_string(broker.account.balance - broker.account.starting_balance),
                to_string(combined_return),
                to_string(baseline_always_long),
                to_string(baseline_always_short),
                "0.0",
                to_string(baseline_flat),
                best_baseline_name,
                to_string(best_baseline_return),
                to_string(combined_excess),
                model_edge_verdict,
                risk_verdict,
                to_string(broker.stats.total_trades),
                to_string(broker.stats.long_trades),
                to_string(broker.stats.short_trades),
                to_string(broker.stats.win_rate),
                to_string(broker.stats.profit_factor),
                to_string(broker.account.max_drawdown_pct),
                to_string(broker.stats.tp_hits),
                to_string(broker.stats.sl_hits),
                to_string(broker.stats.trailing_stop_hits),
                to_string(broker.stats.time_stop_hits),
                to_string(hedge_violations),
                to_string(combiner_long_choices),
                to_string(combiner_short_choices),
                to_string(combiner_flat_choices),
                to_string(combiner_conflicts),
                LOAD_LONG_MODEL_PATH,
                LOAD_SHORT_MODEL_PATH,
                long_model.model_type,
                short_model.model_type,
                long_model.model_edge_verdict,
                short_model.model_edge_verdict,
                to_string(long_model.model_excess_return_pct),
                to_string(short_model.model_excess_return_pct),
                (long_validated ? "true" : "false"),
                (short_validated ? "true" : "false")
            };

            // Self-check
            if (header.size() != row.size()) {
                cerr << "FATAL: Dual results CSV schema mismatch: header=" << header.size()
                     << " row=" << row.size() << endl;
                return 1;
            }

            // Write header
            for (size_t i = 0; i < header.size(); ++i) {
                dual_results << header[i];
                if (i + 1 < header.size()) dual_results << ",";
            }
            dual_results << "\n";

            // Write row
            for (size_t i = 0; i < row.size(); ++i) {
                dual_results << row[i];
                if (i + 1 < row.size()) dual_results << ",";
            }
            dual_results << "\n";
            dual_results.close();

            print_progress("  Dual results: " + dual_results_path, true);

            results_csv.close();

            // Write trades
            for (const auto& t : broker.trade_ledger) {
                trades_csv << t.config << "," << t.trade_id << "," << t.entry_bar << "," << t.exit_bar << ","
                           << t.direction << "," << fixed << setprecision(4) << t.lot_size << ","
                           << setprecision(2) << t.entry_price << "," << t.exit_price << ","
                           << t.stop_loss_price << "," << t.take_profit_price << "," << t.trailing_stop_price << ","
                           << t.gross_pnl << "," << t.commission << "," << t.net_pnl << ","
                           << t.required_margin << "," << t.balance_after << "," << t.equity_after << ","
                           << t.holding_bars << "," << t.exit_reason << ","
                           << setprecision(4) << t.confidence << "," << t.rr << ","
                           << t.kelly_raw << "," << t.kelly_risk_pct << "," << t.final_risk_pct << ","
                           << t.lot_by_risk << "," << t.lot_by_margin << "," << t.final_lot_size << ","
                           << setprecision(2) << t.risk_dollars << "," << setprecision(4) << t.drawdown_risk_multiplier << ","
                           << (t.kelly_fallback_used ? "true" : "false") << ","
                           << setprecision(6) << t.signal_probability << "," << t.regime_at_entry << ","
                           << (t.was_counter_regime ? "true" : "false") << "\n";
            }
            trades_csv.close();

            // Write equity
            for (const auto& erow : broker.equity_curve) {
                equity_csv << erow.config << "," << erow.bar_index << ","
                           << fixed << setprecision(2) << erow.close_price << ","
                           << erow.balance << "," << erow.equity << ","
                           << erow.unrealized_pnl << "," << erow.realized_pnl << ","
                           << erow.used_margin << "," << erow.free_margin << ","
                           << erow.open_positions << "," << erow.drawdown_dollars << ","
                           << setprecision(4) << erow.drawdown_pct << ","
                           << (erow.account_failed ? "true" : "false") << ","
                           << erow.fail_reason << "\n";
            }
            equity_csv.close();

            print_progress("\n================================================================================", true);
            print_progress("DUAL-SPECIALIST DONE | Elapsed: " + to_string((int)elapsed_seconds()) + "s", true);
            print_progress("================================================================================", true);

            PROGRESS_JSONL.close();
            RUNTIME_LOG.close();
            PARTIAL_CSV.close();
            return 0;
        }

        // Row split
        double bars_per_year = (double)meta.rows / 11.4;
        int train_rows = (int)(TRAIN_YEARS * bars_per_year);
        int oos_rows = (int)(OOS_YEARS * bars_per_year);

        if (train_rows + horizon + oos_rows > meta.rows) {
            oos_rows = meta.rows - train_rows - horizon;
        }
        if (oos_rows < 100) {
            cerr << "FATAL: Not enough data for OOS. train_rows=" << train_rows
                 << " oos_rows=" << oos_rows << " total=" << meta.rows << endl;
            return 1;
        }

        int train_start = 0;
        int train_end = train_rows;
        int oos_start = train_end + horizon;
        int oos_end = min(oos_start + oos_rows, meta.rows);

        print_progress("  Train: rows [0.." + to_string(train_end) + "] (" + to_string(train_end) + " rows, ~" + to_string(TRAIN_YEARS) + " years)", true);
        print_progress("  Embargo: " + to_string(horizon) + " bars", true);
        print_progress("  OOS: rows [" + to_string(oos_start) + ".." + to_string(oos_end) + "] (" + to_string(oos_end - oos_start) + " rows, ~" + to_string(OOS_YEARS) + " year)", true);
        print_progress("  Starting balance: $" + to_string((int)STARTING_BALANCE), true);
        print_progress("  Leverage: " + to_string((int)LEVERAGE) + "x", true);
        print_progress("  Max loss: " + to_string((int)(MAX_LOSS_PCT * 100)) + "%", true);
        print_progress("  Stopout equity: $" + to_string((int)(STARTING_BALANCE * (1.0 - MAX_LOSS_PCT))), true);
        print_progress("  Lot size: " + to_string(lot_size), true);
        print_progress("  Max open positions: " + to_string(MAX_OPEN_POSITIONS), true);
        print_progress("  Max holding bars: " + to_string(MAX_HOLDING_BARS), true);
        print_progress("  Default R:R: " + to_string(DEFAULT_RR), true);
        print_progress("  Confidence RR: " + string(CONFIDENCE_RR ? "yes" : "no") + " [" + to_string(MIN_RR) + " - " + to_string(MAX_RR) + "]", true);
        print_progress("  Risk per trade: " + to_string(RISK_PER_TRADE_PCT * 100).substr(0, 5) + "%", true);
        print_progress("  Kelly sizing: " + string(KELLY_SIZING ? "yes" : "no") + " (frac=" + to_string(KELLY_FRACTION) + " min_samples=" + to_string(KELLY_MIN_SAMPLES) + ")", true);
        print_progress("  Drawdown throttle: " + string(DRAWDOWN_RISK_THROTTLE ? "yes" : "no"), true);
        print_progress("  Trailing stop: " + string(TRAILING_STOP_ENABLED ? "yes" : "no") + " (activate=" + to_string(TRAIL_ACTIVATE_R) + "R dist=" + to_string(TRAIL_DISTANCE_R) + "R BE=" + to_string(MOVE_SL_TO_BREAKEVEN_AT_R) + "R)", true);

        if (STARTING_BALANCE <= 20000 && lot_size >= 1.0) {
            print_progress("  [WARN] For $" + to_string((int)STARTING_BALANCE) + " balance, 1.0 lot XAUUSD may be high risk. Backtest still uses provided lot size.", true);
        }

        // Build configs
        vector<pair<double, double>> standard_thresholds_oos = {
            {0.52, 0.48}, {0.55, 0.45}, {0.60, 0.40}, {0.65, 0.35}
        };

        vector<Config> oos_configs;
        // (name, model_type, n_features, n_epochs, lr, l2)
        struct OosConfigDef {
            string name; string model; int n_feat; int epochs; double lr; double l2;
        };
        vector<OosConfigDef> oos_base_configs = {
            {"oos_logistic_top100", "logistic", 100, 50, 0.01, 0.001},
            {"oos_logistic_top200", "logistic", 200, 50, 0.01, 0.001},
            {"oos_logistic_lr001_l2_01_top100", "logistic", 100, 100, 0.001, 0.01},
            {"oos_logistic_lr0005_l2_1_top100", "logistic", 100, 100, 0.0005, 0.1},
            {"oos_logistic_lr0001_l2_10_top100", "logistic", 100, 200, 0.0001, 1.0},
            {"oos_ftrl_top100", "ftrl", 100, 1, 0.1, 1.0},
            {"oos_pa_top100", "passive_aggressive", 100, 10, 0.01, 1.0},
            {"oos_rank_top100", "rank_ensemble", 100, 0, 0.01, 0.001},
            {"oos_rank_top200", "rank_ensemble", 200, 0, 0.01, 0.001},
        };

        for (const auto& def : oos_base_configs) {
            if (DISABLE_RANK_ENSEMBLE && def.model == "rank_ensemble") continue;
            if (!ONLY_MODEL.empty() && def.model != ONLY_MODEL) continue;

            Config cfg;
            cfg.name = def.name;
            cfg.model_type = def.model;
            cfg.n_features = def.n_feat;
            cfg.n_epochs = def.epochs;
            cfg.learning_rate = def.lr;
            cfg.l2_lambda = def.l2;
            cfg.n_stumps = 0;
            cfg.thresholds = standard_thresholds_oos;
            cfg.ftrl_alpha = 0.1;
            cfg.ftrl_beta = 1.0;
            cfg.ftrl_l1 = 1.0;
            cfg.ftrl_l2 = 1.0;
            cfg.pa_C = 1.0;
            cfg.feature_score_method = feature_score_method;
            cfg.regime_aware = regime_aware;
            cfg.objective = objective;
            oos_configs.push_back(cfg);
        }

        print_progress("\n[OOS CONFIGS] " + to_string(oos_configs.size()) + " configs", true);

        // Indices
        vector<int> train_indices, oos_indices;
        train_indices.reserve(train_end);
        oos_indices.reserve(oos_end - oos_start);
        for (int i = train_start; i < train_end; ++i) train_indices.push_back(i);
        for (int i = oos_start; i < oos_end; ++i) oos_indices.push_back(i);

        // OOS close prices
        vector<double> oos_closes;
        oos_closes.reserve(oos_indices.size());
        for (int idx : oos_indices) oos_closes.push_back(close[idx]);

        // Output files
        ofstream equity_csv(EQUITY_OUTPUT_PATH, ios::trunc);
        equity_csv << "config,bar_index,close,balance,equity,unrealized_pnl,realized_pnl,"
                   << "used_margin,free_margin,open_positions,drawdown_dollars,drawdown_pct,"
                   << "account_failed,fail_reason\n";

        ofstream results_csv(output_csv_path, ios::trunc);
        results_csv << "config,model_type,auc,"
                    << "starting_balance,ending_balance,net_profit,return_pct,"
                    << "leverage,max_loss_pct,stopout_equity,max_drawdown_dollars,max_drawdown_pct,"
                    << "used_margin_max,free_margin_min,margin_call,stopped_out,risk_verdict,"
                    << "total_trades,wins,losses,win_rate,avg_win,avg_loss,profit_factor,"
                    << "avg_holding_bars,tp_hits,sl_hits,trailing_stop_hits,time_stop_hits,"
                    << "rejected_orders,rejected_insufficient_margin,rejected_missing_bracket,"
                    << "rejected_kelly_too_small,rejected_kelly_negative,rejected_drawdown_throttle,"
                    << "rejected_kelly_invalid_sample,rejected_max_trades,rejected_max_open_positions,"
                    << "orders_attempted,orders_opened,"
                    << "avg_rr,avg_confidence,"
                    << "kelly_enabled,kelly_mode,kelly_fraction,kelly_raw,kelly_risk_pct,avg_kelly_risk_pct,"
                    << "kelly_fallback_trades,"
                    << "avg_lot_size,max_lot_size_used,min_lot_size_used,drawdown_throttle_events,"
                    << "proba_min,proba_max,proba_mean,proba_std,"
                    << "proba_p01,proba_p05,proba_p50,proba_p95,proba_p99,"
                    << "count_long_signals,count_short_signals,count_flat_signals,"
                    << "saturated_low_count,saturated_high_count,constant_proba,signal_verdict,"
                    << "best_baseline_return_pct,best_baseline_name,model_excess_return_pct,"
                    << "beats_best_baseline,model_edge_verdict,"
                    << "normalize_features,calibration_enabled,"
                    << "raw_proba_std,calibrated_proba_std,"
                    << "regime_filter_enabled,bullish_bars,bearish_bars,flat_regime_bars,"
                    << "allow_long,allow_short,allow_close_and_reverse,strict_regime_direction,"
                    << "long_trades,short_trades,long_win_rate,short_win_rate,"
                    << "long_net_pnl,short_net_pnl,reverse_exits,ignored_opposite_signals,"
                    << "blocked_long_signals,blocked_short_signals,blocked_counter_regime_signals,"
                    << "direction_mode,specialist_role,saved_model_path,loaded_long_model_path,loaded_short_model_path,"
                    << "hedge_violations\n";

        ofstream trades_csv(TRADES_OUTPUT_PATH, ios::trunc);
        trades_csv << "config,trade_id,entry_bar,exit_bar,direction,lot_size,entry_price,exit_price,"
                   << "stop_loss_price,take_profit_price,trailing_stop_price,gross_pnl,commission,"
                   << "net_pnl,required_margin,balance_after,equity_after,holding_bars,exit_reason,"
                   << "confidence,rr,kelly_raw,kelly_risk_pct,final_risk_pct,"
                   << "lot_by_risk,lot_by_margin,final_lot_size,risk_dollars,drawdown_risk_multiplier,"
                   << "kelly_fallback_used,signal_probability,regime_at_entry,was_counter_regime\n";

        // Track best specialist candidate
        struct SpecialistCandidate {
            string config_name;
            string model_type;
            double excess_return = -1e9;
            vector<double> weights;
            double bias = 0;
            vector<int> feature_indices;
            vector<double> norm_means;
            vector<double> norm_stds;
            double threshold_long = 0.5;
            double threshold_short = 0.5;
            double train_auc = 0;
            double oos_auc = 0;
            string signal_verdict;
            string edge_verdict;
            double baseline_return = 0;
        };
        SpecialistCandidate best_specialist;

        for (size_t ci = 0; ci < oos_configs.size(); ++ci) {
            const auto& config = oos_configs[ci];
            print_progress("\n[OOS CONFIG " + to_string(ci + 1) + "/" + to_string(oos_configs.size()) + "] " + config.name, true);

            emit_progress_event("{\"event\":\"config_start\",\"config_index\":" + to_string(ci + 1) +
                ",\"config_total\":" + to_string(oos_configs.size()) +
                ",\"config\":\"" + json_escape(config.name) + "\"" +
                ",\"model_type\":\"" + json_escape(config.model_type) + "\"" +
                ",\"n_features\":" + to_string(config.n_features) +
                ",\"objective\":\"" + json_escape(config.objective) + "\"}");

            // Train fold to get thresholds
            auto fold_result = train_fold(
                config, 1, X, y, next_bar_delta,
                train_indices, oos_indices,
                lot_size, commission_per_lot, meta.gold_oz_per_lot
            );

            // Re-train to get OOS probabilities
            string score_method = config.feature_score_method.empty() ? "pearson" : config.feature_score_method;

            vector<vector<float>> X_train_oos;
            vector<int> y_train_oos;
            X_train_oos.reserve(train_indices.size());
            y_train_oos.reserve(train_indices.size());
            for (int idx : train_indices) {
                X_train_oos.push_back(X[idx]);
                y_train_oos.push_back(y[idx]);
            }

            vector<FeatureScore> feature_scores = score_all_features(X_train_oos, y_train_oos, score_method);
            vector<int> top_features = rank_features_by_score(feature_scores, config.n_features);

            auto select_features = [&](const vector<vector<float>>& data) {
                vector<vector<float>> selected;
                selected.reserve(data.size());
                for (const auto& row : data) {
                    vector<float> new_row;
                    new_row.reserve(top_features.size());
                    for (int idx : top_features) {
                        new_row.push_back(row[idx]);
                    }
                    selected.push_back(new_row);
                }
                return selected;
            };

            vector<vector<float>> X_train_sel = select_features(X_train_oos);
            vector<vector<float>> X_oos_raw;
            X_oos_raw.reserve(oos_indices.size());
            for (int idx : oos_indices) X_oos_raw.push_back(X[idx]);
            vector<vector<float>> X_oos_sel = select_features(X_oos_raw);

            // Feature normalization (train stats only)
            FeatureNormalizer normalizer;
            if (NORMALIZE_FEATURES) {
                normalizer.fit(X_train_sel);
                normalizer.transform(X_train_sel);
                normalizer.transform(X_oos_sel);
            }

            vector<double> y_proba_oos;
            vector<double> y_proba_train_raw;
            double raw_proba_std = 0.0;
            double calibrated_proba_std = 0.0;
            bool calibration_applied = false;

            // Keep trained model for potential saving
            unique_ptr<LogisticRegression> trained_logistic;
            unique_ptr<PassiveAggressive> trained_pa;

            if (config.model_type == "logistic" || config.model_type == "conservative") {
                trained_logistic = make_unique<LogisticRegression>(config.n_features, config.learning_rate, config.l2_lambda, config.n_epochs);
                trained_logistic->fit(X_train_sel, y_train_oos);
                if (trained_logistic->training_failed) {
                    y_proba_oos.resize(oos_indices.size(), 0.5);
                    y_proba_train_raw.resize(train_indices.size(), 0.5);
                } else {
                    y_proba_oos = trained_logistic->predict_proba(X_oos_sel);
                    y_proba_train_raw = trained_logistic->predict_proba(X_train_sel);
                }
            } else if (config.model_type == "ftrl") {
                FTRLLogistic model(config.n_features, config.ftrl_alpha, config.ftrl_beta, config.ftrl_l1, config.ftrl_l2);
                model.fit(X_train_sel, y_train_oos);
                y_proba_oos = model.predict_proba(X_oos_sel);
                y_proba_train_raw = model.predict_proba(X_train_sel);
            } else if (config.model_type == "passive_aggressive") {
                trained_pa = make_unique<PassiveAggressive>(config.n_features, config.pa_C, config.n_epochs);
                trained_pa->fit(X_train_sel, y_train_oos);
                y_proba_oos = trained_pa->predict_proba(X_oos_sel);
                y_proba_train_raw = trained_pa->predict_proba(X_train_sel);
            } else if (config.model_type == "rank_ensemble") {
                RankEnsemble model;
                model.fit(X_train_sel, y_train_oos, feature_scores, top_features);
                y_proba_oos = model.predict_proba(X_oos_sel);
                y_proba_train_raw = model.predict_proba(X_train_sel);
            } else if (config.model_type == "stump_ensemble") {
                StumpEnsemble model(config.n_stumps > 0 ? config.n_stumps : 50);
                model.fit(X_train_sel, y_train_oos);
                y_proba_oos = model.predict_proba(X_oos_sel);
                y_proba_train_raw = model.predict_proba(X_train_sel);
            }

            // Compute raw proba std before calibration
            {
                double sum_p = 0.0, sum_p2 = 0.0;
                int np = y_proba_oos.size();
                for (int i = 0; i < np; ++i) { sum_p += y_proba_oos[i]; sum_p2 += y_proba_oos[i] * y_proba_oos[i]; }
                double mean_p = sum_p / np;
                raw_proba_std = sqrt(max(0.0, sum_p2 / np - mean_p * mean_p));
            }

            // Platt calibration (fit on train, transform OOS)
            PlattCalibrator calibrator;
            if (CALIBRATE_PROBA && !y_proba_train_raw.empty()) {
                vector<double> y_proba_oos_backup = y_proba_oos;
                calibrator.fit(y_proba_train_raw, y_train_oos);
                if (calibrator.fitted) {
                    vector<double> calibrated = calibrator.transform(y_proba_oos);
                    // Compute calibrated std
                    double cs = 0.0, cs2 = 0.0;
                    int np = calibrated.size();
                    for (int i = 0; i < np; ++i) { cs += calibrated[i]; cs2 += calibrated[i] * calibrated[i]; }
                    double cm = cs / np;
                    double cstd = sqrt(max(0.0, cs2 / np - cm * cm));
                    // Only use calibration if it doesn't kill the signal
                    if (cstd >= raw_proba_std * 0.1 && cstd >= MIN_PROBA_STD) {
                        y_proba_oos = calibrated;
                        calibration_applied = true;
                        calibrated_proba_std = cstd;
                    } else {
                        calibrated_proba_std = cstd;
                    }
                }
            }

            // Compute final proba std (use what's in y_proba_oos now)
            if (!calibration_applied) {
                calibrated_proba_std = raw_proba_std;
            }

            // Sanitize probabilities
            for (size_t i = 0; i < y_proba_oos.size(); ++i) {
                if (!isfinite(y_proba_oos[i])) y_proba_oos[i] = 0.5;
                y_proba_oos[i] = max(1e-6, min(1.0 - 1e-6, y_proba_oos[i]));
            }

            double th_long = fold_result.threshold_long;
            double th_short = fold_result.threshold_short;

            // Compute Kelly estimate from training trades (simulate)
            KellyEstimate train_kelly;
            if (KELLY_SIZING) {
                // Simulate training trades for Kelly estimation
                int train_n = (int)train_indices.size();
                vector<double> train_proba;
                if (config.model_type == "logistic" || config.model_type == "conservative") {
                    LogisticRegression model_k(config.n_features, config.learning_rate, config.l2_lambda, config.n_epochs);
                    model_k.fit(X_train_sel, y_train_oos);
                    train_proba = model_k.predict_proba(X_train_sel);
                } else if (config.model_type == "ftrl") {
                    FTRLLogistic model_k(config.n_features, config.ftrl_alpha, config.ftrl_beta, config.ftrl_l1, config.ftrl_l2);
                    model_k.fit(X_train_sel, y_train_oos);
                    train_proba = model_k.predict_proba(X_train_sel);
                } else if (config.model_type == "passive_aggressive") {
                    PassiveAggressive model_k(config.n_features, config.pa_C, config.n_epochs);
                    model_k.fit(X_train_sel, y_train_oos);
                    train_proba = model_k.predict_proba(X_train_sel);
                } else if (config.model_type == "rank_ensemble") {
                    RankEnsemble model_k;
                    model_k.fit(X_train_sel, y_train_oos, feature_scores, top_features);
                    train_proba = model_k.predict_proba(X_train_sel);
                } else if (config.model_type == "stump_ensemble") {
                    StumpEnsemble model_k(config.n_stumps > 0 ? config.n_stumps : 50);
                    model_k.fit(X_train_sel, y_train_oos);
                    train_proba = model_k.predict_proba(X_train_sel);
                }

                // Compute win/loss stats from training signals
                int wins_k = 0, losses_k = 0;
                double sum_win_k = 0.0, sum_loss_k = 0.0;
                for (int ti = 0; ti < train_n - 1; ++ti) {
                    int sig = 0;
                    if (train_proba[ti] >= th_long) sig = 1;
                    else if (train_proba[ti] <= th_short) sig = -1;
                    if (sig == 0) continue;

                    double pnl_k = sig * next_bar_delta[train_indices[ti]] * meta.gold_oz_per_lot * lot_size
                                   - lot_size * commission_per_lot;
                    if (pnl_k > 0) { wins_k++; sum_win_k += pnl_k; }
                    else { losses_k++; sum_loss_k += pnl_k; }
                }

                train_kelly.sample_count = wins_k + losses_k;
                if (train_kelly.sample_count >= KELLY_MIN_SAMPLES && losses_k > 0) {
                    train_kelly.win_rate = (double)wins_k / train_kelly.sample_count;
                    train_kelly.avg_win = (wins_k > 0) ? (sum_win_k / wins_k) : 0.0;
                    train_kelly.avg_loss = (losses_k > 0) ? (sum_loss_k / losses_k) : 0.0;
                    if (train_kelly.avg_loss < 0) {
                        train_kelly.payoff_ratio = train_kelly.avg_win / abs(train_kelly.avg_loss);
                        if (train_kelly.payoff_ratio > 0) {
                            train_kelly.kelly_raw = train_kelly.win_rate - ((1.0 - train_kelly.win_rate) / train_kelly.payoff_ratio);
                            train_kelly.kelly_raw = max(0.0, min(1.0, train_kelly.kelly_raw));
                            train_kelly.valid = (train_kelly.kelly_raw > 0);
                        }
                    }
                }

                print_progress("  Kelly estimate: win_rate=" + to_string(train_kelly.win_rate).substr(0, 5) +
                    " payoff=" + to_string(train_kelly.payoff_ratio).substr(0, 5) +
                    " raw=" + to_string(train_kelly.kelly_raw).substr(0, 6) +
                    " samples=" + to_string(train_kelly.sample_count) +
                    " valid=" + string(train_kelly.valid ? "yes" : "no"), true);
            }

            // Run broker simulation on OOS
            auto broker_start_time = high_resolution_clock::now();
            BrokerSimulator broker(STARTING_BALANCE, LEVERAGE, MAX_LOSS_PCT, commission_per_lot, meta.gold_oz_per_lot);
            broker.kelly_est = train_kelly;
            int oos_n = (int)oos_indices.size();

            // Reserve space for equity curve
            broker.equity_curve.reserve(oos_n);

            // Probability diagnostics
            ProbaDiagnostics diag = compute_proba_diagnostics(y_proba_oos, oos_n, th_long, th_short, fold_result.auc);

            print_progress("  Proba: min=" + to_string(diag.proba_min).substr(0, 7) +
                " max=" + to_string(diag.proba_max).substr(0, 7) +
                " mean=" + to_string(diag.proba_mean).substr(0, 7) +
                " std=" + to_string(diag.proba_std).substr(0, 7), true);
            print_progress("  Proba percentiles: p01=" + to_string(diag.proba_p01).substr(0, 6) +
                " p05=" + to_string(diag.proba_p05).substr(0, 6) +
                " p50=" + to_string(diag.proba_p50).substr(0, 6) +
                " p95=" + to_string(diag.proba_p95).substr(0, 6) +
                " p99=" + to_string(diag.proba_p99).substr(0, 6), true);
            print_progress("  Signals: long=" + to_string(diag.count_long) +
                " short=" + to_string(diag.count_short) +
                " flat=" + to_string(diag.count_flat) +
                " | saturated_low=" + to_string(diag.saturated_low) +
                " saturated_high=" + to_string(diag.saturated_high), true);
            print_progress("  Signal verdict: " + diag.signal_verdict +
                " | confidence_cap=" + to_string(diag.confidence_cap).substr(0, 5) +
                " | AUC=" + to_string(fold_result.auc).substr(0, 6), true);

            emit_progress_event("{\"event\":\"signal_sanity\",\"config\":\"" + json_escape(config.name) + "\"" +
                ",\"auc\":" + to_string(fold_result.auc) +
                ",\"proba_min\":" + to_string(diag.proba_min) +
                ",\"proba_max\":" + to_string(diag.proba_max) +
                ",\"proba_mean\":" + to_string(diag.proba_mean) +
                ",\"proba_std\":" + to_string(diag.proba_std) +
                ",\"proba_p01\":" + to_string(diag.proba_p01) +
                ",\"proba_p50\":" + to_string(diag.proba_p50) +
                ",\"proba_p99\":" + to_string(diag.proba_p99) +
                ",\"long_signals\":" + to_string(diag.count_long) +
                ",\"short_signals\":" + to_string(diag.count_short) +
                ",\"flat_signals\":" + to_string(diag.count_flat) +
                ",\"saturated_low_count\":" + to_string(diag.saturated_low) +
                ",\"saturated_high_count\":" + to_string(diag.saturated_high) +
                ",\"signal_verdict\":\"" + json_escape(diag.signal_verdict) + "\"}");

            // Signal sanity gate: skip broker if failed
            bool signal_passed = (diag.signal_verdict == "PASS_SIGNAL_SANITY");

            if (!signal_passed) {
                print_progress("  SKIPPING broker sim: " + diag.signal_verdict, true);
            }

            // Regime filter
            vector<int> oos_regime(oos_n, 0);
            int bullish_bars = 0, bearish_bars = 0, flat_regime_bars = 0;
            if (REGIME_FILTER && signal_passed) {
                RegimeInfo regime_info = compute_regime(close, oos_start, oos_end, 288);
                oos_regime = regime_info.regime;
                for (int r : oos_regime) {
                    if (r > 0) bullish_bars++;
                    else if (r < 0) bearish_bars++;
                    else flat_regime_bars++;
                }
                print_progress("  Regime: bullish=" + to_string(bullish_bars) +
                    " bearish=" + to_string(bearish_bars) +
                    " flat=" + to_string(flat_regime_bars), true);
            }

            print_progress("  Normalize=" + string(NORMALIZE_FEATURES ? "yes" : "no") +
                " | Calibrate=" + string(calibration_applied ? "yes" : "no") +
                " | raw_std=" + to_string(raw_proba_std).substr(0, 7) +
                " | cal_std=" + to_string(calibrated_proba_std).substr(0, 7), true);

            // Run broker simulation (only if signal passes)
            if (signal_passed) {
                for (int i = 0; i < oos_n; ++i) {
                    double current_close_price = oos_closes[i];
                    broker.tick(i, current_close_price);

                    if (broker.account.is_failed) {
                        broker.equity_curve.push_back(broker.make_equity_row(config.name, i, current_close_price));
                        break;
                    }

                    do {
                        double p = y_proba_oos[i];
                        int raw_signal = 0;
                        if (p >= th_long) raw_signal = 1;
                        else if (p <= th_short) raw_signal = -1;
                        if (raw_signal == 0) break;

                        // Calibrated confidence with cap
                        double confidence = abs(p - 0.5) * 2.0;
                        confidence = max(0.0, min(1.0, confidence));
                        confidence = min(confidence, diag.confidence_cap);

                        if (confidence < MIN_CONFIDENCE) break;

                        int current_regime = 0;
                        bool counter_regime = false;
                        if (REGIME_FILTER && i < (int)oos_regime.size()) {
                            current_regime = oos_regime[i];
                            if (current_regime > 0 && raw_signal == -1) counter_regime = true;
                            if (current_regime < 0 && raw_signal == 1) counter_regime = true;
                            if (STRICT_REGIME_DIRECTION && counter_regime) {
                                broker.stats.blocked_counter_regime_signals++;
                                break;
                            }
                        }

                        // Direction permissions
                        int signal = raw_signal;
                        if (signal == 1 && !ALLOW_LONG) {
                            broker.stats.blocked_long_signals++;
                            break;
                        }
                        if (signal == -1 && !ALLOW_SHORT) {
                            broker.stats.blocked_short_signals++;
                            break;
                        }

                        // Direction-specific confidence thresholds
                        if (signal == 1 && confidence < MIN_LONG_CONFIDENCE) break;
                        if (signal == -1 && confidence < MIN_SHORT_CONFIDENCE) break;

                        // Position state machine: check for existing position
                        if (broker.open_positions.size() > 0) {
                            int existing_dir = broker.open_positions[0].direction;
                            if (existing_dir == signal) {
                                // same direction: ignore signal
                                broker.stats.ignored_opposite_signals++;
                                break;
                            } else {
                                // opposite direction
                                if (!ALLOW_CLOSE_AND_REVERSE) {
                                    broker.stats.ignored_opposite_signals++;
                                    break;
                                }
                                // close existing with REVERSE_EXIT
                                broker.close_position(broker.open_positions[0], i, current_close_price, "REVERSE_EXIT");
                                broker.open_positions.clear();
                                // fall through to open opposite position
                            }
                        }

                        // MAX_OPEN_POSITIONS check (should never trigger with MAX_OPEN_POSITIONS=1 after clear)
                        if ((int)broker.open_positions.size() >= MAX_OPEN_POSITIONS) {
                            broker.stats.rejected_orders++;
                            broker.stats.max_open_pos_rejections++;
                            break;
                        }

                        // MAX_TRADES_PER_CONFIG check
                        if (MAX_TRADES_PER_CONFIG > 0 && broker.stats.total_trades >= MAX_TRADES_PER_CONFIG) {
                            broker.stats.rejected_orders++;
                            broker.stats.max_trades_rejections++;
                            break;
                        }

                        broker.stats.orders_attempted++;

                        double rr = DEFAULT_RR;
                        if (CONFIDENCE_RR) {
                            rr = MIN_RR + confidence * (MAX_RR - MIN_RR);
                            rr = max(MIN_RR, min(MAX_RR, rr));
                        }

                        double risk_pct = RISK_PER_TRADE_PCT;
                        double kelly_raw_val = 0.0;
                        double kelly_risk_pct_val = 0.0;
                        bool kelly_fallback = false;

                        if (KELLY_SIZING && KELLY_MODE != "off") {
                            if ((int)broker.trade_ledger.size() >= KELLY_MIN_SAMPLES) {
                                broker.compute_kelly_from_trades(KELLY_LOOKBACK_TRADES);
                                if (broker.kelly_est.valid && broker.kelly_est.kelly_raw > 0) {
                                    kelly_raw_val = broker.kelly_est.kelly_raw;
                                    kelly_risk_pct_val = kelly_raw_val * KELLY_FRACTION;
                                    risk_pct = max(MIN_RISK_PER_TRADE_PCT, min(MAX_RISK_PER_TRADE_PCT, kelly_risk_pct_val));
                                } else if (broker.kelly_est.kelly_raw <= 0 && broker.kelly_est.valid) {
                                    if (KELLY_MODE == "strict") { broker.stats.rejected_orders++; broker.stats.kelly_negative_rejections++; break; }
                                    else { risk_pct = MIN_RISK_PER_TRADE_PCT; kelly_fallback = true; broker.stats.kelly_fallback_trades++; }
                                } else {
                                    if (KELLY_MODE == "strict") { broker.stats.rejected_orders++; broker.stats.kelly_invalid_sample_rejections++; break; }
                                    else { risk_pct = MIN_RISK_PER_TRADE_PCT; kelly_fallback = true; broker.stats.kelly_fallback_trades++; }
                                }
                            } else if (train_kelly.valid && train_kelly.kelly_raw > 0) {
                                kelly_raw_val = train_kelly.kelly_raw;
                                kelly_risk_pct_val = kelly_raw_val * KELLY_FRACTION;
                                risk_pct = max(MIN_RISK_PER_TRADE_PCT, min(MAX_RISK_PER_TRADE_PCT, kelly_risk_pct_val));
                            } else if (train_kelly.sample_count >= KELLY_MIN_SAMPLES && !train_kelly.valid) {
                                if (KELLY_MODE == "strict") { broker.stats.rejected_orders++; broker.stats.kelly_negative_rejections++; break; }
                                else { risk_pct = MIN_RISK_PER_TRADE_PCT; kelly_fallback = true; broker.stats.kelly_fallback_trades++; }
                            } else {
                                risk_pct = MIN_RISK_PER_TRADE_PCT; kelly_fallback = true; broker.stats.kelly_fallback_trades++;
                            }
                        }

                        double dd_mult = broker.get_drawdown_risk_multiplier();
                        if (dd_mult <= 0.0) { broker.stats.rejected_orders++; broker.stats.drawdown_throttle_rejections++; broker.stats.drawdown_throttle_events++; break; }
                        if (dd_mult < 1.0) broker.stats.drawdown_throttle_events++;
                        risk_pct *= dd_mult;

                        double risk_dollars = broker.account.equity * risk_pct;
                        double dollars_per_point = lot_size * meta.gold_oz_per_lot;
                        double stop_distance = risk_dollars / dollars_per_point;
                        if (stop_distance < 0.01) break;
                        double tp_distance = stop_distance * rr;
                        if (tp_distance < 0.01) break;

                        double lot_by_risk = risk_dollars / (stop_distance * meta.gold_oz_per_lot);
                        double lot_by_margin = broker.account.free_margin * broker.account.leverage /
                                               (current_close_price * meta.gold_oz_per_lot);
                        double final_lot = min({lot_size, lot_by_risk, lot_by_margin, MAX_LOT_SIZE});
                        if (AUTO_SIZE_BY_RISK) final_lot = min({lot_by_risk, lot_by_margin, MAX_LOT_SIZE});
                        final_lot = max(final_lot, MIN_LOT_SIZE);
                        if (final_lot < MIN_LOT_SIZE) { broker.stats.rejected_orders++; broker.stats.kelly_too_small_rejections++; break; }
                        if (final_lot > MAX_LOT_SIZE) final_lot = MAX_LOT_SIZE;

                        TradeIntent intent;
                        intent.config_name = config.name;
                        intent.direction = signal;
                        intent.probability = p;
                        intent.confidence = confidence;
                        intent.requested_lot_size = lot_size;
                        intent.final_lot_size = final_lot;
                        intent.entry_price = current_close_price;
                        intent.rr = rr;
                        intent.risk_dollars = risk_dollars;
                        intent.risk_pct = risk_pct;
                        intent.kelly_raw = kelly_raw_val;
                        intent.kelly_risk_pct = kelly_risk_pct_val;
                        intent.drawdown_risk_multiplier = dd_mult;
                        intent.max_holding_bars = MAX_HOLDING_BARS;
                        intent.trailing_stop_enabled = TRAILING_STOP_ENABLED;
                        intent.kelly_fallback_used = kelly_fallback;

                        if (signal == 1) {
                            intent.stop_loss_price = current_close_price - stop_distance;
                            intent.take_profit_price = current_close_price + tp_distance;
                        } else {
                            intent.stop_loss_price = current_close_price + stop_distance;
                            intent.take_profit_price = current_close_price - tp_distance;
                        }

                        bool opened = broker.try_open_position(intent, i, current_close_price);
                        if (opened && broker.open_positions.size() > 0) {
                            broker.open_positions.back().regime_at_entry = current_regime;
                            broker.open_positions.back().was_counter_regime = counter_regime;
                        }
                    } while (false);

                    broker.equity_curve.push_back(broker.make_equity_row(config.name, i, current_close_price));
                }

                if (!broker.account.is_failed && !broker.open_positions.empty()) {
                    broker.end_of_test(oos_n - 1, oos_closes.back());
                }
            }

            broker.finalize_stats();

            auto broker_end_time = high_resolution_clock::now();
            double broker_ms = duration_cast<milliseconds>(broker_end_time - broker_start_time).count();

            string risk_verdict = "PASS_RISK";
            if (broker.account.is_failed) {
                if (broker.account.fail_reason == "MARGIN_CALL") risk_verdict = "MARGIN_CALL";
                else risk_verdict = "RISK_STOPPED_OUT";
            }

            emit_progress_event("{\"event\":\"broker_result\",\"config\":\"" + json_escape(config.name) + "\"" +
                ",\"ending_balance\":" + to_string(broker.account.balance) +
                ",\"return_pct\":" + to_string((broker.account.balance - broker.account.starting_balance) / broker.account.starting_balance) +
                ",\"max_drawdown_pct\":" + to_string(broker.account.max_drawdown_pct) +
                ",\"total_trades\":" + to_string(broker.stats.total_trades) +
                ",\"win_rate\":" + to_string(broker.stats.win_rate) +
                ",\"profit_factor\":" + to_string(broker.stats.profit_factor) +
                ",\"tp_hits\":" + to_string(broker.stats.tp_hits) +
                ",\"sl_hits\":" + to_string(broker.stats.sl_hits) +
                ",\"trailing_stop_hits\":" + to_string(broker.stats.trailing_stop_hits) +
                ",\"time_stop_hits\":" + to_string(broker.stats.time_stop_hits) +
                ",\"risk_verdict\":\"" + json_escape(risk_verdict) + "\"}");

            // Run baselines
            vector<int> always_long_sig(oos_n, 1);
            vector<int> always_short_sig(oos_n, -1);
            vector<int> random_sig(oos_n, 0);
            vector<int> inverted_sig(oos_n, 0);
            vector<int> flat_sig(oos_n, 0);

            // Random 50/50 with fixed seed
            {
                uint32_t seed = 42;
                for (int j = 0; j < oos_n; ++j) {
                    seed = seed * 1103515245 + 12345;
                    random_sig[j] = ((seed >> 16) & 1) ? 1 : -1;
                }
            }

            // Inverted model signals
            for (int j = 0; j < oos_n; ++j) {
                double p = y_proba_oos[j];
                if (p >= th_long) inverted_sig[j] = -1;
                else if (p <= th_short) inverted_sig[j] = 1;
            }

            BaselineResult bl_long = run_baseline_broker("baseline_always_long", always_long_sig, oos_closes, lot_size, commission_per_lot, meta.gold_oz_per_lot, TRAILING_STOP_ENABLED);
            BaselineResult bl_short = run_baseline_broker("baseline_always_short", always_short_sig, oos_closes, lot_size, commission_per_lot, meta.gold_oz_per_lot, TRAILING_STOP_ENABLED);
            BaselineResult bl_random = run_baseline_broker("baseline_random_50_50", random_sig, oos_closes, lot_size, commission_per_lot, meta.gold_oz_per_lot, TRAILING_STOP_ENABLED);
            BaselineResult bl_inverted = run_baseline_broker("baseline_inverted_" + config.name, inverted_sig, oos_closes, lot_size, commission_per_lot, meta.gold_oz_per_lot, TRAILING_STOP_ENABLED);
            BaselineResult bl_flat = {"baseline_flat_no_trade", 0.0, 0, 0.0, 0.0};

            vector<BaselineResult> baselines = {bl_long, bl_short, bl_random, bl_inverted, bl_flat};

            // Find best baseline (direction-mode aware)
            BaselineResult best_baseline = bl_flat;
            if (DIRECTION_MODE == "long-only") {
                // Long specialist must beat always-long
                best_baseline = bl_long;
            } else if (DIRECTION_MODE == "short-only") {
                // Short specialist must beat always-short
                best_baseline = bl_short;
            } else {
                // both or dual-specialist: beat best of all baselines
                for (const auto& bl : baselines) {
                    if (bl.return_pct > best_baseline.return_pct) best_baseline = bl;
                }
            }

            double model_return = (broker.account.balance - broker.account.starting_balance) / broker.account.starting_balance;
            double model_excess = model_return - best_baseline.return_pct;
            bool beats_baseline = (model_return > best_baseline.return_pct);

            string model_edge_verdict = "NO_TRADE";
            if (!signal_passed) {
                model_edge_verdict = "SIGNAL_INVALID";
            } else if (broker.stats.total_trades == 0) {
                model_edge_verdict = "NO_TRADE";
            } else if (beats_baseline && signal_passed) {
                model_edge_verdict = "EDGE_CONFIRMED";
            } else {
                model_edge_verdict = "BASELINE_DOMINATED";
            }

            print_progress("  Baselines: long=" + to_string(bl_long.return_pct * 100).substr(0, 6) + "%" +
                " short=" + to_string(bl_short.return_pct * 100).substr(0, 6) + "%" +
                " random=" + to_string(bl_random.return_pct * 100).substr(0, 6) + "%" +
                " inverted=" + to_string(bl_inverted.return_pct * 100).substr(0, 6) + "%", true);
            print_progress("  Best baseline: " + best_baseline.name + " (" + to_string(best_baseline.return_pct * 100).substr(0, 6) + "%)", true);
            print_progress("  Model return: " + to_string(model_return * 100).substr(0, 6) + "% | Excess: " + to_string(model_excess * 100).substr(0, 6) + "% | Edge: " + model_edge_verdict, true);

            // Update best specialist candidate (only save-supported models)
            bool is_edge_confirmed = (model_edge_verdict == "EDGE_CONFIRMED");
            bool is_candidate = SAVE_BEST_CANDIDATE && (signal_passed && risk_verdict == "PASS_RISK");

            // Check if model type is save-supported
            bool save_supported = (config.model_type == "logistic" || config.model_type == "conservative" || config.model_type == "passive_aggressive");

            if (SAVE_MODELS && (is_edge_confirmed || is_candidate)) {
                if (!save_supported) {
                    print_progress("  SKIP_UNSUPPORTED_SAVE_CANDIDATE model_type=" + config.model_type + " config=" + config.name, true);
                } else {
                    // Only update if better excess or first candidate
                    bool should_update = (model_excess > best_specialist.excess_return);
                    // If no EDGE_CONFIRMED yet and this is first candidate, accept it
                    if (best_specialist.config_name.empty() && is_candidate) should_update = true;
                    // EDGE_CONFIRMED always beats candidate
                    if (is_edge_confirmed && best_specialist.edge_verdict != "EDGE_CONFIRMED") should_update = true;

                    if (should_update) {
                        best_specialist.config_name = config.name;
                        best_specialist.model_type = config.model_type;
                        best_specialist.excess_return = model_excess;
                        best_specialist.feature_indices = top_features;
                        best_specialist.norm_means = normalizer.means;
                        best_specialist.norm_stds = normalizer.stds;
                        best_specialist.threshold_long = th_long;
                        best_specialist.threshold_short = th_short;
                        best_specialist.train_auc = fold_result.auc;
                        best_specialist.oos_auc = fold_result.auc; // TODO: compute OOS AUC
                        best_specialist.signal_verdict = diag.signal_verdict;
                        best_specialist.edge_verdict = model_edge_verdict;
                        best_specialist.baseline_return = best_baseline.return_pct;

                        // Copy model weights
                        if (trained_logistic) {
                            best_specialist.weights = trained_logistic->weights;
                            best_specialist.bias = trained_logistic->bias;
                        } else if (trained_pa) {
                            best_specialist.weights = trained_pa->weights;
                            best_specialist.bias = trained_pa->bias;
                        }
                    }
                }
            }

            emit_progress_event("{\"event\":\"baseline_eval\",\"config\":\"" + json_escape(config.name) + "\"" +
                ",\"baseline_always_long\":" + to_string(bl_long.return_pct) +
                ",\"baseline_always_short\":" + to_string(bl_short.return_pct) +
                ",\"baseline_random\":" + to_string(bl_random.return_pct) +
                ",\"baseline_inverted\":" + to_string(bl_inverted.return_pct) +
                ",\"best_baseline_name\":\"" + json_escape(best_baseline.name) + "\"" +
                ",\"best_baseline_return_pct\":" + to_string(best_baseline.return_pct) + "}");

            // No-trailing ablation
            BaselineResult no_trail_result = {"", 0.0, 0, 0.0, 0.0};
            if (NO_TRAILING_ABLATION && signal_passed && TRAILING_STOP_ENABLED) {
                // Re-run model signals without trailing stop
                vector<int> model_sigs(oos_n, 0);
                for (int j = 0; j < oos_n; ++j) {
                    double p = y_proba_oos[j];
                    if (p >= th_long) model_sigs[j] = 1;
                    else if (p <= th_short) model_sigs[j] = -1;
                }
                no_trail_result = run_baseline_broker("no_trailing_" + config.name, model_sigs, oos_closes, lot_size, commission_per_lot, meta.gold_oz_per_lot, false);
                print_progress("  No-trailing ablation: " + to_string(no_trail_result.return_pct * 100).substr(0, 6) + "% (" + to_string(no_trail_result.total_trades) + " trades)", true);
            }

            // Write equity curve
            for (const auto& erow : broker.equity_curve) {
                equity_csv << erow.config << "," << erow.bar_index << ","
                           << fixed << setprecision(2) << erow.close_price << ","
                           << erow.balance << "," << erow.equity << ","
                           << erow.unrealized_pnl << "," << erow.realized_pnl << ","
                           << erow.used_margin << "," << erow.free_margin << ","
                           << erow.open_positions << "," << erow.drawdown_dollars << ","
                           << setprecision(4) << erow.drawdown_pct << ","
                           << (erow.account_failed ? "true" : "false") << ","
                           << erow.fail_reason << "\n";
            }
            equity_csv.flush();

            // Write trade ledger
            for (const auto& t : broker.trade_ledger) {
                trades_csv << t.config << "," << t.trade_id << "," << t.entry_bar << "," << t.exit_bar << ","
                           << t.direction << "," << fixed << setprecision(4) << t.lot_size << ","
                           << setprecision(2) << t.entry_price << "," << t.exit_price << ","
                           << t.stop_loss_price << "," << t.take_profit_price << "," << t.trailing_stop_price << ","
                           << t.gross_pnl << "," << t.commission << "," << t.net_pnl << ","
                           << t.required_margin << "," << t.balance_after << "," << t.equity_after << ","
                           << t.holding_bars << "," << t.exit_reason << ","
                           << setprecision(4) << t.confidence << "," << t.rr << ","
                           << t.kelly_raw << "," << t.kelly_risk_pct << "," << t.final_risk_pct << ","
                           << t.lot_by_risk << "," << t.lot_by_margin << "," << t.final_lot_size << ","
                           << setprecision(2) << t.risk_dollars << "," << setprecision(4) << t.drawdown_risk_multiplier << ","
                           << (t.kelly_fallback_used ? "true" : "false") << ","
                           << setprecision(6) << t.signal_probability << "," << t.regime_at_entry << ","
                           << (t.was_counter_regime ? "true" : "false") << "\n";
            }
            trades_csv.flush();

            // Determine risk verdict (already computed above for event)
            // string risk_verdict already set

            // Write results row
            results_csv << config.name << "," << config.model_type << ","
                        << fixed << setprecision(4) << fold_result.auc << ","
                        << setprecision(2)
                        << broker.account.starting_balance << "," << broker.account.balance << ","
                        << (broker.account.balance - broker.account.starting_balance) << ","
                        << setprecision(4) << model_return << ","
                        << setprecision(0) << broker.account.leverage << ","
                        << setprecision(4) << MAX_LOSS_PCT << ","
                        << setprecision(2) << broker.account.stopout_equity << ","
                        << broker.account.max_drawdown_dollars << ","
                        << setprecision(4) << broker.account.max_drawdown_pct << ","
                        << setprecision(2) << broker.account.max_used_margin << ","
                        << broker.account.min_free_margin << ","
                        << (broker.account.fail_reason == "MARGIN_CALL" ? "true" : "false") << ","
                        << (broker.account.is_failed ? "true" : "false") << ","
                        << risk_verdict << ","
                        << broker.stats.total_trades << "," << broker.stats.wins << "," << broker.stats.losses << ","
                        << setprecision(4) << broker.stats.win_rate << ","
                        << setprecision(2) << broker.stats.avg_win << "," << broker.stats.avg_loss << ","
                        << setprecision(4) << broker.stats.profit_factor << ","
                        << setprecision(1) << broker.stats.avg_holding_bars << ","
                        << broker.stats.tp_hits << "," << broker.stats.sl_hits << ","
                        << broker.stats.trailing_stop_hits << "," << broker.stats.time_stop_hits << ","
                        << broker.stats.rejected_orders << ","
                        << broker.stats.margin_rejections << ","
                        << broker.stats.no_sl_rejections << ","
                        << broker.stats.kelly_too_small_rejections << ","
                        << broker.stats.kelly_negative_rejections << ","
                        << broker.stats.drawdown_throttle_rejections << ","
                        << broker.stats.kelly_invalid_sample_rejections << ","
                        << broker.stats.max_trades_rejections << ","
                        << broker.stats.max_open_pos_rejections << ","
                        << broker.stats.orders_attempted << ","
                        << broker.stats.orders_opened << ","
                        << setprecision(4) << broker.stats.avg_rr << ","
                        << broker.stats.avg_confidence << ","
                        << (KELLY_SIZING ? "true" : "false") << ","
                        << KELLY_MODE << ","
                        << KELLY_FRACTION << ","
                        << train_kelly.kelly_raw << ","
                        << (train_kelly.kelly_raw * KELLY_FRACTION) << ","
                        << broker.stats.avg_kelly_risk_pct << ","
                        << broker.stats.kelly_fallback_trades << ","
                        << broker.stats.avg_lot_size << ","
                        << broker.stats.max_lot_size_used << ","
                        << broker.stats.min_lot_size_used << ","
                        << broker.stats.drawdown_throttle_events << ","
                        << setprecision(6) << diag.proba_min << "," << diag.proba_max << ","
                        << diag.proba_mean << "," << diag.proba_std << ","
                        << diag.proba_p01 << "," << diag.proba_p05 << "," << diag.proba_p50 << ","
                        << diag.proba_p95 << "," << diag.proba_p99 << ","
                        << diag.count_long << "," << diag.count_short << "," << diag.count_flat << ","
                        << diag.saturated_low << "," << diag.saturated_high << ","
                        << (diag.constant_proba ? "true" : "false") << ","
                        << diag.signal_verdict << ","
                        << setprecision(4) << best_baseline.return_pct << ","
                        << best_baseline.name << ","
                        << model_excess << ","
                        << (beats_baseline ? "true" : "false") << ","
                        << model_edge_verdict << ","
                        << (NORMALIZE_FEATURES ? "true" : "false") << ","
                        << (calibration_applied ? "true" : "false") << ","
                        << setprecision(6) << raw_proba_std << "," << calibrated_proba_std << ","
                        << (REGIME_FILTER ? "true" : "false") << ","
                        << bullish_bars << "," << bearish_bars << "," << flat_regime_bars << ","
                        << (ALLOW_LONG ? "true" : "false") << "," << (ALLOW_SHORT ? "true" : "false") << ","
                        << (ALLOW_CLOSE_AND_REVERSE ? "true" : "false") << "," << (STRICT_REGIME_DIRECTION ? "true" : "false") << ","
                        << broker.stats.long_trades << "," << broker.stats.short_trades << ","
                        << setprecision(4) << (broker.stats.long_trades > 0 ? (double)broker.stats.long_wins / broker.stats.long_trades : 0.0) << ","
                        << (broker.stats.short_trades > 0 ? (double)broker.stats.short_wins / broker.stats.short_trades : 0.0) << ","
                        << setprecision(2) << broker.stats.long_net_pnl << "," << broker.stats.short_net_pnl << ","
                        << broker.stats.reverse_exits << "," << broker.stats.ignored_opposite_signals << ","
                        << broker.stats.blocked_long_signals << "," << broker.stats.blocked_short_signals << ","
                        << broker.stats.blocked_counter_regime_signals << ","
                        << "\"" << DIRECTION_MODE << "\",\"\",\"\",\"\",\"\","
                        << "0\n";
            results_csv.flush();

            // Write baseline rows
            for (const auto& bl : baselines) {
                if (bl.name.empty()) continue;
                results_csv << bl.name << ",baseline,"
                            << "0.0000,"
                            << setprecision(2) << STARTING_BALANCE << "," << (STARTING_BALANCE * (1.0 + bl.return_pct)) << ","
                            << (STARTING_BALANCE * bl.return_pct) << ","
                            << setprecision(4) << bl.return_pct << ","
                            << setprecision(0) << LEVERAGE << ","
                            << setprecision(4) << MAX_LOSS_PCT << ","
                            << setprecision(2) << (STARTING_BALANCE * (1.0 - MAX_LOSS_PCT)) << ","
                            << "0.00," << setprecision(4) << bl.max_drawdown_pct << ","
                            << "0.00,0.00,false,false,BASELINE,"
                            << bl.total_trades << ",0,0,0.0000,0.00,0.00,"
                            << setprecision(4) << bl.profit_factor << ","
                            << "0.0,0,0,0,0,0,0,0,0,0,0,0,0,0,"
                            << "0.0000,0.0000,false," << KELLY_MODE << ","
                            << KELLY_FRACTION << ",0.0000,0.0000,0.0000,0,"
                            << "0.0000,0.0000,0.0000,0,"
                            << "0.000000,0.000000,0.000000,0.000000,"
                            << "0.000000,0.000000,0.000000,0.000000,0.000000,"
                            << "0,0,0,0,0,false,BASELINE,"
                            << "0.0000,,0.0000,false,BASELINE,"
                            << "false,false,0.000000,0.000000,false,0,0,0,"
                            << "false,false,false,false,0,0,0.0000,0.0000,0.00,0.00,0,0,0,0,0,"
                            << "\"" << DIRECTION_MODE << "\",\"\",\"\",\"\",\"\",0\n";
            }
            results_csv.flush();

            // Console output
            print_progress("  Broker sim: " + to_string((int)broker_ms) + " ms for " + to_string(oos_n) + " bars", true);
            print_progress("  Balance: $" + to_string((int)broker.account.starting_balance) + " -> $" + to_string((int)broker.account.balance), true);
            print_progress("  Trades: " + to_string(broker.stats.total_trades) + " | WR: " + to_string((int)(broker.stats.win_rate * 100)) + "% | PF: " + to_string(broker.stats.profit_factor).substr(0, 5), true);
            print_progress("  Long: " + to_string(broker.stats.long_trades) + " (" + to_string((int)((broker.stats.long_trades > 0 ? (double)broker.stats.long_wins / broker.stats.long_trades : 0.0) * 100)) + "% WR) | Short: " + to_string(broker.stats.short_trades) + " (" + to_string((int)((broker.stats.short_trades > 0 ? (double)broker.stats.short_wins / broker.stats.short_trades : 0.0) * 100)) + "% WR)", true);
            print_progress("  MaxDD: $" + to_string((int)broker.account.max_drawdown_dollars) + " (" + to_string((int)(broker.account.max_drawdown_pct * 100)) + "%)", true);
            print_progress("  TP/SL/Trail/Time: " + to_string(broker.stats.tp_hits) + "/" + to_string(broker.stats.sl_hits) + "/" + to_string(broker.stats.trailing_stop_hits) + "/" + to_string(broker.stats.time_stop_hits), true);
            print_progress("  Rejected: blocked_long=" + to_string(broker.stats.blocked_long_signals) + " blocked_short=" + to_string(broker.stats.blocked_short_signals) + " counter_regime=" + to_string(broker.stats.blocked_counter_regime_signals) + " ignored_opposite=" + to_string(broker.stats.ignored_opposite_signals), true);
            print_progress("  Risk verdict: " + risk_verdict + " | Edge: " + model_edge_verdict, true);
            if (broker.account.is_failed) {
                print_progress("  Fail reason: " + broker.account.fail_reason, true);
            }

            log_event("oos_config_done", "\"config\":\"" + config.name + "\",\"verdict\":\"" + risk_verdict + "\",\"edge\":\"" + model_edge_verdict + "\",\"trades\":" + to_string(broker.stats.total_trades) + ",\"broker_ms\":" + to_string((int)broker_ms));

            emit_progress_event("{\"event\":\"config_done\",\"config\":\"" + json_escape(config.name) + "\"" +
                ",\"risk_verdict\":\"" + json_escape(risk_verdict) + "\"" +
                ",\"signal_verdict\":\"" + json_escape(diag.signal_verdict) + "\"" +
                ",\"model_edge_verdict\":\"" + json_escape(model_edge_verdict) + "\"" +
                ",\"return_pct\":" + to_string(model_return) +
                ",\"model_excess_return_pct\":" + to_string(model_excess) +
                ",\"total_trades\":" + to_string(broker.stats.total_trades) + "}");
        }

        equity_csv.close();
        results_csv.close();
        trades_csv.close();

        print_progress("\n[OOS RESULTS WRITTEN]", true);
        print_progress("  Results: " + output_csv_path, true);
        print_progress("  Equity curves: " + EQUITY_OUTPUT_PATH, true);
        print_progress("  Trade ledger: " + TRADES_OUTPUT_PATH, true);

        // Save best specialist if found
        if (SAVE_MODELS && !best_specialist.config_name.empty()) {
            string model_path;
            if (DIRECTION_MODE == "long-only" && !LONG_MODEL_PATH.empty()) {
                model_path = LONG_MODEL_PATH;
            } else if (DIRECTION_MODE == "short-only" && !SHORT_MODEL_PATH.empty()) {
                model_path = SHORT_MODEL_PATH;
            }

            if (!model_path.empty()) {
                // Create model dir
                size_t slash_pos = model_path.rfind('/');
                if (slash_pos != string::npos) {
                    string dir = model_path.substr(0, slash_pos);
                    system(("mkdir -p " + dir).c_str());
                }

                // Save weights
                bool weight_save_success = false;
                if (best_specialist.model_type == "logistic" || best_specialist.model_type == "conservative") {
                    ofstream wf(model_path);
                    if (wf.is_open()) {
                        wf << best_specialist.bias << "\n";
                        for (double w : best_specialist.weights) wf << w << "\n";
                        wf.close();
                        weight_save_success = true;
                        print_progress("\n[MODEL SAVED]", true);
                        print_progress("  Config: " + best_specialist.config_name, true);
                        print_progress("  Path: " + model_path, true);
                        print_progress("  Excess: " + to_string(best_specialist.excess_return * 100).substr(0, 6) + "%", true);
                    } else {
                        print_progress("\n[MODEL SAVE FAILED]", true);
                        print_progress("  Failed to open: " + model_path, true);
                    }
                } else if (best_specialist.model_type == "passive_aggressive") {
                    ofstream wf(model_path);
                    if (wf.is_open()) {
                        wf << best_specialist.bias << "\n";
                        for (double w : best_specialist.weights) wf << w << "\n";
                        wf.close();
                        weight_save_success = true;
                        print_progress("\n[MODEL SAVED]", true);
                        print_progress("  Config: " + best_specialist.config_name, true);
                        print_progress("  Path: " + model_path, true);
                        print_progress("  Excess: " + to_string(best_specialist.excess_return * 100).substr(0, 6) + "%", true);
                    } else {
                        print_progress("\n[MODEL SAVE FAILED]", true);
                        print_progress("  Failed to open: " + model_path, true);
                    }
                } else {
                    print_progress("\n[MODEL SAVE SKIPPED]", true);
                    print_progress("  Model type not supported: " + best_specialist.model_type, true);
                }

                // Delete stale metadata if weight save failed
                string meta_path = model_path + ".meta.json";
                if (!weight_save_success) {
                    if (ifstream(meta_path)) {
                        system(("rm -f " + meta_path).c_str());
                        print_progress("  Deleted stale metadata: " + meta_path, true);
                    }
                } else {
                    // Save metadata only if weights saved successfully
                    ModelMetadata meta;
                    meta.model_name = best_specialist.config_name;
                    meta.model_type = best_specialist.model_type;
                    meta.direction_mode = DIRECTION_MODE;
                    meta.n_features = best_specialist.weights.size();
                    meta.selected_feature_indices = best_specialist.feature_indices;
                    meta.normalization_means = best_specialist.norm_means;
                    meta.normalization_stds = best_specialist.norm_stds;
                    meta.threshold_long = best_specialist.threshold_long;
                    meta.threshold_short = best_specialist.threshold_short;
                    meta.train_years = TRAIN_YEARS;
                    meta.oos_years = OOS_YEARS;
                    meta.horizon = horizon;
                    meta.train_auc = best_specialist.train_auc;
                    meta.oos_auc = best_specialist.oos_auc;
                    meta.signal_verdict = best_specialist.signal_verdict;
                    meta.model_edge_verdict = best_specialist.edge_verdict;
                    meta.baseline_return_pct = best_specialist.baseline_return;
                    meta.model_excess_return_pct = best_specialist.excess_return;
                    meta.created_at = get_timestamp();

                    if (save_model_metadata(meta_path, meta)) {
                        print_progress("  Metadata: " + meta_path, true);
                    }
                }
            }
        } else if (SAVE_MODELS) {
            print_progress("\n[NO EDGE_CONFIRMED SPECIALIST FOUND]", true);
        }

        print_progress("\n================================================================================", true);
        print_progress("BROKER OOS BACKTEST DONE | Elapsed: " + to_string((int)elapsed_seconds()) + "s | Configs: " + to_string(oos_configs.size()), true);
        print_progress("================================================================================", true);

        emit_progress_event("{\"event\":\"run_done\",\"elapsed_seconds\":" + to_string((int)elapsed_seconds()) +
            ",\"configs\":" + to_string(oos_configs.size()) +
            ",\"results_csv\":\"" + json_escape(output_csv_path) + "\"" +
            ",\"trades_csv\":\"" + json_escape(TRADES_OUTPUT_PATH) + "\"" +
            ",\"equity_csv\":\"" + json_escape(EQUITY_OUTPUT_PATH) + "\"}");

        PROGRESS_JSONL.close();
        RUNTIME_LOG.close();
        PARTIAL_CSV.close();
        return 0;
    }

    // Configs
    vector<Config> configs;

    vector<pair<double, double>> standard_thresholds = {
        {0.52, 0.48}, {0.55, 0.45}, {0.60, 0.40}, {0.65, 0.35}
    };

    vector<pair<double, double>> conservative_thresholds = {
        {0.60, 0.40}, {0.65, 0.35}, {0.70, 0.30}
    };

    if (MATH_SWEEP) {
        // Math sweep: grid over scoring/model/features/objective
        print_progress("\n[MATH SWEEP MODE]", true);
        print_progress("Max configs: " + to_string(MAX_SWEEP_CONFIGS), true);
        print_progress("Max runtime: " + to_string(MAX_SWEEP_RUNTIME_MINUTES) + " min", true);

        if (DISABLE_RANK_ENSEMBLE) {
            print_progress("DISABLE_RANK_ENSEMBLE active: skipping rank_ensemble configs", true);
        }
        if (!ONLY_MODEL.empty()) {
            print_progress("ONLY_MODEL active: only generating " + ONLY_MODEL + " configs", true);
        }

        vector<string> score_methods = {"pearson", "spearman", "composite"};
        vector<string> model_types = {"rank_ensemble", "ftrl", "passive_aggressive", "logistic"};
        vector<int> top_features = {50, 100, 200};
        vector<string> objectives_sweep;

        // If --objective passed, use it as the sole sweep objective (requirement 10)
        if (!objective.empty()) {
            objectives_sweep = {objective};
        } else {
            objectives_sweep = {"sharpe", "utility"};
        }

        vector<bool> regime_opts = {false, true};

        int config_count = 0;
        for (const auto& score_m : score_methods) {
            for (const auto& model_t : model_types) {
                // Filter by DISABLE_RANK_ENSEMBLE
                if (DISABLE_RANK_ENSEMBLE && model_t == "rank_ensemble") continue;

                // Filter by ONLY_MODEL
                if (!ONLY_MODEL.empty() && model_t != ONLY_MODEL) continue;

                for (int n_feat : top_features) {
                    for (const auto& obj : objectives_sweep) {
                        for (bool regime : regime_opts) {
                            if (config_count >= MAX_SWEEP_CONFIGS) break;

                            string name = "math_" + score_m + "_" + model_t + "_top" + to_string(n_feat) + "_" + obj;
                            if (regime) name += "_regime";

                            Config cfg;
                            cfg.name = name;
                            cfg.model_type = model_t;
                            cfg.n_features = n_feat;
                            cfg.n_epochs = (model_t == "logistic") ? 50 : 10;
                            cfg.learning_rate = 0.01;
                            cfg.l2_lambda = 0.001;
                            cfg.n_stumps = 0;
                            cfg.thresholds = standard_thresholds;
                            cfg.ftrl_alpha = 0.1;
                            cfg.ftrl_beta = 1.0;
                            cfg.ftrl_l1 = 1.0;
                            cfg.ftrl_l2 = 1.0;
                            cfg.pa_C = 1.0;
                            cfg.feature_score_method = score_m;
                            cfg.regime_aware = regime;
                            cfg.objective = obj;

                            configs.push_back(cfg);
                            config_count++;
                        }
                    }
                }
            }
        }

        print_progress("Generated " + to_string(configs.size()) + " sweep configs", true);

    } else if (SMOKE) {
        Config c1;
        c1.name = "fast_logistic_top50";
        c1.model_type = "logistic";
        c1.n_features = 50;
        c1.n_epochs = 2;
        c1.learning_rate = 0.01;
        c1.l2_lambda = 0.001;
        c1.n_stumps = 0;
        c1.thresholds = standard_thresholds;
        c1.feature_score_method = feature_score_method;
        c1.regime_aware = regime_aware;
        c1.objective = objective;
        configs.push_back(c1);

        Config c2;
        c2.name = "fast_stump_top50";
        c2.model_type = "stump_ensemble";
        c2.n_features = 50;
        c2.n_epochs = 0;
        c2.learning_rate = 0;
        c2.l2_lambda = 0;
        c2.n_stumps = 20;
        c2.thresholds = standard_thresholds;
        c2.feature_score_method = feature_score_method;
        c2.regime_aware = regime_aware;
        c2.objective = objective;
        configs.push_back(c2);

    } else {
        // Default configs (old-style)
        vector<tuple<string, string, int, int>> base_configs = {
            {"fast_logistic_top100", "logistic", 100, 50},
            {"fast_logistic_top200", "logistic", 200, 50},
            {"fast_ftrl_top100", "ftrl", 100, 1},
            {"fast_pa_top100", "passive_aggressive", 100, 10},
            {"fast_rank_top100", "rank_ensemble", 100, 0},
            {"fast_rank_top200", "rank_ensemble", 200, 0},
        };

        for (const auto& [name, model, n_feat, epochs] : base_configs) {
            Config cfg;
            cfg.name = name;
            cfg.model_type = model;
            cfg.n_features = n_feat;
            cfg.n_epochs = epochs;
            cfg.learning_rate = 0.01;
            cfg.l2_lambda = 0.001;
            cfg.n_stumps = 0;
            cfg.thresholds = standard_thresholds;
            cfg.ftrl_alpha = 0.1;
            cfg.ftrl_beta = 1.0;
            cfg.ftrl_l1 = 1.0;
            cfg.ftrl_l2 = 1.0;
            cfg.pa_C = 1.0;
            cfg.feature_score_method = feature_score_method;
            cfg.regime_aware = regime_aware;
            cfg.objective = objective;
            configs.push_back(cfg);
        }
    }

    print_progress("\n[CONFIGS]", true);
    print_progress("Total: " + to_string(configs.size()), true);

    log_event("configs_configured", "\"n_configs\":" + to_string(configs.size()));

    // Folds — chronological walk-forward with embargo
    int embargo = horizon;

    struct FoldSpec {
        int train_start, train_end;
        int embargo_start, embargo_end;
        int test_start, test_end;
    };
    vector<FoldSpec> folds;

    if (SMOKE) {
        // Smoke: force 1 fold — first 60% train, embargo, rest test
        int min_train = 1000;
        int min_test = 500;
        int train_end = (int)(meta.rows * 0.6);
        int test_start = train_end + embargo;
        int test_end = meta.rows;

        if (train_end < min_train || (test_end - test_start) < min_test) {
            cerr << "FATAL: Not enough data for smoke fold. rows=" << meta.rows
                 << " need train>=" << min_train << " test>=" << min_test << endl;
            return 1;
        }

        folds.push_back({0, train_end, train_end, test_start, test_start, test_end});
    } else {
        // Full: expanding window walk-forward
        // Each fold: train on rows [0, train_end), embargo [train_end, test_start), test [test_start, test_end)
        // test_size = rows / (n_folds + 1) to leave room for all folds
        int test_size = meta.rows / (n_folds + 1);
        int min_train = test_size; // train must be at least as big as test

        for (int i = 0; i < n_folds; ++i) {
            int train_end = (i + 1) * test_size;
            int test_start_i = train_end + embargo;
            int test_end_i = test_start_i + test_size;

            if (train_end < min_train) continue;
            if (test_end_i > meta.rows) {
                // Try shrinking last fold test to fit
                test_end_i = meta.rows;
                if (test_end_i - test_start_i < min_train / 2) break;
            }
            if (test_start_i >= meta.rows) break;

            folds.push_back({0, train_end, train_end, test_start_i, test_start_i, test_end_i});
        }

        if ((int)folds.size() < n_folds) {
            cerr << "[WARN] Requested " << n_folds << " folds but only " << folds.size()
                 << " possible with " << meta.rows << " rows and embargo=" << embargo << endl;
        }
    }

    if (folds.empty()) {
        cerr << "FATAL: Zero folds generated. rows=" << meta.rows << " requested=" << n_folds << endl;
        return 1;
    }

    print_progress("\n[FOLDS]", true);
    print_progress("Count: " + to_string(folds.size()), true);
    for (size_t fi = 0; fi < folds.size(); ++fi) {
        const auto& f = folds[fi];
        int train_rows = f.train_end - f.train_start;
        int test_rows = f.test_end - f.test_start;
        print_progress("  Fold " + to_string(fi + 1) + ": train[" + to_string(f.train_start) + ".." + to_string(f.train_end) + "] (" + to_string(train_rows) + " rows)"
                       + " embargo[" + to_string(f.embargo_start) + ".." + to_string(f.embargo_end) + "]"
                       + " test[" + to_string(f.test_start) + ".." + to_string(f.test_end) + "] (" + to_string(test_rows) + " rows)", true);
    }

    log_event("folds_configured", "\"n_folds\":" + to_string(folds.size()));

    // Training loop
    print_progress("\n[TRAINING]", true);

    vector<FoldResult> all_results;

    for (size_t config_idx = 0; config_idx < configs.size(); ++config_idx) {
        // Runtime limit check for sweep mode
        if (MATH_SWEEP && elapsed_seconds() > MAX_SWEEP_RUNTIME_MINUTES * 60.0) {
            print_progress("\n[SWEEP TIMEOUT] Reached max runtime: " + to_string(MAX_SWEEP_RUNTIME_MINUTES) + " min", true);
            log_event("sweep_timeout");
            break;
        }

        const auto& config = configs[config_idx];

        print_progress("\n[CONFIG " + to_string(config_idx + 1) + "/" + to_string(configs.size()) + "] " + config.name, true);
        log_event("config_start", "\"config\":\"" + config.name + "\"");

        for (size_t fold_idx = 0; fold_idx < folds.size(); ++fold_idx) {
            const auto& fold = folds[fold_idx];

            print_progress("  Fold " + to_string(fold_idx + 1) + "...", true);
            log_event("fold_start", "\"fold\":" + to_string(fold_idx + 1) + ",\"config\":\"" + config.name + "\"");

            // Create indices from FoldSpec
            vector<int> train_indices, test_indices;
            train_indices.reserve(fold.train_end - fold.train_start);
            test_indices.reserve(fold.test_end - fold.test_start);

            for (int i = fold.train_start; i < fold.train_end; ++i) train_indices.push_back(i);
            for (int i = fold.test_start; i < fold.test_end; ++i) test_indices.push_back(i);

            // Train with timeout tracking
            auto fold_start_time = high_resolution_clock::now();

            auto result = train_fold(
                config, fold_idx + 1, X, y, next_bar_delta,
                train_indices, test_indices,
                lot_size, commission_per_lot, meta.gold_oz_per_lot
            );

            auto fold_end_time = high_resolution_clock::now();
            double fold_elapsed_sec = duration_cast<milliseconds>(fold_end_time - fold_start_time).count() / 1000.0;

            if (DEBUG_FOLD_TIMEOUT_SECONDS > 0 && fold_elapsed_sec > DEBUG_FOLD_TIMEOUT_SECONDS) {
                print_progress("  [FOLD_TIMEOUT_WARNING] config=" + config.name + " fold=" + to_string(fold_idx + 1) + " elapsed=" + to_string((int)fold_elapsed_sec) + "s (threshold=" + to_string(DEBUG_FOLD_TIMEOUT_SECONDS) + "s)", true);
            }

            all_results.push_back(result);

            // Write to partial CSV immediately
            {
                lock_guard<mutex> lock(OUTPUT_MUTEX);
                PARTIAL_CSV << result.config_name << "," << result.model_type << "," << result.fold << "," << result.n_features << ","
                            << result.threshold_long << "," << result.threshold_short << ","
                            << result.auc << "," << result.balanced_accuracy << "," << result.accuracy << "," << result.f1 << ","
                            << result.long_rate << "," << result.short_rate << "," << result.flat_rate << ","
                            << result.gross_pnl << "," << result.commission_paid << "," << result.net_pnl << "," << result.n_trades << ","
                            << result.sharpe << "," << result.max_drawdown << "," << result.calmar << "," << result.utility << ","
                            << result.feature_score_method << "," << result.avg_pearson_ic << "," << result.avg_spearman_ic << ","
                            << result.avg_mi << "," << result.avg_stability << "," << result.avg_turnover << ","
                            << result.objective << "," << (result.regime_aware ? "true" : "false") << "\n";
                PARTIAL_CSV.flush();
            }

            {
                stringstream ss;
                ss << fixed << setprecision(4);
                ss << "    AUC=" << result.auc << ", Net=$" << (int)result.net_pnl
                   << ", Sharpe=" << result.sharpe;
                print_progress(ss.str(), true);

                if (abs(result.net_pnl) > 5000000.0) {
                    print_progress("    PNL_SANITY_WARNING: net PnL very large for 1 lot; verify units.", true);
                }
                if (abs(result.sharpe) > 10.0) {
                    print_progress("    SHARPE_SANITY_WARNING: |Sharpe| > 10; verify return stream.", true);
                }
            }

            log_event("fold_done",
                "\"fold\":" + to_string(fold_idx + 1) +
                ",\"auc\":" + to_string(result.auc) +
                ",\"net_pnl\":" + to_string(result.net_pnl) +
                ",\"sharpe\":" + to_string(result.sharpe));
        }

        log_event("config_done", "\"config\":\"" + config.name + "\"");
    }

    // Write results CSV
    print_progress("\n[WRITE RESULTS]", true);

    ofstream csv_file(output_csv_path);
    csv_file << "config,model_type,fold,n_features,threshold_long,threshold_short,"
             << "auc,balanced_accuracy,accuracy,f1,long_rate,short_rate,flat_rate,"
             << "gross_pnl,commission_paid,net_pnl,n_trades,sharpe,max_drawdown,calmar,utility,"
             << "feature_score_method,avg_pearson_ic,avg_spearman_ic,avg_mi,avg_stability,avg_turnover,"
             << "objective,regime_aware\n";

    for (const auto& r : all_results) {
        csv_file << r.config_name << "," << r.model_type << "," << r.fold << "," << r.n_features << ","
                 << r.threshold_long << "," << r.threshold_short << ","
                 << r.auc << "," << r.balanced_accuracy << "," << r.accuracy << "," << r.f1 << ","
                 << r.long_rate << "," << r.short_rate << "," << r.flat_rate << ","
                 << r.gross_pnl << "," << r.commission_paid << "," << r.net_pnl << "," << r.n_trades << ","
                 << r.sharpe << "," << r.max_drawdown << "," << r.calmar << "," << r.utility << ","
                 << r.feature_score_method << "," << r.avg_pearson_ic << "," << r.avg_spearman_ic << ","
                 << r.avg_mi << "," << r.avg_stability << "," << r.avg_turnover << ","
                 << r.objective << "," << (r.regime_aware ? "true" : "false") << "\n";
    }
    csv_file.close();

    print_progress("✓ " + output_csv_path, true);
    log_event("output_written", "\"file\":\"" + output_csv_path + "\"");

    // Summary
    ofstream json_file(output_json_path);
    json_file << "{\n";
    json_file << "  \"timestamp\": \"" << "2026-05-21" << "\",\n";
    json_file << "  \"elapsed_seconds\": " << elapsed_seconds() << ",\n";
    json_file << "  \"threads\": " << THREAD_COUNT << ",\n";
    json_file << "  \"openmp_enabled\": " << (HYDRA_OPENMP ? "true" : "false") << ",\n";
    json_file << "  \"n_configs\": " << configs.size() << ",\n";
    json_file << "  \"n_folds\": " << folds.size() << ",\n";
    json_file << "  \"n_results\": " << all_results.size() << "\n";
    json_file << "}\n";
    json_file.close();

    print_progress("✓ " + output_json_path, true);
    log_event("output_written", "\"file\":\"" + output_json_path + "\"");

    log_event("run_done");

    print_progress("\n================================================================================", true);
    print_progress("DONE | Elapsed: " + to_string((int)elapsed_seconds()) + "s | Threads: " + to_string(THREAD_COUNT), true);
    print_progress("================================================================================", true);

    PROGRESS_JSONL.close();
    RUNTIME_LOG.close();
    PARTIAL_CSV.close();

    return 0;
}
