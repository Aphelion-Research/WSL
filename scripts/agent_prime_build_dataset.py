#!/usr/bin/env python3
"""Build the Agent-Prime XAUUSD M5 research dataset.

The builder is intentionally separate from the fixed HYDRA 3001-column matrix.
It preserves the raw OHLCV source, carries existing clean HYDRA features forward,
adds point-in-time rolling/macro/microstructure features, and writes explicit
feature/target artifacts plus a manifest.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


TARGET_RE = re.compile(
    r"(^|_)(fwd|future|target|label|lead|next)(_|$)|fwd_ret|forward",
    re.IGNORECASE,
)


@dataclass
class ManifestEntry:
    feature_name: str
    feature_family: str
    lookback: int | str | None
    required_columns: list[str]
    implementation_source: str
    uses_future_data: bool
    warmup_behavior: str


def is_target_like(name: str) -> bool:
    return bool(TARGET_RE.search(name))


def utc_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce")


def infer_existing_family(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["dxy", "usdjpy", "gld", "silver", "spx", "tlt", "vix", "macro_", "cot_", "dfii", "dgs", "t10y", "walcl"]):
        return "macro"
    if any(x in n for x in ["vol", "atr", "range", "parkinson", "drawdown", "skew", "kurt", "std"]):
        return "volatility"
    if any(x in n for x in ["spread", "tick", "volume", "obv", "cmf", "liquidity"]):
        return "microstructure"
    if any(x in n for x in ["hour", "weekday", "day_", "month", "session", "qend", "mend"]):
        return "time"
    if any(x in n for x in ["ret", "return", "momentum", "roc"]):
        return "return"
    if any(x in n for x in ["rsi", "ema", "bb_", "stoch", "cci", "macd"]):
        return "technical"
    return "existing"


def add_manifest(
    manifest: list[ManifestEntry],
    names: Iterable[str],
    family: str,
    lookback: int | str | None,
    required: list[str],
    source: str = "python",
    warmup: str | None = None,
) -> None:
    if warmup is None:
        warmup = f"NaN until {lookback} observations are available" if isinstance(lookback, int) else "source-defined"
    for name in names:
        manifest.append(
            ManifestEntry(
                feature_name=name,
                feature_family=family,
                lookback=lookback,
                required_columns=required,
                implementation_source=source,
                uses_future_data=False,
                warmup_behavior=warmup,
            )
        )


def load_raw_ohlcv(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    time_col = "timestamp" if "timestamp" in df.columns else "time"
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Raw OHLC source is missing required columns: {missing}")

    out = df.copy()
    out["time"] = utc_series(out[time_col])
    out = out.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    duplicate_count = int(out["time"].duplicated().sum())
    if duplicate_count:
        raise ValueError(f"Raw source has duplicate timestamps: {duplicate_count}")

    for optional in ["tick_volume", "spread", "real_volume"]:
        if optional not in out.columns:
            out[optional] = np.nan

    keep = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    return out[keep]


def load_existing_features(path: Path, base_times: pd.Series) -> tuple[pd.DataFrame, list[str], list[ManifestEntry]]:
    if not path.exists():
        return pd.DataFrame({"time": base_times}), [], []

    df = pd.read_parquet(path)
    if "time" not in df.columns:
        return pd.DataFrame({"time": base_times}), [], []

    df = df.copy()
    df["time"] = utc_series(df["time"])
    df = df.dropna(subset=["time"]).sort_values("time")
    dropped = [c for c in df.columns if c != "time" and is_target_like(c)]
    feature_cols = [c for c in df.columns if c != "time" and c not in dropped]

    rename = {c: f"ex__{c}" for c in feature_cols}
    existing = df[["time", *feature_cols]].rename(columns=rename)
    manifest = [
        ManifestEntry(
            feature_name=rename[c],
            feature_family=infer_existing_family(c),
            lookback="existing",
            required_columns=["time"],
            implementation_source="existing",
            uses_future_data=False,
            warmup_behavior="preserved from existing clean feature table",
        )
        for c in feature_cols
    ]
    return existing, dropped, manifest


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0.0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return 100.0 - (100.0 / (1.0 + gain / (loss + 1e-12)))


def make_price_features(raw: pd.DataFrame, manifest: list[ManifestEntry]) -> pd.DataFrame:
    close = raw["close"].astype("float64")
    high = raw["high"].astype("float64")
    low = raw["low"].astype("float64")
    open_ = raw["open"].astype("float64")
    spread = raw["spread"].astype("float64")
    tick_volume = raw["tick_volume"].astype("float64")
    real_volume = raw["real_volume"].astype("float64")
    log_close = np.log(close.replace(0, np.nan))
    log_ret_1 = log_close.diff()
    pct_ret_1 = close.pct_change()

    feats: dict[str, pd.Series | np.ndarray] = {
        "raw_open": open_,
        "raw_high": high,
        "raw_low": low,
        "raw_close": close,
        "raw_spread": spread,
        "raw_tick_volume": tick_volume,
        "raw_real_volume": real_volume,
    }
    add_manifest(manifest, feats.keys(), "raw", 0, ["open", "high", "low", "close", "spread", "tick_volume", "real_volume"], warmup="available at current bar close")

    windows = [1, 2, 3, 5, 10, 20, 40, 60, 72, 120, 144, 288, 576, 1000]
    return_names = []
    for w in windows:
        names = [f"ret_log_{w}b", f"ret_pct_{w}b"]
        feats[names[0]] = log_close - log_close.shift(w)
        feats[names[1]] = close / close.shift(w) - 1.0
        return_names.extend(names)
    add_manifest(manifest, return_names, "return", "1..1000", ["close"], warmup="NaN until the requested lag is available")

    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    range_pct = (high - low) / close.replace(0, np.nan)
    body_pct = (close - open_).abs() / close.replace(0, np.nan)
    feats["range_pct_1b"] = range_pct
    feats["body_pct_1b"] = body_pct
    add_manifest(manifest, ["range_pct_1b", "body_pct_1b"], "volatility", 1, ["open", "high", "low", "close"])

    vol_names: list[str] = []
    for w in [5, 10, 20, 40, 60, 72, 120, 144, 288, 576, 1000]:
        rv = log_ret_1.rolling(w, min_periods=w).std()
        atr = true_range.rolling(w, min_periods=w).mean() / close.replace(0, np.nan)
        parkinson = np.sqrt((np.log(high / low.replace(0, np.nan)) ** 2).rolling(w, min_periods=w).mean() / (4 * math.log(2)))
        names = [
            f"vol_realized_{w}b",
            f"vol_atr_{w}b",
            f"vol_parkinson_{w}b",
            f"range_mean_{w}b",
        ]
        feats[names[0]] = rv
        feats[names[1]] = atr
        feats[names[2]] = parkinson
        feats[names[3]] = range_pct.rolling(w, min_periods=w).mean()
        vol_names.extend(names)

        if w >= 20:
            zn = f"vol_realized_z_{w}b"
            feats[zn] = (rv - rv.rolling(w * 3, min_periods=w).mean()) / (rv.rolling(w * 3, min_periods=w).std() + 1e-12)
            vol_names.append(zn)
    add_manifest(manifest, vol_names, "volatility", "5..1000", ["open", "high", "low", "close"], warmup="NaN until rolling window is available")

    regime_names = []
    for short, long in [(5, 60), (20, 120), (72, 288), (144, 576)]:
        name = f"vol_compression_{short}_{long}b"
        feats[name] = feats[f"vol_realized_{short}b"] / (feats[f"vol_realized_{long}b"] + 1e-12)
        regime_names.append(name)
    for w in [20, 72, 144, 288, 576]:
        roll_max = close.rolling(w, min_periods=w).max()
        dd = close / roll_max - 1.0
        names = [f"drawdown_{w}b", f"ret_skew_{w}b", f"ret_kurt_{w}b"]
        feats[names[0]] = dd
        feats[names[1]] = log_ret_1.rolling(w, min_periods=w).skew()
        feats[names[2]] = log_ret_1.rolling(w, min_periods=w).kurt()
        regime_names.extend(names)
    for w in [20, 72, 288]:
        for lag in [1, 2, 5, 10]:
            name = f"ret_autocorr_lag{lag}_{w}b"
            feats[name] = log_ret_1.rolling(w, min_periods=w).corr(log_ret_1.shift(lag))
            regime_names.append(name)
    add_manifest(manifest, regime_names, "volatility", "20..576", ["close"], warmup="NaN until rolling window is available")

    technical_names = []
    for period in [10, 20, 50, 100, 200]:
        ema = close.ewm(span=period, adjust=False, min_periods=period).mean()
        name = f"ema_dist_{period}b"
        feats[name] = close / (ema + 1e-12) - 1.0
        technical_names.append(name)
    for period in [7, 14, 28]:
        name = f"rsi_{period}b"
        feats[name] = rsi(close, period)
        technical_names.append(name)
    for period in [20, 72]:
        ma = close.rolling(period, min_periods=period).mean()
        std = close.rolling(period, min_periods=period).std()
        name = f"bb_pos_{period}b"
        feats[name] = (close - ma) / (2 * std + 1e-12)
        technical_names.append(name)
    add_manifest(manifest, technical_names, "technical", "7..200", ["close"], warmup="NaN until rolling/EMA window is available")

    micro_names = []
    for w in [10, 20, 60, 120, 288]:
        spread_mean = spread.rolling(w, min_periods=w).mean()
        spread_std = spread.rolling(w, min_periods=w).std()
        vol_mean = tick_volume.rolling(w, min_periods=w).mean()
        vol_std = tick_volume.rolling(w, min_periods=w).std()
        names = [f"spread_mean_{w}b", f"spread_z_{w}b", f"tick_volume_mean_{w}b", f"tick_volume_z_{w}b"]
        feats[names[0]] = spread_mean
        feats[names[1]] = (spread - spread_mean) / (spread_std + 1e-12)
        feats[names[2]] = vol_mean
        feats[names[3]] = (tick_volume - vol_mean) / (vol_std + 1e-12)
        micro_names.extend(names)
    obv = (np.sign(pct_ret_1.fillna(0.0)) * tick_volume.fillna(0.0)).cumsum()
    for w in [20, 72, 288]:
        name = f"obv_change_{w}b"
        feats[name] = obv - obv.shift(w)
        micro_names.append(name)
    add_manifest(manifest, micro_names, "microstructure", "10..288", ["close", "spread", "tick_volume"], warmup="NaN until rolling window is available")

    advanced_names = []
    sign_pos = (log_ret_1 > 0).astype(float)
    abs_ret = log_ret_1.abs()
    for w in [20, 72, 144, 288]:
        p = sign_pos.rolling(w, min_periods=w).mean().clip(1e-6, 1 - 1e-6)
        entropy_name = f"entropy_sign_{w}b"
        efficiency_name = f"fractal_efficiency_{w}b"
        feats[entropy_name] = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
        feats[efficiency_name] = (close - close.shift(w)).abs() / (abs_ret.rolling(w, min_periods=w).sum() * close + 1e-12)
        advanced_names.extend([entropy_name, efficiency_name])
    add_manifest(manifest, advanced_names, "advanced", "20..288", ["close"], warmup="NaN until rolling window is available")

    return pd.DataFrame(feats, index=raw.index)


def flatten_daily_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            "_".join(str(part).strip().lower() for part in col if str(part).strip())
            for col in out.columns
        ]
    else:
        out.columns = [str(c).strip().lower() for c in out.columns]
    if out.index.name is not None or "date" not in out.columns:
        out = out.reset_index()
    out.columns = [str(c).strip().lower() for c in out.columns]
    return out


def first_matching_column(columns: Iterable[str], token: str) -> str | None:
    token = token.lower()
    for col in columns:
        c = col.lower()
        if c == token or c.startswith(f"close_{token}") or c.endswith(f"_{token}"):
            return col
    return None


def load_daily_panel(path: Path, selected: list[str], prefix: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["available_time"])
    df = flatten_daily_columns(pd.read_parquet(path))
    date_col = "date" if "date" in df.columns else ("time" if "time" in df.columns else df.columns[0])
    out = pd.DataFrame({"date": pd.to_datetime(df[date_col], utc=True, errors="coerce")})
    for symbol in selected:
        col = first_matching_column(df.columns, symbol)
        if col is not None:
            out[f"{prefix}_{symbol}"] = pd.to_numeric(df[col], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date")
    for col in [c for c in out.columns if c != "date"]:
        s = out[col]
        out[f"{col}_ret1d"] = s.pct_change()
        out[f"{col}_ret5d"] = s.pct_change(5)
        out[f"{col}_z20d"] = (s - s.rolling(20, min_periods=20).mean()) / (s.rolling(20, min_periods=20).std() + 1e-12)
        out[f"{col}_z60d"] = (s - s.rolling(60, min_periods=60).mean()) / (s.rolling(60, min_periods=60).std() + 1e-12)
    out["available_time"] = out["date"] + pd.Timedelta(days=1)
    return out.drop(columns=["date"])


def load_macro_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["available_time"])
    selected = ["DGS10", "DGS2", "DFII10", "T10YIE", "T10Y2Y", "T10Y3M", "DFF", "UNRATE", "ICSA", "WALCL"]
    df = pd.read_parquet(path).reset_index()
    date_col = "date" if "date" in df.columns else df.columns[0]
    out = pd.DataFrame({"date": pd.to_datetime(df[date_col], utc=True, errors="coerce")})
    for col in selected:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            base = f"macro_{col.lower()}"
            out[base] = s
            out[f"{base}_chg1d"] = s.diff(1)
            out[f"{base}_chg5d"] = s.diff(5)
            out[f"{base}_z60d"] = (s - s.rolling(60, min_periods=60).mean()) / (s.rolling(60, min_periods=60).std() + 1e-12)
    out["macro_real_yield_shock_10y"] = out.get("macro_dfii10_chg1d", np.nan)
    out["available_time"] = out["date"] + pd.Timedelta(days=1)
    return out.drop(columns=["date"]).dropna(subset=["available_time"])


def load_cot_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["available_time"])
    df = pd.read_parquet(path).reset_index()
    date_col = "date" if "date" in df.columns else df.columns[0]
    out = pd.DataFrame({"date": pd.to_datetime(df[date_col], utc=True, errors="coerce")})
    for col in ["mm_long", "mm_short", "open_interest"]:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            out[f"cot_{col}"] = s
            out[f"cot_{col}_chg4w"] = s.diff(4)
            out[f"cot_{col}_z52w"] = (s - s.rolling(52, min_periods=26).mean()) / (s.rolling(52, min_periods=26).std() + 1e-12)
    if "cot_mm_long" in out.columns and "cot_mm_short" in out.columns:
        out["cot_mm_net"] = out["cot_mm_long"] - out["cot_mm_short"]
    out["available_time"] = out["date"] + pd.Timedelta(days=1)
    return out.drop(columns=["date"]).dropna(subset=["available_time"])


def asof_merge_panel(features: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty or panel.shape[1] <= 1:
        return features
    left = features[["time"]].sort_values("time")
    right = panel.sort_values("available_time")
    merged = pd.merge_asof(left, right, left_on="time", right_on="available_time", direction="backward")
    return merged.drop(columns=["available_time"], errors="ignore")


def make_time_features(times: pd.Series, manifest: list[ManifestEntry]) -> pd.DataFrame:
    t = pd.to_datetime(times, utc=True)
    hour = t.dt.hour + t.dt.minute / 60.0
    dow = t.dt.dayofweek
    month = t.dt.month
    feats = pd.DataFrame(
        {
            "time_hour_sin": np.sin(2 * np.pi * hour / 24.0),
            "time_hour_cos": np.cos(2 * np.pi * hour / 24.0),
            "time_dow_sin": np.sin(2 * np.pi * dow / 7.0),
            "time_dow_cos": np.cos(2 * np.pi * dow / 7.0),
            "time_month_sin": np.sin(2 * np.pi * month / 12.0),
            "time_month_cos": np.cos(2 * np.pi * month / 12.0),
            "time_session_asia": ((hour >= 0) & (hour < 7)).astype(float),
            "time_session_london": ((hour >= 7) & (hour < 13)).astype(float),
            "time_session_ny": ((hour >= 13) & (hour < 21)).astype(float),
            "time_is_month_end": t.dt.is_month_end.astype(float),
            "time_is_quarter_end": t.dt.is_quarter_end.astype(float),
        }
    )
    add_manifest(manifest, feats.columns, "time", 0, ["time"], warmup="available from timestamp")
    return feats


def make_macro_features(raw: pd.DataFrame, paths: dict[str, Path], manifest: list[ManifestEntry]) -> pd.DataFrame:
    selected_assets = [
        "dxy", "usdjpy", "eurusd", "gbpusd", "gld", "silver", "vix", "gvz", "tlt", "ief",
        "spx", "nasdaq", "wti", "brent", "copper", "platinum", "btc", "eth",
    ]
    panels = [
        load_daily_panel(paths["cross_asset"], selected_assets, "xa"),
        load_macro_panel(paths["macro"]),
        load_cot_panel(paths["cot"]),
    ]
    merged_parts = [asof_merge_panel(raw[["time"]], panel) for panel in panels]
    macro = pd.concat([part.drop(columns=["time"], errors="ignore") for part in merged_parts], axis=1)
    macro = macro.loc[:, ~macro.columns.duplicated()].copy()

    interaction_sources = {
        "dxy": "xa_dxy_ret1d",
        "usdjpy": "xa_usdjpy_ret1d",
        "gld": "xa_gld_ret1d",
        "silver": "xa_silver_ret1d",
        "real_yield": "macro_dfii10_chg1d",
    }
    xau_ret_72 = raw["close"].pct_change(72)
    added = {}
    for name, col in interaction_sources.items():
        if col in macro.columns:
            added[f"macro_xau_ret72_x_{name}"] = xau_ret_72 * macro[col]
    if "xa_dxy_z60d" in macro.columns and "macro_dfii10_z60d" in macro.columns:
        added["macro_dxy_real_yield_z_cross"] = macro["xa_dxy_z60d"] * macro["macro_dfii10_z60d"]
    if added:
        macro = pd.concat([macro, pd.DataFrame(added)], axis=1)

    add_manifest(
        manifest,
        macro.columns,
        "macro",
        "daily/weekly lagged by one day",
        ["data/cross_asset_extended/cross_asset_extended_daily.parquet", "data/macro/macro_daily.parquet", "data/cot/cot_gold_weekly.parquet"],
        source="python",
        warmup="daily/weekly source values shifted to next calendar day before asof join",
    )
    return macro


def make_targets(raw: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    close = raw["close"].astype("float64")
    targets = pd.DataFrame({"time": raw["time"]})
    for h in horizons:
        ret = close.shift(-h) / close - 1.0
        targets[f"fwd_ret_{h}b"] = ret
        targets[f"label_sign_{h}b"] = (ret > 0).astype("float32")
        targets.loc[ret.isna(), f"label_sign_{h}b"] = np.nan
        rolling_abs = ret.abs().rolling(5000, min_periods=500).median()
        threshold = rolling_abs.shift(1).fillna(rolling_abs.median()) * 0.25
        thr = np.where(ret > threshold, 1.0, np.where(ret < -threshold, -1.0, 0.0))
        targets[f"label_threshold_{h}b"] = thr
        targets.loc[ret.isna(), f"label_threshold_{h}b"] = np.nan
    return targets


def family_nan_percent(features: pd.DataFrame, manifest: list[ManifestEntry]) -> dict[str, float]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for entry in manifest:
        if entry.feature_name in features.columns:
            by_family[entry.feature_family].append(entry.feature_name)
    out = {}
    for family, cols in by_family.items():
        if cols:
            out[family] = float(features[cols].isna().to_numpy().mean() * 100.0)
    return out


def downcast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if col == "time":
            continue
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float32")
    return out


def write_parquet_atomic(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    os.replace(tmp, path)


def build(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = load_raw_ohlcv(Path(args.raw_ohlc))
    manifest: list[ManifestEntry] = []
    dropped_columns: list[str] = []

    existing, dropped_existing, existing_manifest = load_existing_features(Path(args.existing_features), raw["time"])
    dropped_columns.extend([f"existing:{c}" for c in dropped_existing])
    manifest.extend(existing_manifest)

    raw_features = make_price_features(raw, manifest)
    time_features = make_time_features(raw["time"], manifest)
    macro_features = make_macro_features(
        raw,
        {
            "cross_asset": Path(args.cross_asset),
            "macro": Path(args.macro),
            "cot": Path(args.cot),
        },
        manifest,
    )

    features = pd.DataFrame({"time": raw["time"]})
    features = pd.concat([features, raw_features, time_features, macro_features], axis=1)
    if existing.shape[1] > 1:
        features = features.merge(existing, on="time", how="left", validate="one_to_one")

    target_like_features = [c for c in features.columns if c != "time" and is_target_like(c)]
    if target_like_features:
        features = features.drop(columns=target_like_features)
        dropped_columns.extend([f"target_like_feature:{c}" for c in target_like_features])
        manifest = [m for m in manifest if m.feature_name not in set(target_like_features)]

    feature_cols = [c for c in features.columns if c != "time"]
    duplicate_feature_cols = [name for name, count in Counter(feature_cols).items() if count > 1]
    if duplicate_feature_cols:
        raise ValueError(f"Duplicate feature columns produced: {duplicate_feature_cols[:20]}")

    numeric = features[feature_cols].apply(pd.to_numeric, errors="coerce")
    inf_count = int(np.isinf(numeric.to_numpy(dtype="float64", na_value=np.nan)).sum())
    features[feature_cols] = numeric.replace([np.inf, -np.inf], np.nan)

    targets = make_targets(raw, args.horizons)

    features = downcast_numeric(features)
    targets = downcast_numeric(targets)
    combined = features.merge(targets, on="time", how="left", validate="one_to_one")

    feature_path = output_dir / "agent_prime_xauusd_m5_features.parquet"
    target_path = output_dir / "agent_prime_xauusd_m5_targets.parquet"
    combined_path = output_dir / "agent_prime_xauusd_m5_modeling.parquet"
    manifest_path = output_dir / "agent_prime_xauusd_m5_feature_manifest.json"
    validation_path = output_dir / "agent_prime_xauusd_m5_validation.json"

    write_parquet_atomic(features, feature_path)
    write_parquet_atomic(targets, target_path)
    write_parquet_atomic(combined, combined_path)

    manifest_json = {
        "dataset": "agent_prime_xauusd_m5",
        "source_raw_ohlc": args.raw_ohlc,
        "source_existing_features": args.existing_features,
        "features": [asdict(entry) for entry in manifest],
    }
    manifest_path.write_text(json.dumps(manifest_json, indent=2), encoding="utf-8")

    by_family = Counter(entry.feature_family for entry in manifest if entry.feature_name in feature_cols)
    validation = {
        "rows": int(len(features)),
        "columns": int(combined.shape[1]),
        "feature_columns": int(len(feature_cols)),
        "features_by_family": dict(sorted(by_family.items())),
        "target_columns": [c for c in targets.columns if c != "time"],
        "dropped_columns": dropped_columns,
        "nan_percentage_by_feature_family": family_nan_percent(features, manifest),
        "overall_nan_percentage": float(features[feature_cols].isna().to_numpy().mean() * 100.0),
        "infinite_count_before_cleaning": inf_count,
        "duplicate_timestamps": int(features["time"].duplicated().sum()),
        "first_timestamp": str(features["time"].min()),
        "last_timestamp": str(features["time"].max()),
        "raw_ohlc_columns_present": [c for c in ["open", "high", "low", "close"] if c in raw.columns],
        "output_path": str(combined_path),
        "feature_path": str(feature_path),
        "target_path": str(target_path),
        "manifest_path": str(manifest_path),
    }
    validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")

    print(json.dumps(validation, indent=2))
    return validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-ohlc", default="data/mt5_history/XAUUSD_M5_dukascopy.parquet")
    parser.add_argument("--existing-features", default="data/hydra_xauusd_m5_master_clean.parquet")
    parser.add_argument("--cross-asset", default="data/cross_asset_extended/cross_asset_extended_daily.parquet")
    parser.add_argument("--macro", default="data/macro/macro_daily.parquet")
    parser.add_argument("--cot", default="data/cot/cot_gold_weekly.parquet")
    parser.add_argument("--output-dir", default="data/agent_prime")
    parser.add_argument("--horizons", nargs="+", type=int, default=[5, 20, 72, 144, 288])
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
