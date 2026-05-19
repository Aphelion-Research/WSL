"""Multi-timescale Kalman filter bank for price fusion."""
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime

from data_pipeline.config import KALMAN_FILTERS


class KalmanFilter:
    """Single Kalman filter for price estimation."""

    def __init__(self, process_noise: float, observation_noise: float):
        """Initialize 2D Kalman filter (price + velocity).

        Args:
            process_noise: Process noise covariance (Q)
            observation_noise: Observation noise covariance (R)
        """
        # State: [price, velocity]
        self.x = np.array([0.0, 0.0])  # Initial state
        self.P = np.eye(2) * 1000.0  # Initial covariance (high uncertainty)

        # State transition matrix (constant velocity model)
        self.F = np.array([[1.0, 1.0], [0.0, 1.0]])

        # Observation matrix (we observe only price)
        self.H = np.array([[1.0, 0.0]])

        # Process noise covariance
        self.Q = np.eye(2) * process_noise

        # Observation noise covariance
        self.R = np.array([[observation_noise]])

        self.initialized = False

    def predict(self) -> Tuple[float, float]:
        """Prediction step.

        Returns:
            (predicted_price, uncertainty)
        """
        # Predict state
        self.x = self.F @ self.x

        # Predict covariance
        self.P = self.F @ self.P @ self.F.T + self.Q

        return self.x[0], self.P[0, 0]

    def update(self, observation: float, trust: float = 1.0) -> Tuple[float, float, float]:
        """Update step.

        Args:
            observation: Observed price
            trust: Trust score for this observation (0-1)

        Returns:
            (filtered_price, uncertainty, innovation)
        """
        if not self.initialized:
            # Initialize state with first observation
            self.x[0] = observation
            self.initialized = True
            return observation, self.P[0, 0], 0.0

        # Compute innovation
        y = observation - (self.H @ self.x)[0]

        # Innovation covariance (weighted by trust)
        S = (self.H @ self.P @ self.H.T + self.R / trust)[0, 0]

        # Kalman gain
        K = (self.P @ self.H.T) / S

        # Update state
        self.x = self.x + K.flatten() * y

        # Update covariance
        self.P = (np.eye(2) - K @ self.H) @ self.P

        return self.x[0], self.P[0, 0], abs(y)


class KalmanFilterBank:
    """Bank of Kalman filters at different timescales."""

    def __init__(self):
        """Initialize filter bank."""
        self.filters: Dict[str, KalmanFilter] = {}
        for name, params in KALMAN_FILTERS.items():
            self.filters[name] = KalmanFilter(
                process_noise=params["process_noise"],
                observation_noise=params["observation_noise"],
            )

        # Trust scores for each source
        self.trust_scores: Dict[str, float] = {}

    def init_trust(self, source: str, initial_trust: float = 0.5) -> None:
        """Initialize trust score for a source."""
        self.trust_scores[source] = max(0.05, min(0.95, initial_trust))

    def update_trust(self, source: str, innovation: float, uncertainty: float) -> float:
        """Update trust score based on innovation residual.

        Args:
            source: Source name
            innovation: Absolute innovation from Kalman filter
            uncertainty: Current uncertainty estimate

        Returns:
            Updated trust score
        """
        if source not in self.trust_scores:
            self.init_trust(source)

        # Compute z-score of innovation
        if uncertainty > 0:
            z_score = innovation / np.sqrt(uncertainty)
        else:
            z_score = 0.0

        # Update trust
        if z_score < 1.0:
            # Good agreement -> increase trust
            self.trust_scores[source] = min(0.95, self.trust_scores[source] + 0.01)
        elif z_score > 3.0:
            # High disagreement -> decrease trust
            self.trust_scores[source] = max(0.05, self.trust_scores[source] - 0.05)

        return self.trust_scores[source]

    def fuse(
        self,
        observations: Dict[str, float],
        timestamp: datetime,
    ) -> Tuple[float, float, Dict[str, float], bool]:
        """Fuse multiple observations via filter bank.

        Args:
            observations: Dict mapping source -> price
            timestamp: Current timestamp

        Returns:
            (fused_price, confidence, source_weights, anomaly_flag)
        """
        # Initialize trust for new sources
        for source in observations:
            if source not in self.trust_scores:
                self.init_trust(source)

        # Predict step for all filters
        predictions = {}
        for name, filt in self.filters.items():
            pred_price, pred_unc = filt.predict()
            predictions[name] = (pred_price, pred_unc)

        # Update each filter with trusted observations
        filter_outputs = {}
        source_innovations = {}

        for source, obs in observations.items():
            trust = self.trust_scores[source]

            for name, filt in self.filters.items():
                filtered_price, uncertainty, innovation = filt.update(obs, trust)
                if name not in filter_outputs:
                    filter_outputs[name] = []
                filter_outputs[name].append((filtered_price, uncertainty))

                # Track innovation for trust update
                source_innovations[source] = (innovation, uncertainty)

        # Update trust scores
        for source, (innov, unc) in source_innovations.items():
            self.update_trust(source, innov, unc)

        # Fuse filter outputs (weighted by inverse uncertainty)
        fused_prices = []
        weights = []

        for name, outputs in filter_outputs.items():
            # Average across all observations for this filter
            avg_price = np.mean([p for p, u in outputs])
            avg_unc = np.mean([u for p, u in outputs])

            if avg_unc > 0:
                weight = 1.0 / avg_unc
            else:
                weight = 1.0

            fused_prices.append(avg_price * weight)
            weights.append(weight)

        # Final fused price
        total_weight = sum(weights)
        if total_weight > 0:
            fused_price = sum(fused_prices) / total_weight
            confidence = total_weight  # Higher weight = higher confidence
        else:
            fused_price = np.mean(list(observations.values()))
            confidence = 0.1

        # Anomaly detection: check if any source diverges >3σ
        anomaly_flag = False
        for source, obs in observations.items():
            if abs(obs - fused_price) > 3.0 * np.sqrt(1.0 / confidence):
                anomaly_flag = True
                break

        # Source weights (normalized trust scores)
        total_trust = sum(self.trust_scores[s] for s in observations)
        if total_trust > 0:
            source_weights = {s: self.trust_scores[s] / total_trust for s in observations}
        else:
            source_weights = {s: 1.0 / len(observations) for s in observations}

        return fused_price, confidence, source_weights, anomaly_flag
