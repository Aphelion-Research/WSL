"""Purged walk-forward cross-validation."""
from __future__ import annotations

import numpy as np

from hydra.config import CV


def walk_forward_splits(
    n: int,
    n_splits: int = CV.n_splits,
    purge: int = CV.purge_bars,
    embargo: int = CV.embargo_bars,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Generate expanding-window train/val/test index arrays.

    Returns list of (train_idx, val_idx, test_idx) tuples.
    """
    fold_size = n // (n_splits + 2)
    out = []
    for k in range(n_splits):
        tr_end = (k + 1) * fold_size
        va_beg = tr_end + embargo + purge
        va_size = max(1, int(fold_size * CV.val_frac / (1 - CV.val_frac - CV.test_frac)))
        va_end = va_beg + va_size
        te_beg = va_end + embargo
        te_size = max(1, int(fold_size * CV.test_frac / (1 - CV.val_frac - CV.test_frac)))
        te_end = te_beg + te_size
        if te_end > n:
            break
        out.append((
            np.arange(tr_end),
            np.arange(va_beg, va_end),
            np.arange(te_beg, te_end),
        ))
    return out
