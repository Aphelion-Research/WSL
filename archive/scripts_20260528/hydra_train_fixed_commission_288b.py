#!/usr/bin/env python3
"""
HYDRA 10-run training with fixed commission cost model.
Broker covers spread/slippage — only charge fixed commission per position change.

ENHANCED: Rich progress bars with ETA, JSONL telemetry, resume support, crash diagnostics.
"""
import polars as pl
import numpy as np
import pandas as pd
from pathlib import Path
import json
import argparse
import logging
import traceback
import sys
import time
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif
import warnings
warnings.filterwarnings('ignore')

# Try imports
try:
    import lightgbm as lgb
    HAS_LGBM = True
except:
    HAS_LGBM = False

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn, TaskProgressColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    HAS_RICH = True
except:
    HAS_RICH = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except:
    HAS_TQDM = False

try:
    import psutil
    HAS_PSUTIL = True
except:
    HAS_PSUTIL = False

# ============================================================================
# CONSTANTS
# ============================================================================
COMMISSION_PER_0_1_LOT = 0.50  # USD
COMMISSION_PER_1_LOT = 5.00    # USD
DEFAULT_LOT_SIZE = 1.0
GOLD_OZ_PER_LOT = 100  # standard XAUUSD contract

# Paths
DEFAULT_DATASET = Path("data/hydra_xauusd_m5_master_clean.parquet")
DEFAULT_SCHEMA = Path("data/hydra_xauusd_m5_master_schema.json")
DEFAULT_LABEL = 'label_288b'
HORIZON = 288

# Output
OUTPUT_CSV = Path("runs/hydra_fixed_commission_288b_10runs.csv")
OUTPUT_PARTIAL_CSV = Path("runs/hydra_fixed_commission_288b_partial.csv")
OUTPUT_JSON = Path("reports/hydra_fixed_commission_288b_summary.json")
OUTPUT_MD = Path("reports/hydra_fixed_commission_288b_report.md")
OUTPUT_RUNTIME_LOG = Path("reports/hydra_fixed_commission_288b_runtime.log")
OUTPUT_PROGRESS_JSONL = Path("reports/hydra_fixed_commission_288b_progress.jsonl")
OUTPUT_CRASH_JSON = Path("reports/hydra_fixed_commission_288b_crash.json")

# ============================================================================
# GLOBAL STATE
# ============================================================================
RUN_START_TIME = time.time()
LAST_HEARTBEAT = RUN_START_TIME
CURRENT_BEST = {'config': None, 'sharpe': -np.inf, 'net_pnl': -np.inf, 'auc': 0}
ARGS = None
CONSOLE = None
PROGRESS_FILE = None
LOGGER = None

# ============================================================================
# HELPERS
# ============================================================================

def get_memory_mb():
    """Get current RSS memory in MB."""
    if HAS_PSUTIL:
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0
    return 0

def get_cpu_percent():
    """Get current CPU usage."""
    if HAS_PSUTIL:
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0
    return 0

def elapsed():
    """Seconds since run start."""
    return time.time() - RUN_START_TIME

def log_event(event, **kwargs):
    """Append event to progress JSONL."""
    global PROGRESS_FILE
    obj = {
        'timestamp': datetime.now().isoformat(),
        'elapsed_seconds': round(elapsed(), 2),
        'event': event,
        'memory_mb': round(get_memory_mb(), 1),
        **kwargs
    }

    if PROGRESS_FILE:
        PROGRESS_FILE.write(json.dumps(obj) + '\n')
        PROGRESS_FILE.flush()

    if LOGGER:
        LOGGER.info(f"EVENT: {event} | {json.dumps(kwargs)}")

def heartbeat(step=None):
    """Print heartbeat if interval exceeded."""
    global LAST_HEARTBEAT

    if ARGS.quiet:
        return

    now = time.time()
    if now - LAST_HEARTBEAT < ARGS.heartbeat_seconds:
        return

    LAST_HEARTBEAT = now

    msg = f"\n{'='*80}\n"
    msg += f"HEARTBEAT | Elapsed: {elapsed():.0f}s | Memory: {get_memory_mb():.0f}MB | CPU: {get_cpu_percent():.0f}%\n"
    if step:
        msg += f"Step: {step}\n"
    if CURRENT_BEST['config']:
        msg += f"Current Best: {CURRENT_BEST['config']} | Sharpe={CURRENT_BEST['sharpe']:.2f} | Net=${CURRENT_BEST['net_pnl']:.0f} | AUC={CURRENT_BEST['auc']:.3f}\n"
    msg += f"{'='*80}\n"

    print(msg, flush=True)
    if LOGGER:
        LOGGER.info(msg)

def verify_outputs():
    """Verify output files exist and are non-empty."""
    required = [OUTPUT_CSV, OUTPUT_JSON, OUTPUT_MD, OUTPUT_RUNTIME_LOG, OUTPUT_PROGRESS_JSONL]

    all_good = True
    for path in required:
        if not path.exists():
            print(f"✗ Missing: {path}", flush=True)
            all_good = False
        elif path.stat().st_size == 0:
            print(f"✗ Empty: {path}", flush=True)
            all_good = False
        else:
            print(f"✓ {path} ({path.stat().st_size:,} bytes)", flush=True)

    if all_good:
        print("\n✓ OUTPUT_VERIFICATION_PASS\n", flush=True)
        log_event('output_verified', status='pass')
    else:
        print("\n✗ OUTPUT_VERIFICATION_FAIL\n", flush=True)
        log_event('output_verified', status='fail')

    return all_good

