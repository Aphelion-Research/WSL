"""Probability calibration and conformal prediction for HYDRA-MoE."""

import pickle
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from loguru import logger


class ProbabilityCalibrator:
    """Isotonic regression calibration wrapper."""

    def __init__(self, method: str = "isotonic"):
        self.method = method
        self.calibrator = None

    def fit(self, proba: np.ndarray, y_true: np.ndarray) -> None:
        """Fit calibrator on validation set predictions.

        Args:
            proba: Raw model probabilities (n,).
            y_true: True binary labels (n,).
        """
        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            self.calibrator.fit(proba, y_true)
        else:
            # Platt scaling (logistic)
            from sklearn.linear_model import LogisticRegression
            self.calibrator = LogisticRegression(C=1e10, solver="lbfgs", max_iter=10000)
            self.calibrator.fit(proba.reshape(-1, 1), y_true)

        ece_before = self.ece(proba, y_true)
        ece_after = self.ece(self.transform(proba), y_true)
        logger.info(f"  Calibration ({self.method}): ECE {ece_before:.4f} → {ece_after:.4f}")

    def transform(self, proba: np.ndarray) -> np.ndarray:
        """Apply calibration to raw probabilities.

        Args:
            proba: Raw probabilities (n,).

        Returns:
            Calibrated probabilities (n,).
        """
        if self.calibrator is None:
            return proba

        if self.method == "isotonic":
            result = self.calibrator.transform(proba)
        else:
            result = self.calibrator.predict_proba(proba.reshape(-1, 1))[:, 1]

        return np.clip(result, 0.0, 1.0).astype(np.float32)

    def ece(self, proba: np.ndarray, y_true: np.ndarray, n_bins: int = 15) -> float:
        """Expected Calibration Error.

        Args:
            proba: Predicted probabilities.
            y_true: True labels.
            n_bins: Number of bins.

        Returns:
            ECE value (lower is better, target < 0.02).
        """
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece_val = 0.0
        n = len(proba)

        for i in range(n_bins):
            mask = (proba >= bin_edges[i]) & (proba < bin_edges[i + 1])
            if i == n_bins - 1:
                mask = (proba >= bin_edges[i]) & (proba <= bin_edges[i + 1])
            if mask.sum() == 0:
                continue
            bin_acc = y_true[mask].mean()
            bin_conf = proba[mask].mean()
            ece_val += (mask.sum() / n) * abs(bin_acc - bin_conf)

        return float(ece_val)

    def mce(self, proba: np.ndarray, y_true: np.ndarray, n_bins: int = 15) -> float:
        """Maximum Calibration Error."""
        bin_edges = np.linspace(0, 1, n_bins + 1)
        max_err = 0.0

        for i in range(n_bins):
            mask = (proba >= bin_edges[i]) & (proba < bin_edges[i + 1])
            if i == n_bins - 1:
                mask = (proba >= bin_edges[i]) & (proba <= bin_edges[i + 1])
            if mask.sum() == 0:
                continue
            bin_acc = y_true[mask].mean()
            bin_conf = proba[mask].mean()
            max_err = max(max_err, abs(bin_acc - bin_conf))

        return float(max_err)

    def reliability_diagram(self, proba: np.ndarray, y_true: np.ndarray, save_path: str = None) -> None:
        """Plot reliability diagram (calibration curve)."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        n_bins = 15
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_accs = []
        bin_confs = []
        bin_counts = []

        for i in range(n_bins):
            mask = (proba >= bin_edges[i]) & (proba < bin_edges[i + 1])
            if i == n_bins - 1:
                mask = (proba >= bin_edges[i]) & (proba <= bin_edges[i + 1])
            if mask.sum() == 0:
                bin_accs.append(np.nan)
                bin_confs.append((bin_edges[i] + bin_edges[i + 1]) / 2)
                bin_counts.append(0)
            else:
                bin_accs.append(y_true[mask].mean())
                bin_confs.append(proba[mask].mean())
                bin_counts.append(mask.sum())

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), gridspec_kw={"height_ratios": [3, 1]})

        ax1.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
        ax1.plot(bin_confs, bin_accs, "bo-", label=f"Model (ECE={self.ece(proba, y_true):.4f})")
        ax1.set_xlabel("Mean predicted probability")
        ax1.set_ylabel("Fraction of positives")
        ax1.set_title("Reliability Diagram")
        ax1.legend()
        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
        ax1.grid(True, alpha=0.3)

        bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(n_bins)]
        ax2.bar(bin_centers, bin_counts, width=1.0 / n_bins, alpha=0.5, edgecolor="black")
        ax2.set_xlabel("Mean predicted probability")
        ax2.set_ylabel("Count")
        ax2.set_xlim(0, 1)

        plt.tight_layout()
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

    def save(self, path: str) -> None:
        """Save calibrator to pickle."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"method": self.method, "calibrator": self.calibrator}, f)

    def load(self, path: str) -> None:
        """Load calibrator from pickle."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.method = data["method"]
        self.calibrator = data["calibrator"]


class ConformalWrapper:
    """Conformal prediction wrapper with coverage guarantees.

    Given significance level alpha, produces prediction sets with
    1-alpha coverage on exchangeable data.
    """

    def __init__(self, alpha: float = 0.10):
        self.alpha = alpha
        self.thresholds = None  # (lower, upper)

    def calibrate(self, proba: np.ndarray, y_true: np.ndarray) -> None:
        """Compute nonconformity scores on calibration set.

        Args:
            proba: Calibrated probabilities from MoE.
            y_true: True binary labels.
        """
        # Nonconformity score: 1 - P(true class)
        scores = np.where(y_true == 1, 1 - proba, proba)
        # Quantile for coverage
        n = len(scores)
        q = np.ceil((n + 1) * (1 - self.alpha)) / n
        q = min(q, 1.0)
        threshold = np.quantile(scores, q)
        self.thresholds = threshold
        logger.info(f"  Conformal threshold (alpha={self.alpha}): {threshold:.4f}")

    def predict_set(self, proba: np.ndarray) -> np.ndarray:
        """Return prediction sets: 0={short}, 1={long}, 2={long,short} (uncertain).

        Args:
            proba: Calibrated probabilities.

        Returns:
            Array of set indicators (n,): 0=short, 1=long, 2=uncertain.
        """
        if self.thresholds is None:
            return np.where(proba >= 0.5, 1, 0).astype(np.int32)

        # Include class if P(class) >= 1 - threshold
        include_long = proba >= (1 - self.thresholds)
        include_short = (1 - proba) >= (1 - self.thresholds)

        result = np.full(len(proba), 2, dtype=np.int32)  # uncertain by default
        result[include_long & ~include_short] = 1   # only long
        result[include_short & ~include_long] = 0   # only short
        return result
