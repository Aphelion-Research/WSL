"""Enhanced triple-barrier labeling with Agent 1 adversarial fixes.

Key improvements over hydra/data/targets.py:
1. Spread-aware label filtering (min ATR >= 3x spread)
2. Session-conditional spread costs
3. Min hold bars to prevent one-bar spike trades
4. Both-barriers-hit assigned as NaN (not long)
5. MFE/MAE tracking for analysis
6. Label metadata for quality assessment
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from hydra.config import TARGET, BACKTEST


@dataclass
class LabelMetadata:
    """Quality metrics for generated labels."""

    total_bars: int
    labeled_bars: int
    label_rate: float
    long_rate: float
    short_rate: float
    both_hit_rate: float
    mean_atr: float
    mean_atr_pct: float
    spread_to_atr_ratio: float
    min_hold_violations: int
    session_distribution: dict[str, float]


def detect_session(timestamps: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    """Classify bars into London/NY/Asian sessions.

    London overlap: 13:00-17:00 UTC
    NY session: 13:00-22:00 UTC
    Asian session: 00:00-08:00 UTC

    Returns array of session IDs: 0=asian, 1=london_ny, 2=other
    """
    if isinstance(timestamps, pd.Series):
        timestamps = pd.DatetimeIndex(timestamps)
    hours = timestamps.hour
    session = np.zeros(len(timestamps), dtype=np.int8)

    # London/NY overlap (most liquid)
    london_ny = (hours >= 13) & (hours < 17)
    session[london_ny] = 1

    # Extended NY
    ny_extended = (hours >= 17) & (hours < 22)
    session[ny_extended] = 1

    # Asian
    asian = (hours >= 0) & (hours < 8)
    session[asian] = 0

    # Other (thinly traded)
    other = ~(london_ny | ny_extended | asian)
    session[other] = 2

    return session


def session_spread(session_id: np.ndarray, base_spread: float = BACKTEST.spread_pips) -> np.ndarray:
    """Session-conditional spread in dollars.

    London/NY: 0.15 (tight institutional spread)
    Asian: 0.50 (wide retail spread)
    Other: 0.80 (dead zone)
    """
    spread = np.full(len(session_id), base_spread, dtype=np.float32)
    spread[session_id == 1] = 0.15  # London/NY
    spread[session_id == 0] = 0.50  # Asian
    spread[session_id == 2] = 0.80  # Other
    return spread


class TripleBarrierLabeler:
    """Enhanced triple-barrier with spread awareness and quality gates."""

    def __init__(
        self,
        atr_window: int = TARGET.atr_window,
        horizon_bars: int = TARGET.horizon_bars,
        stop_mult: float = TARGET.stop_mult,
        target_mult: float = TARGET.target_mult,
        min_atr_pct: float = 0.0020,  # Agent 1 recommendation (not 0.0005)
        min_hold_bars: int = 3,  # Prevent one-bar spike trades
        spread_to_atr_min: float = 0.33,  # Max 33% cost-to-risk ratio
        use_session_spread: bool = True,
    ):
        self.atr_window = atr_window
        self.horizon = horizon_bars
        self.stop_mult = stop_mult
        self.target_mult = target_mult
        self.min_atr_pct = min_atr_pct
        self.min_hold_bars = min_hold_bars
        self.spread_to_atr_min = spread_to_atr_min
        self.use_session_spread = use_session_spread

    def compute_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> np.ndarray:
        """Wilder ATR (existing implementation preserved)."""
        pc = np.roll(close, 1)
        pc[0] = close[0]
        tr = np.maximum.reduce([high - low, np.abs(high - pc), np.abs(low - pc)])
        atr = np.full_like(tr, np.nan, dtype=np.float64)

        if len(tr) < self.atr_window:
            return atr

        atr[self.atr_window - 1] = tr[:self.atr_window].mean()
        for i in range(self.atr_window, len(tr)):
            atr[i] = (atr[i - 1] * (self.atr_window - 1) + tr[i]) / self.atr_window

        return atr

    def label_directional(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        atr: np.ndarray,
        spread: np.ndarray,
        direction: int,  # +1 for long, -1 for short
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute labels for one direction with MFE/MAE tracking.

        Returns:
            labels: 1.0=win, 0.0=loss, NaN=no_label
            mfe: maximum favorable excursion in ATR units
            mae: maximum adverse excursion in ATR units
        """
        n = len(close)
        y = np.full(n, np.nan, dtype=np.float32)
        mfe = np.full(n, np.nan, dtype=np.float32)
        mae = np.full(n, np.nan, dtype=np.float32)

        # Pre-filter valid entry bars
        candidates = np.arange(n - self.horizon)
        valid_mask = (
            np.isfinite(atr[candidates]) &
            (atr[candidates] > 0) &
            (close[candidates] != 0) &
            (atr[candidates] / close[candidates] >= self.min_atr_pct) &
            (atr[candidates] >= spread[candidates] / self.spread_to_atr_min)
        )
        valid_idx = candidates[valid_mask]

        if len(valid_idx) == 0:
            return y, mfe, mae

        # Process in chunks to bound memory: chunk_size × horizon floats
        chunk_size = max(1, min(4096, 500_000_000 // (self.horizon * 8)))

        for chunk_start in range(0, len(valid_idx), chunk_size):
            chunk = valid_idx[chunk_start:chunk_start + chunk_size]
            nc = len(chunk)

            entries = close[chunk]
            atrs = atr[chunk]

            if direction == 1:
                stops = entries - self.stop_mult * atrs
                targets = entries + self.target_mult * atrs
            else:
                stops = entries + self.stop_mult * atrs
                targets = entries - self.target_mult * atrs

            # Build forward index matrix: (nc, horizon)
            offsets = np.arange(1, self.horizon + 1)
            fwd_idx = chunk[:, np.newaxis] + offsets[np.newaxis, :]  # (nc, horizon)

            highs_fwd = high[fwd_idx]  # (nc, horizon)
            lows_fwd = low[fwd_idx]    # (nc, horizon)

            # Compute favorable/adverse excursion per bar
            if direction == 1:
                fav_all = (highs_fwd - entries[:, np.newaxis]) / atrs[:, np.newaxis]
                adv_all = (lows_fwd - entries[:, np.newaxis]) / atrs[:, np.newaxis]
                stop_hit = lows_fwd <= stops[:, np.newaxis]
                target_hit = highs_fwd >= targets[:, np.newaxis]
            else:
                fav_all = (entries[:, np.newaxis] - lows_fwd) / atrs[:, np.newaxis]
                adv_all = (entries[:, np.newaxis] - highs_fwd) / atrs[:, np.newaxis]
                stop_hit = highs_fwd >= stops[:, np.newaxis]
                target_hit = lows_fwd <= targets[:, np.newaxis]

            # Apply min_hold_bars mask
            hold_mask = offsets >= self.min_hold_bars  # (horizon,)
            stop_hit_valid = stop_hit & hold_mask[np.newaxis, :]
            target_hit_valid = target_hit & hold_mask[np.newaxis, :]

            # Find first hit bar for each entry (horizon+1 means no hit)
            no_hit = self.horizon + 1
            stop_bars = np.where(stop_hit_valid, offsets[np.newaxis, :], no_hit).min(axis=1)
            target_bars = np.where(target_hit_valid, offsets[np.newaxis, :], no_hit).min(axis=1)

            # Stop-loss priority: stop wins ties
            hit_stop = (stop_bars <= target_bars) & (stop_bars < no_hit)
            hit_target = (target_bars < stop_bars) & (target_bars < no_hit)

            y[chunk[hit_stop]] = 0.0
            y[chunk[hit_target]] = 1.0

            # MFE/MAE up to first hit bar only (initialized at 0 like reference)
            any_hit = hit_stop | hit_target
            hit_bar_k = np.where(hit_stop, stop_bars, np.where(hit_target, target_bars, 0))

            hit_indices = np.where(any_hit)[0]
            if len(hit_indices) > 0:
                # Vectorized MFE/MAE: mask columns beyond hit_bar per row
                hit_k = hit_bar_k[hit_indices]  # (n_hits,)
                # Create mask: col_idx < hit_k (columns 0..horizon-1 represent bars 1..horizon)
                col_range = np.arange(self.horizon)[np.newaxis, :]  # (1, horizon)
                valid_cols = col_range < hit_k[:, np.newaxis]  # (n_hits, horizon)

                fav_masked = np.where(valid_cols, fav_all[hit_indices], -np.inf)
                adv_masked = np.where(valid_cols, adv_all[hit_indices], np.inf)

                mfe_vals = np.maximum(0.0, fav_masked.max(axis=1))
                mae_vals = np.minimum(0.0, adv_masked.min(axis=1))

                mfe[chunk[hit_indices]] = mfe_vals.astype(np.float32)
                mae[chunk[hit_indices]] = mae_vals.astype(np.float32)

        return y, mfe, mae

    def fit_transform(
        self,
        df: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        timestamp_col: str = "timestamp",
    ) -> tuple[np.ndarray, LabelMetadata]:
        """Generate unified labels with quality metadata.

        Returns:
            labels: 1.0=long, 0.0=short, NaN=no_label
            metadata: LabelMetadata with quality stats
        """
        high = df[high_col].values.astype(np.float64)
        low = df[low_col].values.astype(np.float64)
        close = df[close_col].values.astype(np.float64)

        # Compute ATR
        atr = self.compute_atr(high, low, close)

        # Session-conditional spread
        if self.use_session_spread and timestamp_col in df.columns:
            timestamps = pd.to_datetime(df[timestamp_col])
            session_id = detect_session(timestamps)
            spread = session_spread(session_id)
        else:
            spread = np.full(len(df), BACKTEST.spread_pips, dtype=np.float32)

        # Label both directions
        y_long, mfe_long, mae_long = self.label_directional(
            high, low, close, atr, spread, direction=1
        )
        y_short, mfe_short, mae_short = self.label_directional(
            high, low, close, atr, spread, direction=-1
        )

        # Unified labels (Agent 1 fix: both-hit → NaN, not long)
        y = np.full(len(df), np.nan, dtype=np.float32)

        long_win = y_long == 1.0
        short_win = y_short == 1.0

        # Clear wins (only one direction hit target)
        y[long_win & ~short_win] = 1.0
        y[short_win & ~long_win] = 0.0

        # Both hit → NaN (high-vol ambiguous regime)
        both_hit = long_win & short_win
        y[both_hit] = np.nan

        # Compute metadata
        labeled_mask = np.isfinite(y)
        n_labeled = labeled_mask.sum()

        if n_labeled > 0:
            long_rate = (y[labeled_mask] == 1.0).sum() / n_labeled
        else:
            long_rate = 0.0

        atr_valid = atr[np.isfinite(atr)]
        close_valid = close[np.isfinite(atr)]

        if len(atr_valid) > 0:
            mean_atr = float(np.mean(atr_valid))
            mean_atr_pct = float(np.mean(atr_valid / close_valid))
        else:
            mean_atr = 0.0
            mean_atr_pct = 0.0

        # Session distribution
        if self.use_session_spread and timestamp_col in df.columns:
            session_dist = {
                "london_ny": float((session_id[labeled_mask] == 1).sum() / max(n_labeled, 1)),
                "asian": float((session_id[labeled_mask] == 0).sum() / max(n_labeled, 1)),
                "other": float((session_id[labeled_mask] == 2).sum() / max(n_labeled, 1)),
            }
        else:
            session_dist = {}

        metadata = LabelMetadata(
            total_bars=len(df),
            labeled_bars=n_labeled,
            label_rate=n_labeled / len(df) if len(df) > 0 else 0.0,
            long_rate=long_rate,
            short_rate=1.0 - long_rate if n_labeled > 0 else 0.0,
            both_hit_rate=both_hit.sum() / len(df) if len(df) > 0 else 0.0,
            mean_atr=mean_atr,
            mean_atr_pct=mean_atr_pct,
            spread_to_atr_ratio=float(np.mean(spread[labeled_mask]) / mean_atr) if mean_atr > 0 else 0.0,
            min_hold_violations=0,  # Would need separate tracking
            session_distribution=session_dist,
        )

        return y, metadata


def compute_label_statistics(
    labels: np.ndarray,
    feature_matrix: Optional[np.ndarray] = None,
) -> dict:
    """Compute label distribution statistics for RAGD/reporting.

    Args:
        labels: Array of labels (1.0=long, 0.0=short, NaN=no_label)
        feature_matrix: Optional feature matrix for correlation analysis

    Returns:
        Statistics dict for logging
    """
    valid_mask = np.isfinite(labels)
    n_valid = valid_mask.sum()

    if n_valid == 0:
        return {
            "n_total": len(labels),
            "n_labeled": 0,
            "label_rate": 0.0,
            "class_balance": {"long": 0.0, "short": 0.0},
        }

    long_mask = labels[valid_mask] == 1.0
    short_mask = labels[valid_mask] == 0.0

    stats = {
        "n_total": len(labels),
        "n_labeled": n_valid,
        "label_rate": float(n_valid / len(labels)),
        "class_balance": {
            "long": float(long_mask.sum() / n_valid),
            "short": float(short_mask.sum() / n_valid),
        },
    }

    # Feature correlation with labels (if provided)
    if feature_matrix is not None and n_valid > 50:
        valid_features = feature_matrix[valid_mask]
        valid_labels = labels[valid_mask]

        # Compute per-feature correlation
        correlations = []
        for i in range(valid_features.shape[1]):
            feat = valid_features[:, i]
            if np.isfinite(feat).sum() > 50:
                corr = np.corrcoef(feat[np.isfinite(feat)], valid_labels[np.isfinite(feat)])[0, 1]
                if np.isfinite(corr):
                    correlations.append(abs(corr))

        if correlations:
            stats["label_feature_correlation"] = {
                "mean_abs_corr": float(np.mean(correlations)),
                "max_abs_corr": float(np.max(correlations)),
                "n_features_analyzed": len(correlations),
            }

    return stats