def write_partial_result(row):
    """Append row to partial CSV."""
    df = pd.DataFrame([row])
    if not OUTPUT_PARTIAL_CSV.exists():
        df.to_csv(OUTPUT_PARTIAL_CSV, index=False)
    else:
        df.to_csv(OUTPUT_PARTIAL_CSV, index=False, mode='a', header=False)

def load_partial_results():
    """Load partial results for resume."""
    if not OUTPUT_PARTIAL_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(OUTPUT_PARTIAL_CSV)

def should_skip_completed(config_name, fold, partial_df):
    """Check if this config/fold already completed."""
    if partial_df.empty:
        return False

    mask = (partial_df['config'] == config_name) & (partial_df['fold'] == fold)
    return mask.any()

def crash_handler(exc_info, state):
    """Write crash diagnostics."""
    crash_data = {
        'timestamp': datetime.now().isoformat(),
        'elapsed_seconds': round(elapsed(), 2),
        'exception_type': exc_info[0].__name__ if exc_info[0] else 'Unknown',
        'exception_message': str(exc_info[1]) if exc_info[1] else 'Unknown',
        'traceback': ''.join(traceback.format_exception(*exc_info)),
        'state': state,
        'memory_mb': get_memory_mb(),
        'outputs': {
            'partial_csv_exists': OUTPUT_PARTIAL_CSV.exists(),
            'partial_csv_size': OUTPUT_PARTIAL_CSV.stat().st_size if OUTPUT_PARTIAL_CSV.exists() else 0
        }
    }

    OUTPUT_CRASH_JSON.write_text(json.dumps(crash_data, indent=2))
    log_event('run_failed', **crash_data)

    print(f"\n{'='*80}", flush=True)
    print("CRASH DIAGNOSTICS", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"Exception: {crash_data['exception_type']}", flush=True)
    print(f"Message: {crash_data['exception_message']}", flush=True)
    print(f"State: {state}", flush=True)
    print(f"Crash log: {OUTPUT_CRASH_JSON}", flush=True)
    print(f"{'='*80}\n", flush=True)

# ============================================================================
# COST FUNCTION
# ============================================================================

def calculate_fixed_commission_pnl(positions, returns, close_prices, lot_size=1.0):
    """
    Calculate PnL with fixed commission.

    Args:
        positions: array of {-1, 0, +1}
        returns: array of log returns
        close_prices: array of close prices
        lot_size: position size in lots

    Returns:
        dict with gross_pnl_usd, commission_usd, net_pnl_usd
    """
    # Gross PnL in returns
    gross_ret = positions * returns

    # Convert to USD
    notional = close_prices * GOLD_OZ_PER_LOT * lot_size
    gross_pnl_usd = gross_ret * notional

    # Commission
    position_changes = np.abs(np.diff(positions, prepend=0))
    commission_usd = position_changes * lot_size * COMMISSION_PER_1_LOT

    # Net PnL
    net_pnl_usd = gross_pnl_usd - commission_usd

    return {
        'gross_pnl_usd': gross_pnl_usd,
        'commission_usd': commission_usd,
        'net_pnl_usd': net_pnl_usd,
        'position_changes': position_changes
    }

# ============================================================================
# THRESHOLD SEARCH
# ============================================================================

def find_best_threshold(y_true, y_proba, returns, close_prices, candidates, lot_size=1.0):
    """Find threshold pair that maximizes net Sharpe."""
    best_sharpe = -np.inf
    best_threshold = None

    for long_th, short_th in candidates:
        # Apply threshold
        positions = np.where(y_proba >= long_th, 1,
                            np.where(y_proba <= short_th, -1, 0))

        # Compute PnL
        pnl_dict = calculate_fixed_commission_pnl(positions, returns, close_prices, lot_size)
        net_pnl = pnl_dict['net_pnl_usd']

        # Sharpe
        if net_pnl.std() > 0:
            sharpe = net_pnl.mean() / net_pnl.std() * np.sqrt(252 * 288)
        else:
            sharpe = 0

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_threshold = (long_th, short_th)

    return best_threshold, best_sharpe

# ============================================================================
# METRICS
# ============================================================================

def compute_classification_metrics(y_true, y_pred, y_proba):
    """Classification metrics."""
    try:
        auc = roc_auc_score(y_true, y_proba)
    except:
        auc = 0.5

    bal_acc = balanced_accuracy_score(y_true, y_pred)
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)

    pred_long = (y_pred == 1).sum() / len(y_pred)
    pred_short = (y_pred == -1).sum() / len(y_pred)
    pred_flat = (y_pred == 0).sum() / len(y_pred)

    return {
        'auc': float(auc),
        'balanced_accuracy': float(bal_acc),
        'accuracy': float(acc),
        'f1': float(f1),
        'precision': float(prec),
        'recall': float(rec),
        'pred_long_rate': float(pred_long),
        'pred_short_rate': float(pred_short),
        'pred_flat_rate': float(pred_flat),
        'class_balance': float(y_true.mean())
    }

