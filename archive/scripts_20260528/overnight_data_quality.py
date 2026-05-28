#!/usr/bin/env python3
"""Data quality analysis overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
import json

DATASETS = [
    "data/hydra_xauusd_m5_master.parquet",
    "data/hydra_xauusd_m5_3k.parquet",
]
OUTPUT = Path("runs/data_quality_report.json")


def analyze_quality(filepath):
    """Full data quality analysis."""
    df = pd.read_parquet(filepath)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    report = {
        'file': filepath,
        'total_rows': len(df),
        'total_cols': len(df.columns),
        'feature_cols': len(feature_cols),
        'label_cols': len(label_cols),
        'date_range': f"{df.index.min()} to {df.index.max()}",
        'missing_values': {},
        'zero_variance': [],
        'high_correlation': [],
        'outliers': {},
        'feature_stats': {}
    }

    print(f"\nAnalyzing: {filepath}")
    print(f"  Rows: {len(df):,} | Features: {len(feature_cols)}")

    # Missing values
    print("  Checking missing values...")
    for col in feature_cols[:100]:  # Sample
        missing_pct = df[col].isna().sum() / len(df) * 100
        if missing_pct > 5:
            report['missing_values'][col] = f"{missing_pct:.1f}%"

    # Zero variance
    print("  Checking variance...")
    for col in feature_cols:
        if df[col].std() < 1e-10:
            report['zero_variance'].append(col)

    # Correlation
    print("  Checking correlations...")
    corr_sample = df[feature_cols[:200]].corr().abs()
    high_corr_pairs = []
    for i in range(len(corr_sample.columns)):
        for j in range(i+1, len(corr_sample.columns)):
            if corr_sample.iloc[i, j] > 0.95:
                high_corr_pairs.append(
                    (corr_sample.columns[i], corr_sample.columns[j], corr_sample.iloc[i, j])
                )
    report['high_correlation'] = [
        f"{c1} <-> {c2}: {v:.3f}" for c1, c2, v in high_corr_pairs[:20]
    ]

    # Outliers
    print("  Checking outliers...")
    for col in feature_cols[:50]:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        outliers = ((df[col] < q1 - 3*iqr) | (df[col] > q3 + 3*iqr)).sum()
        if outliers > 0:
            report['outliers'][col] = int(outliers)

    # Feature stats
    print("  Computing stats...")
    for col in feature_cols[:20]:
        report['feature_stats'][col] = {
            'mean': float(df[col].mean()),
            'std': float(df[col].std()),
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'skew': float(df[col].skew()),
            'kurt': float(df[col].kurt())
        }

    return report


def main():
    all_reports = []

    for dataset_path in DATASETS:
        if Path(dataset_path).exists():
            report = analyze_quality(dataset_path)
            all_reports.append(report)

    with open(OUTPUT, 'w') as f:
        json.dump(all_reports, f, indent=2)

    print(f"\n{'='*60}")
    print("DATA QUALITY ANALYSIS COMPLETE")
    print(f"{'='*60}")
    for report in all_reports:
        print(f"\nFile: {report['file']}")
        print(f"  Rows: {report['total_rows']:,}")
        print(f"  Features: {report['feature_cols']}")
        print(f"  Zero variance: {len(report['zero_variance'])}")
        print(f"  High correlation pairs: {len(report['high_correlation'])}")
        print(f"  Features with >5% missing: {len(report['missing_values'])}")

    print(f"\nFull report: {OUTPUT}")


if __name__ == "__main__":
    main()
