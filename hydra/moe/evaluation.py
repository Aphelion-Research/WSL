"""Comprehensive evaluation suite for HYDRA-MoE."""

import json
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score, precision_score, recall_score,
    log_loss, confusion_matrix, precision_recall_curve, roc_curve, brier_score_loss
)
from loguru import logger

from hydra.moe.moe_model import HydraMoE


class MoEEvaluator:
    """Comprehensive evaluation for HYDRA-MoE with regime-level breakdown."""

    def __init__(self, moe: HydraMoE, output_dir: str):
        self.moe = moe
        self.output_dir = Path(output_dir)
        self.plots_dir = self.output_dir / "plots"
        self.metrics_dir = self.output_dir / "metrics"
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def full_evaluation(
        self,
        X_oos: np.ndarray,
        y_oos: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        single_brain_oos_proba: np.ndarray = None,
    ) -> dict:
        """Run all evaluations and save plots and metrics.

        Args:
            X_oos: OOS features.
            y_oos: OOS labels.
            X_val: Val features.
            y_val: Val labels.
            single_brain_oos_proba: Single-Brain Day OOS proba for comparison.

        Returns:
            Complete results dict.
        """
        logger.info("═══ COMPREHENSIVE EVALUATION ═══")

        # Get predictions
        oos_result = self.moe.predict(X_oos, return_routing_weights=True, return_expert_probas=True, calibrated=True)
        val_result = self.moe.predict(X_val, return_routing_weights=True, return_expert_probas=True, calibrated=True)

        results = {
            "model": "HYDRA-MoE",
            "date": "2026-05-27",
        }

        # Standard metrics
        logger.info("  Computing standard metrics...")
        results["oos"] = self._compute_metrics(y_oos, oos_result["proba"], oos_result["direction"])
        results["val"] = self._compute_metrics(y_val, val_result["proba"], val_result["direction"])

        # Calibration
        logger.info("  Computing calibration metrics...")
        results["calibration"] = self._compute_calibration(y_oos, oos_result["proba"], y_val, val_result["proba"])

        # Confidence-gated metrics
        logger.info("  Computing confidence-gated metrics...")
        results["gated"] = self._compute_gated_metrics(y_oos, oos_result["proba"], oos_result["trade_signal"])

        # Regime-level breakdown
        logger.info("  Computing regime-level breakdown...")
        results["expert_breakdown"] = self._compute_regime_breakdown(
            y_oos, oos_result["proba"], oos_result["dominant_expert"], oos_result["expert_probas"], X_oos
        )

        # Routing analysis
        logger.info("  Computing routing analysis...")
        results["routing_analysis"] = self._compute_routing_analysis(oos_result["routing_weights"], X_oos)

        # Single-brain comparison
        if single_brain_oos_proba is not None:
            logger.info("  Comparing vs Single-Brain Day...")
            results["vs_single_brain"] = self._compare_vs_baseline(
                y_oos, oos_result["proba"], single_brain_oos_proba
            )
        else:
            results["vs_single_brain"] = {"note": "No baseline proba provided"}

        # Production recommendation
        results["production_recommendation"] = self._make_recommendation(results)

        # Save results
        results_path = self.metrics_dir / "results_moe.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"  Results saved: {results_path}")

        # Generate plots
        logger.info("  Generating plots...")
        self._generate_plots(y_oos, oos_result, y_val, val_result, single_brain_oos_proba)

        # Save predictions
        logger.info("  Saving predictions...")
        pred_dir = self.output_dir / "predictions"
        pred_dir.mkdir(exist_ok=True)
        np.save(pred_dir / "oos_proba_moe.npy", oos_result["proba"])
        np.save(pred_dir / "oos_routing_weights.npy", oos_result["routing_weights"])
        np.save(pred_dir / "val_proba_moe.npy", val_result["proba"])

        return results

    def _compute_metrics(self, y_true, proba, direction) -> dict:
        """Standard classification metrics."""
        try:
            auc = roc_auc_score(y_true, proba)
        except ValueError:
            auc = 0.5

        acc = accuracy_score(y_true, direction)
        precision = precision_score(y_true, direction, zero_division=0)
        recall = recall_score(y_true, direction, zero_division=0)
        f1 = f1_score(y_true, direction, zero_division=0)

        try:
            logloss = log_loss(y_true, proba)
        except ValueError:
            logloss = 1.0

        return {
            "auc": float(auc),
            "accuracy": float(acc),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "log_loss": float(logloss),
        }

    def _compute_calibration(self, y_oos, proba_oos, y_val, proba_val) -> dict:
        """Calibration metrics: ECE, MCE, Brier."""
        ece_oos = self.moe.calibrator.ece(proba_oos, y_oos)
        mce_oos = self.moe.calibrator.mce(proba_oos, y_oos)
        brier_oos = brier_score_loss(y_oos, proba_oos)

        ece_val = self.moe.calibrator.ece(proba_val, y_val)
        mce_val = self.moe.calibrator.mce(proba_val, y_val)
        brier_val = brier_score_loss(y_val, proba_val)

        return {
            "oos_ece": float(ece_oos),
            "oos_mce": float(mce_oos),
            "oos_brier": float(brier_oos),
            "val_ece": float(ece_val),
            "val_mce": float(mce_val),
            "val_brier": float(brier_val),
        }

    def _compute_gated_metrics(self, y_true, proba, trade_signal) -> dict:
        """Confidence-gated metrics at multiple thresholds."""
        thresholds = [0.50, 0.55, 0.60, 0.65, 0.70]
        gated = {}

        for thresh in thresholds:
            gate = (proba > thresh) | (proba < (1 - thresh))
            if gate.sum() == 0:
                gated[f"gate_{thresh:.2f}"] = {"trade_rate": 0.0, "gated_accuracy": 0.0, "gated_auc": 0.5}
                continue

            trade_rate = gate.mean()
            gated_acc = accuracy_score(y_true[gate], (proba[gate] >= 0.5).astype(int))

            try:
                gated_auc = roc_auc_score(y_true[gate], proba[gate])
            except ValueError:
                gated_auc = 0.5

            gated[f"gate_{thresh:.2f}"] = {
                "trade_rate": float(trade_rate),
                "gated_accuracy": float(gated_acc),
                "gated_auc": float(gated_auc),
            }

        return gated

    def _compute_regime_breakdown(self, y_true, proba, dominant_expert, expert_probas, X) -> dict:
        """Per-expert performance breakdown."""
        breakdown = {}
        from hydra.moe.feature_groups import EXPERT_NAMES

        for k, name in enumerate(EXPERT_NAMES):
            mask = dominant_expert == k
            if mask.sum() == 0:
                breakdown[f"expert_{k}_{name}"] = {"count": 0, "pct": 0.0}
                continue

            pct = mask.mean() * 100
            try:
                expert_auc = roc_auc_score(y_true[mask], proba[mask])
            except ValueError:
                expert_auc = 0.5

            expert_acc = accuracy_score(y_true[mask], (proba[mask] >= 0.5).astype(int))

            breakdown[f"expert_{k}_{name}"] = {
                "count": int(mask.sum()),
                "pct": float(pct),
                "auc": float(expert_auc),
                "accuracy": float(expert_acc),
            }

        return breakdown

    def _compute_routing_analysis(self, routing_weights, X) -> dict:
        """Routing distribution and entropy analysis."""
        # Routing distribution
        mean_weights = routing_weights.mean(axis=0)
        dist = {f"expert_{k}_mean_weight": float(w) for k, w in enumerate(mean_weights)}

        # Routing entropy (per bar)
        entropy = -np.sum(routing_weights * np.log(routing_weights + 1e-8), axis=1)
        dist["mean_entropy"] = float(entropy.mean())
        dist["low_entropy_pct"] = float((entropy < 0.5).mean() * 100)  # hard routing

        return dist

    def _compare_vs_baseline(self, y_true, moe_proba, baseline_proba) -> dict:
        """Statistical comparison vs Single-Brain Day."""
        try:
            moe_auc = roc_auc_score(y_true, moe_proba)
        except ValueError:
            moe_auc = 0.5

        try:
            baseline_auc = roc_auc_score(y_true, baseline_proba)
        except ValueError:
            baseline_auc = 0.5

        improvement = moe_auc - baseline_auc

        # DeLong test
        try:
            pvalue = self._delong_test(y_true, moe_proba, baseline_proba)
        except Exception as e:
            logger.warning(f"  DeLong test failed: {e}")
            pvalue = 1.0

        significant = pvalue < 0.10

        return {
            "single_brain_oos_auc": float(baseline_auc),
            "moe_oos_auc": float(moe_auc),
            "improvement": float(improvement),
            "delong_pvalue": float(pvalue),
            "significant": bool(significant),
        }

    def _delong_test(self, y_true, proba1, proba2) -> float:
        """DeLong test for comparing two ROC curves (simplified bootstrap version)."""
        from sklearn.metrics import roc_auc_score

        # Bootstrap approach (simpler than full DeLong)
        n_bootstraps = 1000
        auc_diffs = []
        n = len(y_true)

        for _ in range(n_bootstraps):
            idx = np.random.randint(0, n, size=n)
            try:
                auc1 = roc_auc_score(y_true[idx], proba1[idx])
                auc2 = roc_auc_score(y_true[idx], proba2[idx])
                auc_diffs.append(auc1 - auc2)
            except ValueError:
                continue

        if not auc_diffs:
            return 1.0

        # Two-tailed test: is difference significantly different from 0?
        auc_diffs = np.array(auc_diffs)
        obs_diff = roc_auc_score(y_true, proba1) - roc_auc_score(y_true, proba2)

        # P-value: fraction of bootstrap samples with opposite sign
        if obs_diff >= 0:
            pvalue = (auc_diffs <= 0).mean()
        else:
            pvalue = (auc_diffs >= 0).mean()

        return float(pvalue * 2)  # two-tailed

    def _make_recommendation(self, results: dict) -> str:
        """Determine production recommendation based on criteria."""
        oos_auc = results["oos"]["auc"]
        ece = results["calibration"]["oos_ece"]

        vs_sb = results.get("vs_single_brain", {})
        baseline_auc = vs_sb.get("single_brain_oos_auc", 0.5278)
        improvement = vs_sb.get("improvement", 0.0)
        significant = vs_sb.get("significant", False)

        # DEPLOY: OOS AUC > 0.5310 AND statistically significant AND calibrated
        if oos_auc > 0.5310 and significant and ece < 0.03:
            return "DEPLOY"

        # RESEARCH: Beats baseline but not deploy criteria
        if oos_auc > baseline_auc and improvement > 0.0002:
            return "RESEARCH"

        # REJECT: Does not beat baseline
        return "REJECT"

    def _generate_plots(self, y_oos, oos_result, y_val, val_result, baseline_proba=None):
        """Generate all evaluation plots."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        sns.set_style("whitegrid")

        # ROC curve
        fpr, tpr, _ = roc_curve(y_oos, oos_result["proba"])
        auc = roc_auc_score(y_oos, oos_result["proba"])

        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, label=f"MoE (AUC={auc:.4f})", lw=2)
        if baseline_proba is not None:
            fpr_b, tpr_b, _ = roc_curve(y_oos, baseline_proba)
            auc_b = roc_auc_score(y_oos, baseline_proba)
            plt.plot(fpr_b, tpr_b, label=f"Single-Brain (AUC={auc_b:.4f})", lw=2, linestyle="--")
        plt.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.3)
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve — OOS")
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.plots_dir / "roc_curve.png", dpi=150)
        plt.close()

        # Calibration curve
        self.moe.calibrator.reliability_diagram(
            oos_result["proba"], y_oos,
            save_path=str(self.plots_dir / "calibration_curve.png")
        )

        # Routing distribution
        routing_weights = oos_result["routing_weights"]
        mean_weights = routing_weights.mean(axis=0)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Bar chart of mean routing weights
        from hydra.moe.feature_groups import EXPERT_NAMES
        ax1.bar(range(len(EXPERT_NAMES)), mean_weights, tick_label=EXPERT_NAMES)
        ax1.set_ylabel("Mean Routing Weight")
        ax1.set_title("Expert Routing Distribution (OOS)")
        ax1.grid(axis="y", alpha=0.3)

        # Histogram of routing entropy
        entropy = -np.sum(routing_weights * np.log(routing_weights + 1e-8), axis=1)
        ax2.hist(entropy, bins=50, edgecolor="black", alpha=0.7)
        ax2.axvline(entropy.mean(), color="red", linestyle="--", label=f"Mean={entropy.mean():.2f}")
        ax2.set_xlabel("Routing Entropy")
        ax2.set_ylabel("Count")
        ax2.set_title("Routing Confidence Distribution")
        ax2.legend()
        plt.tight_layout()
        plt.savefig(self.plots_dir / "routing_distribution.png", dpi=150)
        plt.close()

        # Confusion matrices
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for ax, (y, pred, title) in zip(axes, [
            (y_val, val_result["direction"], "Validation"),
            (y_oos, oos_result["direction"], "Out-of-Sample"),
        ]):
            cm = confusion_matrix(y, pred)
            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax, cbar=False)
            ax.set_xlabel("Predicted")
            ax.set_ylabel("True")
            ax.set_title(f"Confusion Matrix — {title}")
            ax.set_xticklabels(["Short", "Long"])
            ax.set_yticklabels(["Short", "Long"])
        plt.tight_layout()
        plt.savefig(self.plots_dir / "confusion_matrices.png", dpi=150)
        plt.close()

        # Rolling OOS AUC
        window = 10000
        if len(y_oos) > window:
            rolling_aucs = []
            for i in range(0, len(y_oos) - window, window // 2):
                end = min(i + window, len(y_oos))
                y_win = y_oos[i:end]
                p_win = oos_result["proba"][i:end]
                try:
                    auc_win = roc_auc_score(y_win, p_win)
                    rolling_aucs.append((i + window // 2, auc_win))
                except ValueError:
                    pass

            if rolling_aucs:
                indices, aucs = zip(*rolling_aucs)
                plt.figure(figsize=(12, 5))
                plt.plot(indices, aucs, marker="o", label="MoE Rolling AUC")
                plt.axhline(auc, color="red", linestyle="--", label=f"Overall AUC={auc:.4f}")
                plt.xlabel("Bar Index")
                plt.ylabel("AUC")
                plt.title(f"Rolling {window}-bar AUC (OOS)")
                plt.legend()
                plt.grid(alpha=0.3)
                plt.tight_layout()
                plt.savefig(self.plots_dir / "oos_rolling_auc.png", dpi=150)
                plt.close()

        logger.info(f"  Plots saved to {self.plots_dir}")