def compute_trading_metrics(pnl_dict):
    """Trading metrics."""
    gross = pnl_dict['gross_pnl_usd']
    commission = pnl_dict['commission_usd']
    net = pnl_dict['net_pnl_usd']
    pos_changes = pnl_dict['position_changes']

    gross_total = gross.sum()
    commission_total = commission.sum()
    net_total = net.sum()

    n_changes = pos_changes.sum()
    n_trades = n_changes / 2  # round turn

    # Sharpe
    if net.std() > 0:
        sharpe = net.mean() / net.std() * np.sqrt(252 * 288)
    else:
        sharpe = 0

    # Max DD
    cum = np.cumsum(net)
    running_max = np.maximum.accumulate(cum)
    dd = running_max - cum
    max_dd = dd.max()

    return {
        'gross_pnl_usd': float(gross_total),
        'commission_usd': float(commission_total),
        'net_pnl_usd': float(net_total),
        'n_position_changes': float(n_changes),
        'n_round_turn_trades': float(n_trades),
        'avg_gross_per_trade': float(gross_total / (n_trades + 1e-10)),
        'avg_net_per_trade': float(net_total / (n_trades + 1e-10)),
        'sharpe': float(sharpe),
        'max_drawdown_usd': float(max_dd)
    }

# ============================================================================
# BASELINES
# ============================================================================

def run_baselines(df_pd, lot_size=1.0, progress_callback=None):
    """Run baseline strategies."""
    baselines = []

    # Prepare data
    df_pd = df_pd.dropna(subset=['fwd_ret', 'close']).copy()
    returns = df_pd['fwd_ret'].values
    close_prices = df_pd['close'].values

    baseline_configs = [
        ('always_long', lambda: np.ones(len(df_pd))),
        ('always_short', lambda: -np.ones(len(df_pd))),
        ('prev_bar_direction', lambda: np.roll(np.sign(returns), 1)),
        ('momentum_12', lambda: np.sign(pd.Series(close_prices).pct_change(12).fillna(0).values)),
        ('momentum_72', lambda: np.sign(pd.Series(close_prices).pct_change(72).fillna(0).values)),
        ('momentum_288', lambda: np.sign(pd.Series(close_prices).pct_change(288).fillna(0).values)),
        # PATCHED: Remove bfill (uses future data). Use shift(1) + fillna(0) for point-in-time safety.
        ('mean_reversion_12', lambda: np.sign(pd.Series(close_prices).rolling(12).mean().shift(1).fillna(0).values - close_prices)),
        ('mean_reversion_72', lambda: np.sign(pd.Series(close_prices).rolling(72).mean().shift(1).fillna(0).values - close_prices)),
        ('mean_reversion_288', lambda: np.sign(pd.Series(close_prices).rolling(288).mean().shift(1).fillna(0).values - close_prices)),
        ('random_50_50', lambda: np.random.RandomState(42).choice([-1, 1], size=len(df_pd))),
    ]

    for name, position_fn in baseline_configs:
        positions = position_fn()
        pnl = calculate_fixed_commission_pnl(positions, returns, close_prices, lot_size)
        metrics = compute_trading_metrics(pnl)
        baselines.append({'name': name, **metrics})

        if progress_callback:
            progress_callback()

    return baselines

# ============================================================================
# PROGRESS CONTEXT
# ============================================================================

