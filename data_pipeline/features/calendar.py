"""Calendar and seasonality features."""
import numpy as np
import pandas as pd
from datetime import datetime


def compute_day_of_week(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute day of week one-hot encoding."""
    features = pd.DataFrame(index=timestamps)

    dow = timestamps.dayofweek  # 0=Monday, 4=Friday

    for i in range(5):
        features[f"dow_{i}"] = (dow == i).astype(int)

    return features


def compute_week_of_month(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute week of month."""
    features = pd.DataFrame(index=timestamps)

    features["week_of_month"] = (timestamps.day - 1) // 7 + 1

    return features


def compute_month_of_year(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute month one-hot encoding."""
    features = pd.DataFrame(index=timestamps)

    month = timestamps.month

    for i in range(1, 13):
        features[f"month_{i}"] = (month == i).astype(int)

    return features


def compute_quarter(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute quarter one-hot encoding."""
    features = pd.DataFrame(index=timestamps)

    quarter = timestamps.quarter

    for i in range(1, 5):
        features[f"quarter_{i}"] = (quarter == i).astype(int)

    return features


def compute_month_end(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute month-end indicator (last 5 trading days)."""
    features = pd.DataFrame(index=timestamps)

    # Approximate: days 25-31 of month
    features["is_month_end"] = (timestamps.day >= 25).astype(int)

    return features


def compute_quarter_end(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute quarter-end indicator."""
    features = pd.DataFrame(index=timestamps)

    features["is_quarter_end"] = (
        ((timestamps.month == 3) | (timestamps.month == 6) |
         (timestamps.month == 9) | (timestamps.month == 12)) &
        (timestamps.day >= 25)
    ).astype(int)

    return features


def compute_options_expiry(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute days until options expiry (3rd Friday of month)."""
    features = pd.DataFrame(index=timestamps)

    days_to_expiry = []
    for ts in timestamps:
        # Find 3rd Friday
        year, month = ts.year, ts.month
        first_day = datetime(year, month, 1)
        first_friday = (4 - first_day.weekday()) % 7 + 1  # First Friday
        third_friday_day = first_friday + 14

        try:
            third_friday = datetime(year, month, third_friday_day)
        except ValueError:
            # Month doesn't have that many days
            days_to_expiry.append(np.nan)
            continue

        delta = (third_friday - ts).days

        if delta < 0:
            # Already passed, find next month
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            first_day = datetime(next_year, next_month, 1)
            first_friday = (4 - first_day.weekday()) % 7 + 1
            third_friday_day = first_friday + 14
            try:
                third_friday = datetime(next_year, next_month, third_friday_day)
                delta = (third_friday - ts).days
            except ValueError:
                delta = np.nan

        days_to_expiry.append(delta)

    features["days_to_expiry"] = days_to_expiry

    return features


def compute_seasonal_demand(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute seasonal gold demand indicators."""
    features = pd.DataFrame(index=timestamps)

    month = timestamps.month

    # Q4 demand (Oct-Dec): India/China wedding/New Year buying
    features["seasonal_q4"] = ((month >= 10) & (month <= 12)).astype(int)

    # Ramadan indicator (approximate, varies by year)
    # Placeholder: assume March-April
    features["seasonal_ramadan"] = ((month >= 3) & (month <= 4)).astype(int)

    return features


def compute_all_calendar_features(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute all calendar features (~30 features)."""
    all_features = [
        compute_day_of_week(timestamps),
        compute_week_of_month(timestamps),
        compute_month_of_year(timestamps),
        compute_quarter(timestamps),
        compute_month_end(timestamps),
        compute_quarter_end(timestamps),
        compute_options_expiry(timestamps),
        compute_seasonal_demand(timestamps),
    ]

    return pd.concat(all_features, axis=1)