class ProgressContext:
    """Wrapper for Rich/tqdm/plain progress."""

    def __init__(self, use_rich=True, quiet=False):
        self.use_rich = use_rich and HAS_RICH
        self.use_tqdm = not self.use_rich and HAS_TQDM
        self.quiet = quiet
        self.progress = None
        self.tasks = {}

    def __enter__(self):
        if self.use_rich and not self.quiet:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=CONSOLE
            )
            self.progress.__enter__()
        return self

    def __exit__(self, *args):
        if self.progress:
            self.progress.__exit__(*args)

    def add_task(self, name, description, total):
        """Add a progress task."""
        if self.progress:
            task_id = self.progress.add_task(description, total=total)
            self.tasks[name] = task_id
            return task_id
        return None

    def update(self, name, advance=1):
        """Update progress."""
        if self.progress and name in self.tasks:
            self.progress.update(self.tasks[name], advance=advance)

    def print(self, msg):
        """Print message."""
        if not self.quiet:
            if self.progress:
                self.progress.console.print(msg)
            else:
                print(msg, flush=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    global ARGS, CONSOLE, PROGRESS_FILE, LOGGER, CURRENT_BEST

    # Parse args
    parser = argparse.ArgumentParser(description='HYDRA fixed commission training')
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--schema', type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument('--label', default=DEFAULT_LABEL)
    parser.add_argument('--lot-size', type=float, default=DEFAULT_LOT_SIZE)
    parser.add_argument('--commission-per-lot', type=float, default=COMMISSION_PER_1_LOT)
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--smoke', action='store_true', help='Fast smoke test')
    parser.add_argument('--dry-run', action='store_true', help='Validate only, no training')
    parser.add_argument('--resume', action='store_true', help='Resume from partial results')
    parser.add_argument('--no-rich', action='store_true', help='Disable Rich UI')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--verbose', action='store_true', help='Extra diagnostics')
    parser.add_argument('--log-every', type=int, default=1, help='Print every N configs')
    parser.add_argument('--heartbeat-seconds', type=int, default=30, help='Heartbeat interval')
    parser.add_argument('--output-dir', type=Path, default=Path('runs'))
    parser.add_argument('--reports-dir', type=Path, default=Path('reports'))

    ARGS = parser.parse_args()

    # Setup output dirs
    ARGS.output_dir.mkdir(exist_ok=True)
    ARGS.reports_dir.mkdir(exist_ok=True)
    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    OUTPUT_JSON.parent.mkdir(exist_ok=True)

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if ARGS.verbose else logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(OUTPUT_RUNTIME_LOG),
            logging.StreamHandler(sys.stdout) if ARGS.verbose else logging.NullHandler()
        ]
    )
    LOGGER = logging.getLogger(__name__)

    # Setup progress JSONL
    PROGRESS_FILE = open(OUTPUT_PROGRESS_JSONL, 'a')

    # Setup Rich
    use_rich = HAS_RICH and not ARGS.no_rich and not ARGS.quiet
    if use_rich:
        CONSOLE = Console()

    state = {'step': 'init'}

    try:
        # Banner
        if not ARGS.quiet:
            print("=" * 80, flush=True)
            print("HYDRA FIXED COMMISSION TRAINING", flush=True)
            print("=" * 80, flush=True)

        log_event('run_start', mode='smoke' if ARGS.smoke else 'dry_run' if ARGS.dry_run else 'full', resume=ARGS.resume)

        # ============================================================================
        # VALIDATION
        # ============================================================================
        state['step'] = 'validation'

        if not ARGS.quiet:
            print("\n[VALIDATION]", flush=True)

        # Check files
        if not ARGS.dataset.exists():
            raise FileNotFoundError(f"Dataset not found: {ARGS.dataset}")

        if not ARGS.schema.exists():
            raise FileNotFoundError(f"Schema not found: {ARGS.schema}")

        log_event('validation_start', dataset=str(ARGS.dataset), schema=str(ARGS.schema))

        # Load schema
        schema = json.loads(ARGS.schema.read_text())
        log_event('schema_loaded', columns=len(schema['columns']))

        # Feature selection
        forbidden_patterns = ['fwd', 'forward', 'future', 'next', 'lead', 'target', 'label', 'y_']

        feature_pool = [
            c['name'] for c in schema['columns']
            if c['role'] == 'feature'
            and c.get('allowed_for_training', False)
            and not c.get('is_forward_looking', False)
        ]

        # Remove forbidden patterns
        feature_pool_before = len(feature_pool)
        feature_pool = [f for f in feature_pool if not any(p in f.lower() for p in forbidden_patterns)]
        forbidden_count = feature_pool_before - len(feature_pool)

        if not ARGS.quiet:
            print(f"✓ Feature pool: {len(feature_pool)}", flush=True)
            if forbidden_count > 0:
                print(f"✓ Blocked {forbidden_count} forbidden features", flush=True)

        log_event('feature_selection', total=len(feature_pool), forbidden_blocked=forbidden_count)

        # Load dataset
        if not ARGS.quiet:
            print(f"Loading dataset: {ARGS.dataset}...", flush=True)

        df = pl.read_parquet(ARGS.dataset)
        log_event('dataset_loaded', rows=df.shape[0], cols=df.shape[1])

        if not ARGS.quiet:
            print(f"✓ Dataset: {df.shape[0]:,} rows × {df.shape[1]:,} cols", flush=True)

        # Check time
        t_min = df['time'].min()
        t_max = df['time'].max()
        if t_min.year < 2010:
            raise ValueError(f"Time min year {t_min.year} < 2010")

        if not ARGS.quiet:
            print(f"✓ Time: {t_min} → {t_max}", flush=True)

        # Check duplicates
        dup_count = df.select(pl.col('time')).is_duplicated().sum()
        if dup_count > 0:
            raise ValueError(f"Duplicate timestamps: {dup_count}")

        if not ARGS.quiet:
            print(f"✓ No duplicates", flush=True)

        # Check label
        if ARGS.label not in df.columns:
            raise ValueError(f"Label {ARGS.label} not found")

        if not ARGS.quiet:
            print(f"✓ Label: {ARGS.label}", flush=True)

        log_event('validation_passed')

        # Load close prices
        raw_df = pl.read_parquet('data/mt5_history/XAUUSD_M5_dukascopy.parquet')
        close_prices = raw_df.select(['time', 'close']).to_pandas()

        # Convert to pandas
        df_pd = df.to_pandas()
        df_pd = df_pd.merge(close_prices, on='time', how='left')
        df_pd = df_pd.sort_values('time').reset_index(drop=True)

        # Drop label nulls
        rows_before = len(df_pd)
        df_pd = df_pd.dropna(subset=[ARGS.label, 'close'])
        rows_dropped = rows_before - len(df_pd)

        if not ARGS.quiet:
            print(f"✓ After dropna: {len(df_pd):,} rows (dropped {rows_dropped})", flush=True)

        # Balance
        y_balance = df_pd[ARGS.label].mean()
        if not ARGS.quiet:
            print(f"✓ Label balance: {y_balance:.3f}", flush=True)

        # Compute forward return
        df_pd['fwd_ret'] = np.log(df_pd['close'].shift(-HORIZON) / df_pd['close'])

        # Return units
        ret_mean = df_pd['fwd_ret'].dropna().mean()
        ret_std = df_pd['fwd_ret'].dropna().std()

        if not ARGS.quiet:
            print(f"\n[RETURN UNITS]", flush=True)
            print(f"Return mean: {ret_mean:.6f}", flush=True)
            print(f"Return std: {ret_std:.6f}", flush=True)
            print(f"Units: LOG RETURNS (decimal)", flush=True)

        if not ARGS.quiet:
            print(f"\n[COST MODEL]", flush=True)
            print(f"Broker covers: spread + slippage", flush=True)
            print(f"Commission: ${ARGS.commission_per_lot}/lot", flush=True)
            print(f"Lot size: {ARGS.lot_size}", flush=True)

        # ============================================================================
        # FOLDS
        # ============================================================================
        state['step'] = 'fold_setup'

        if not ARGS.quiet:
            print("\n[FOLD SETUP]", flush=True)

        n_folds = 1 if ARGS.smoke else ARGS.folds
        embargo = HORIZON

        n_rows = len(df_pd)
        fold_size = n_rows // n_folds

        folds = []
        for i in range(n_folds):
            train_end = (i + 1) * fold_size
            test_start = train_end + embargo
            test_end = min(test_start + fold_size, n_rows)

            if test_start >= n_rows:
                break

            folds.append({
                'fold': i + 1,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end
            })

        if not ARGS.quiet:
            print(f"Folds: {len(folds)}", flush=True)
            if ARGS.verbose:
                for fold in folds:
                    t_train_end = df_pd.iloc[fold['train_end']]['time']
                    t_test_start = df_pd.iloc[fold['test_start']]['time']
                    t_test_end = df_pd.iloc[fold['test_end']-1]['time']
                    print(f"  Fold {fold['fold']}: train={fold['train_end']:,} ({t_train_end}), test={fold['test_start']:,}-{fold['test_end']:,} ({t_test_start} → {t_test_end})", flush=True)

        log_event('folds_configured', n_folds=len(folds))

        # ============================================================================
        # CONFIGS
        # ============================================================================
        state['step'] = 'config_setup'

        if not ARGS.quiet:
            print("\n[HYDRA CONFIGS]", flush=True)

        configs = [
            {'name': 'hydra_lgbm_top100_balanced', 'model': 'lgbm', 'n_features': 50 if ARGS.smoke else 100, 'class_weight': 'balanced', 'seed': 42,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_lgbm_top200_balanced', 'model': 'lgbm', 'n_features': 200, 'class_weight': 'balanced', 'seed': 43,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_lgbm_top400_balanced', 'model': 'lgbm', 'n_features': 400, 'class_weight': 'balanced', 'seed': 44,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_rf_top100_balanced', 'model': 'rf', 'n_features': 100, 'class_weight': 'balanced', 'seed': 45,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_rf_top200_balanced', 'model': 'rf', 'n_features': 200, 'class_weight': 'balanced', 'seed': 46,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_rf_top400_balanced', 'model': 'rf', 'n_features': 400, 'class_weight': 'balanced', 'seed': 47,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_gbm_top100', 'model': 'gb', 'n_features': 100, 'class_weight': None, 'seed': 48,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_gbm_top200', 'model': 'gb', 'n_features': 200, 'class_weight': None, 'seed': 49,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_ensemble_top200', 'model': 'ensemble', 'n_features': 200, 'class_weight': 'balanced', 'seed': 50,
             'thresholds': [(0.52, 0.48), (0.55, 0.45), (0.60, 0.40), (0.65, 0.35)]},

            {'name': 'hydra_conservative_top100', 'model': 'lgbm', 'n_features': 100, 'class_weight': 'balanced', 'seed': 51,
             'thresholds': [(0.60, 0.40), (0.65, 0.35), (0.70, 0.30)]},
        ]

        if ARGS.smoke:
            configs = configs[:1]

        # Skip LGBM configs if not available
        if not HAS_LGBM:
            configs = [c for c in configs if c['model'] != 'lgbm']
            if not ARGS.quiet:
                print(f"⚠ Skipping LGBM configs (not installed)", flush=True)

        if not ARGS.quiet:
            print(f"Configs: {len(configs)}", flush=True)

        log_event('configs_configured', n_configs=len(configs))

        # ============================================================================
        # RUN SUMMARY
        # ============================================================================
        if not ARGS.quiet:
            print(f"\n[RUN SUMMARY]", flush=True)
            print(f"Dataset: {ARGS.dataset}", flush=True)
            print(f"Schema: {ARGS.schema}", flush=True)
            print(f"Label: {ARGS.label}", flush=True)
            print(f"Rows: {len(df_pd):,}", flush=True)
            print(f"Features: {len(feature_pool)}", flush=True)
            print(f"Folds: {len(folds)}", flush=True)
            print(f"Configs: {len(configs)}", flush=True)
            print(f"Commission: ${ARGS.commission_per_lot}/lot", flush=True)
            print(f"Lot size: {ARGS.lot_size}", flush=True)
            print(f"Gold oz/lot: {GOLD_OZ_PER_LOT}", flush=True)
            print(f"\nOutputs:", flush=True)
            print(f"  {OUTPUT_CSV}", flush=True)
            print(f"  {OUTPUT_JSON}", flush=True)
            print(f"  {OUTPUT_MD}", flush=True)
            print(f"  {OUTPUT_RUNTIME_LOG}", flush=True)
            print(f"  {OUTPUT_PROGRESS_JSONL}", flush=True)

        # ============================================================================
        # DRY RUN EXIT
        # ============================================================================
        if ARGS.dry_run:
            if not ARGS.quiet:
                print("\n[DRY RUN COMPLETE]", flush=True)
            log_event('dry_run_complete')
            PROGRESS_FILE.close()
            return

        # ============================================================================
        # RESUME
        # ============================================================================
        partial_df = pd.DataFrame()
        if ARGS.resume:
            partial_df = load_partial_results()
            if not partial_df.empty:
                if not ARGS.quiet:
                    print(f"\n[RESUME] Loaded {len(partial_df)} completed folds", flush=True)
                log_event('resume_loaded', rows=len(partial_df))

        # ============================================================================
        # TRAINING WITH PROGRESS BARS
        # ============================================================================
        state['step'] = 'training'

        if not ARGS.quiet:
            print("\n[TRAINING]", flush=True)

        all_results = []

        n_baselines = 10 if not ARGS.smoke else 1
        total_work = len(configs) * len(folds) + n_baselines + 1  # +1 for output

        with ProgressContext(use_rich=use_rich, quiet=ARGS.quiet) as progress:
            # Progress bars
            overall_task = progress.add_task('overall', '[cyan]Overall Progress', total=total_work)
            config_task = progress.add_task('configs', '[green]Configs', total=len(configs))

            for config_idx, config in enumerate(configs):
                state['config'] = config['name']

                if not ARGS.quiet and config_idx % ARGS.log_every == 0:
                    progress.print(f"\n[bold blue]CONFIG {config_idx+1}/{len(configs)}: {config['name']}[/bold blue]")

                log_event('config_start', config=config['name'], index=config_idx+1, total=len(configs))

                fold_task = progress.add_task('folds', f'[yellow]Folds for {config["name"][:30]}', total=len(folds))
                config_results = []

                for fold in folds:
                    state['fold'] = fold['fold']

                    # Skip if already completed
                    if ARGS.resume and should_skip_completed(config['name'], fold['fold'], partial_df):
                        progress.print(f"  Fold {fold['fold']}: SKIPPED (completed)")
                        progress.update('folds', advance=1)
                        progress.update('overall', advance=1)
                        continue

                    log_event('fold_start', fold=fold['fold'], config=config['name'])
                    heartbeat(f"Config {config['name']} | Fold {fold['fold']}")

                    # Within-fold progress
                    fold_steps = ['split', 'feature_rank', 'feature_select', 'scale', 'train', 'predict', 'threshold', 'metrics']
                    fold_step_task = progress.add_task('fold_steps', f'  [magenta]Fold {fold["fold"]} steps', total=len(fold_steps))

                    # Split
                    progress.update('fold_steps', advance=1)
                    train_data = df_pd.iloc[:fold['train_end']].copy()
                    test_data = df_pd.iloc[fold['test_start']:fold['test_end']].copy()

                    # Feature ranking
                    progress.update('fold_steps', advance=1)
                    log_event('feature_ranking_start', fold=fold['fold'])
                    X_train_pool = train_data[feature_pool].fillna(0).replace([np.inf, -np.inf], [1e10, -1e10])
                    y_train = train_data[ARGS.label].values

                    valid_train = ~np.isnan(y_train)
                    X_train_pool = X_train_pool[valid_train]
                    y_train = y_train[valid_train]

                    mi_scores = mutual_info_classif(X_train_pool, y_train, random_state=config['seed'])
                    ranked_features = [feature_pool[i] for i in np.argsort(mi_scores)[::-1]]

                    # Feature select
                    progress.update('fold_steps', advance=1)
                    selected_features = ranked_features[:config['n_features']]
                    log_event('feature_selection_done', n_features=len(selected_features))

                    if ARGS.verbose:
                        progress.print(f"    Top 20: {selected_features[:20]}")

                    X_train = X_train_pool[selected_features].values

                    X_test = test_data[selected_features].fillna(0).replace([np.inf, -np.inf], [1e10, -1e10]).values
                    y_test = test_data[ARGS.label].values
                    ret_test = test_data['fwd_ret'].values
                    close_test = test_data['close'].values

                    valid_test = ~(np.isnan(y_test) | np.isnan(ret_test))
                    X_test = X_test[valid_test]
                    y_test = y_test[valid_test]
                    ret_test = ret_test[valid_test]
                    close_test = close_test[valid_test]

                    if len(X_train) < 100 or len(X_test) < 10:
                        progress.print(f"    Insufficient data")
                        log_event('fold_skipped', reason='insufficient_data')
                        progress.update('fold_steps', advance=len(fold_steps) - 3)
                        progress.update('folds', advance=1)
                        progress.update('overall', advance=1)
                        continue

                    # Scale
                    progress.update('fold_steps', advance=1)
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)

                    # Train
                    progress.update('fold_steps', advance=1)
                    log_event('model_train_start', model=config['model'])

                    if config['model'] == 'lgbm':
                        model = lgb.LGBMClassifier(
                            n_estimators=300, learning_rate=0.03, max_depth=6,
                            num_leaves=31, subsample=0.8, colsample_bytree=0.8,
                            class_weight=config['class_weight'], random_state=config['seed'],
                            n_jobs=-1, verbose=-1
                        )
                    elif config['model'] == 'rf':
                        model = RandomForestClassifier(
                            n_estimators=300, max_depth=10, min_samples_leaf=50,
                            max_features='sqrt', class_weight=config['class_weight'],
                            random_state=config['seed'], n_jobs=-1
                        )
                    elif config['model'] == 'gb':
                        model = GradientBoostingClassifier(
                            n_estimators=200, learning_rate=0.03, max_depth=3,
                            subsample=0.8, random_state=config['seed']
                        )
                    elif config['model'] == 'ensemble':
                        if HAS_LGBM:
                            m1 = lgb.LGBMClassifier(n_estimators=200, max_depth=6, random_state=config['seed'], verbose=-1)
                        else:
                            m1 = GradientBoostingClassifier(n_estimators=200, max_depth=5, random_state=config['seed'])
                        m2 = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=config['seed']+1, n_jobs=-1)

                        m1.fit(X_train_scaled, y_train)
                        m2.fit(X_train_scaled, y_train)
                        log_event('model_train_done', model='ensemble')

                        # Predict
                        progress.update('fold_steps', advance=1)
                        y_proba_test = (m1.predict_proba(X_test_scaled)[:, 1] + m2.predict_proba(X_test_scaled)[:, 1]) / 2
                        y_proba_train = (m1.predict_proba(X_train_scaled)[:, 1] + m2.predict_proba(X_train_scaled)[:, 1]) / 2
                    else:
                        model.fit(X_train_scaled, y_train)
                        log_event('model_train_done', model=config['model'])

                        # Predict
                        progress.update('fold_steps', advance=1)
                        y_proba_test = model.predict_proba(X_test_scaled)[:, 1]
                        y_proba_train = model.predict_proba(X_train_scaled)[:, 1]

                    # Threshold search
                    progress.update('fold_steps', advance=1)
                    log_event('threshold_search_start')
                    ret_train = train_data.iloc[:fold['train_end']]['fwd_ret'].values[valid_train]
                    close_train = train_data.iloc[:fold['train_end']]['close'].values[valid_train]

                    best_th, _ = find_best_threshold(y_train, y_proba_train, ret_train, close_train, config['thresholds'], ARGS.lot_size)
                    log_event('threshold_search_done', threshold=str(best_th))

                    positions = np.where(y_proba_test >= best_th[0], 1,
                                        np.where(y_proba_test <= best_th[1], -1, 0))
                    y_pred_test = positions

                    # Metrics
                    progress.update('fold_steps', advance=1)
                    class_metrics = compute_classification_metrics(y_test, y_pred_test, y_proba_test)
                    pnl_dict = calculate_fixed_commission_pnl(positions, ret_test, close_test, ARGS.lot_size)
                    trade_metrics = compute_trading_metrics(pnl_dict)

                    result = {
                        'config': config['name'],
                        'model': config['model'],
                        'n_features': config['n_features'],
                        'fold': fold['fold'],
                        'threshold': str(best_th),
                        **class_metrics,
                        **trade_metrics
                    }

                    config_results.append(result)
                    write_partial_result(result)

                    log_event('fold_done', fold=fold['fold'], **result)

                    progress.print(f"    Fold {fold['fold']}: AUC={class_metrics['auc']:.3f}, Net=${trade_metrics['net_pnl_usd']:.0f}, Sharpe={trade_metrics['sharpe']:.2f}")

                    # Update current best
                    if trade_metrics['sharpe'] > CURRENT_BEST['sharpe']:
                        CURRENT_BEST = {
                            'config': config['name'],
                            'sharpe': trade_metrics['sharpe'],
                            'net_pnl': trade_metrics['net_pnl_usd'],
                            'auc': class_metrics['auc']
                        }
                        progress.print(f"[bold green]    NEW BEST: {CURRENT_BEST['config']} | Sharpe={CURRENT_BEST['sharpe']:.2f} | Net=${CURRENT_BEST['net_pnl']:.0f}[/bold green]")

                    progress.update('folds', advance=1)
                    progress.update('overall', advance=1)

                all_results.extend(config_results)
                progress.update('configs', advance=1)
                log_event('config_done', config=config['name'])

            # ============================================================================
            # BASELINES
            # ============================================================================
            state['step'] = 'baselines'
            progress.print("\n[bold cyan]BASELINES[/bold cyan]")

            log_event('baseline_start')
            baseline_task = progress.add_task('baselines', '[red]Baselines', total=n_baselines)

            baselines = run_baselines(
                df_pd if not ARGS.smoke else df_pd.iloc[:10000],
                ARGS.lot_size,
                progress_callback=lambda: (progress.update('baselines', advance=1), progress.update('overall', advance=1))
            )

            log_event('baseline_done', count=len(baselines))

            # ============================================================================
            # RESULTS
            # ============================================================================
            state['step'] = 'results'
            progress.print("\n[bold cyan]WRITING RESULTS[/bold cyan]")

            df_results = pd.DataFrame(all_results)
            df_results.to_csv(OUTPUT_CSV, index=False)
            progress.print(f"✓ {OUTPUT_CSV}")
            log_event('output_written', file=str(OUTPUT_CSV), rows=len(df_results))

            # Aggregate
            agg = df_results.groupby('config').agg({
                'auc': 'mean',
                'balanced_accuracy': 'mean',
                'net_pnl_usd': ['mean', 'std'],
                'sharpe': ['mean', 'std'],
                'commission_usd': 'mean'
            }).round(3)

            # Best config
            best_config = df_results.groupby('config')['sharpe'].mean().idxmax()
            best_sharpe = df_results.groupby('config')['sharpe'].mean().max()
            best_net = df_results[df_results['config'] == best_config]['net_pnl_usd'].mean()
            best_auc = df_results[df_results['config'] == best_config]['auc'].mean()

            # Verdict
            if best_net > 0 and best_sharpe > 1:
                folds_positive = (df_results[df_results['config'] == best_config]['net_pnl_usd'] > 0).sum()
                if folds_positive >= 4:
                    verdict = "EDGE_FOUND"
                elif folds_positive >= 3:
                    verdict = "EDGE_WEAK"
                else:
                    verdict = "NO_EDGE_FIXED_COMMISSION"
            elif best_net > 0 and best_sharpe > 0.5:
                verdict = "EDGE_WEAK"
            else:
                verdict = "NO_EDGE_FIXED_COMMISSION"

            # Save summary
            summary = {
                'timestamp': datetime.now().isoformat(),
                'elapsed_seconds': round(elapsed(), 2),
                'dataset': str(ARGS.dataset),
                'label': ARGS.label,
                'horizon': HORIZON,
                'n_folds': len(folds),
                'n_configs': len(configs),
                'cost_model': {
                    'commission_per_lot': ARGS.commission_per_lot,
                    'lot_size': ARGS.lot_size,
                    'spread_modeled': False,
                    'slippage_modeled': False
                },
                'best_config': {
                    'name': best_config,
                    'sharpe': float(best_sharpe),
                    'net_pnl_usd': float(best_net),
                    'auc': float(best_auc)
                },
                'verdict': verdict,
                'baselines': baselines
            }

            OUTPUT_JSON.write_text(json.dumps(summary, indent=2))
            progress.print(f"✓ {OUTPUT_JSON}")
            log_event('output_written', file=str(OUTPUT_JSON))

            # Write markdown
            report_lines = [
                f"# HYDRA Fixed Commission Training Report",
                f"",
                f"**Generated:** {datetime.now().isoformat()}",
                f"**Elapsed:** {elapsed():.0f}s",
                f"**Verdict:** {verdict}",
                f"",
                f"## Best Config",
                f"",
                f"- **Name:** {best_config}",
                f"- **Sharpe:** {best_sharpe:.2f}",
                f"- **Net PnL:** ${best_net:.0f}",
                f"- **AUC:** {best_auc:.3f}",
                f"",
                f"## Aggregate Results",
                f"",
                f"```",
                str(agg),
                f"```",
            ]

            OUTPUT_MD.write_text('\n'.join(report_lines))
            progress.print(f"✓ {OUTPUT_MD}")
            log_event('output_written', file=str(OUTPUT_MD))

            progress.update('overall', advance=1)

            # ============================================================================
            # FINAL TABLE
            # ============================================================================
            if use_rich and not ARGS.quiet:
                table = Table(title="Final Results")
                table.add_column("Config")
                table.add_column("Model")
                table.add_column("Features")
                table.add_column("Folds")
                table.add_column("Avg AUC")
                table.add_column("Avg Net PnL")
                table.add_column("Avg Sharpe")

                for config_name in df_results['config'].unique():
                    subset = df_results[df_results['config'] == config_name]
                    table.add_row(
                        config_name,
                        subset['model'].iloc[0],
                        str(subset['n_features'].iloc[0]),
                        str(len(subset)),
                        f"{subset['auc'].mean():.3f}",
                        f"${subset['net_pnl_usd'].mean():.0f}",
                        f"{subset['sharpe'].mean():.2f}"
                    )

                CONSOLE.print(table)

        # ============================================================================
        # VERIFY OUTPUTS
        # ============================================================================
        if not ARGS.quiet:
            print("\n[OUTPUT VERIFICATION]", flush=True)

        verify_outputs()

        log_event('run_done', verdict=verdict, elapsed_seconds=round(elapsed(), 2))

        if not ARGS.quiet:
            print("=" * 80, flush=True)
            print(f"DONE | Elapsed: {elapsed():.0f}s | Verdict: {verdict}", flush=True)
            print("=" * 80, flush=True)

    except Exception as e:
        exc_info = sys.exc_info()
        crash_handler(exc_info, state)
        raise

    finally:
        if PROGRESS_FILE:
            PROGRESS_FILE.close()

if __name__ == '__main__':
    main()
