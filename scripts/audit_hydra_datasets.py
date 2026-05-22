#!/usr/bin/env python3
"""Audit HYDRA datasets - resolve provenance confusion."""
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Try polars first, fallback to pandas
try:
    import polars as pl
    USE_POLARS = True
except ImportError:
    import pandas as pd
    USE_POLARS = False

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [
    REPO_ROOT / "data",
    REPO_ROOT / "datasets",
    REPO_ROOT / "runs",
    REPO_ROOT / "reports",
]

HYDRA_PATTERNS = ["hydra", "xauusd", "m5", "gold"]
REPORT_DIRS = [REPO_ROOT / "reports", REPO_ROOT / "logs"]


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_dataset(path: Path):
    """Load dataset with polars or pandas."""
    if USE_POLARS:
        if path.suffix == ".parquet":
            return pl.scan_parquet(path).collect()
        else:
            return pl.read_csv(path)
    else:
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        else:
            return pd.read_csv(path)


def detect_time_column(df):
    """Detect timestamp column."""
    if USE_POLARS:
        for col in df.columns:
            if col.lower() in ["timestamp", "time", "datetime", "date", "ts"]:
                return col
            dtype = df[col].dtype
            if dtype in [pl.Datetime, pl.Date]:
                return col
    else:
        for col in df.columns:
            if col.lower() in ["timestamp", "time", "datetime", "date", "ts"]:
                return col
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
    return None


def analyze_dataset(path: Path) -> dict:
    """Analyze a single dataset."""
    try:
        stat = path.stat()
        size_mb = stat.st_size / 1024 / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

        df = load_dataset(path)

        if USE_POLARS:
            nrows = df.height
            ncols = df.width
            columns = df.columns
        else:
            nrows = len(df)
            ncols = len(df.columns)
            columns = df.columns.tolist()

        time_col = detect_time_column(df)

        # Detect min/max timestamp
        min_ts = max_ts = None
        if time_col:
            if USE_POLARS:
                min_ts = str(df[time_col].min())
                max_ts = str(df[time_col].max())
            else:
                min_ts = str(df[time_col].min())
                max_ts = str(df[time_col].max())

        # Count column types
        label_cols = [c for c in columns if "label" in c.lower() or "fwd_ret" in c.lower()]
        numeric_cols = []
        if USE_POLARS:
            numeric_cols = [c for c in columns if df[c].dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Float32, pl.Float64]]
        else:
            numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]

        feature_cols = [c for c in numeric_cols if c not in label_cols and c != time_col]

        # Null percentage
        null_pcts = {}
        for col in columns[:20]:  # Top 20
            if USE_POLARS:
                null_pct = (df[col].null_count() / nrows) * 100 if nrows > 0 else 0
            else:
                null_pct = (df[col].isna().sum() / nrows) * 100 if nrows > 0 else 0
            null_pcts[col] = null_pct

        # Constant columns
        constant_cols = []
        for col in numeric_cols:
            if USE_POLARS:
                nunique = df[col].n_unique()
            else:
                nunique = df[col].nunique()
            if nunique <= 1:
                constant_cols.append(col)

        # Placeholder columns (all zeros or constant)
        placeholder_cols = constant_cols.copy()

        # Hash
        file_hash = sha256_file(path)

        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "size_mb": round(size_mb, 2),
            "modified": modified,
            "row_count": nrows,
            "column_count": ncols,
            "time_column": time_col,
            "min_timestamp": min_ts,
            "max_timestamp": max_ts,
            "numeric_columns": len(numeric_cols),
            "label_columns": len(label_cols),
            "feature_columns": len(feature_cols),
            "null_pcts_top20": {k: round(v, 2) for k, v in list(null_pcts.items())[:20]},
            "constant_columns": len(constant_cols),
            "placeholder_columns": len(placeholder_cols),
            "sha256_prefix": file_hash,
            "columns_sample": columns[:10],
        }
    except Exception as e:
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "error": str(e),
        }


def search_reports_logs() -> dict:
    """Search reports/logs for overnight pipeline evidence."""
    evidence = {
        "dukascopy_refs": [],
        "850k_refs": [],
        "5500_refs": [],
        "feature_build_refs": [],
        "hydra_m5_refs": [],
        "gate_refs": [],
    }

    for report_dir in REPORT_DIRS:
        if not report_dir.exists():
            continue

        for file_path in report_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix not in [".txt", ".md", ".log", ".json"]:
                continue

            try:
                content = file_path.read_text(errors="ignore")

                if "dukascopy" in content.lower():
                    evidence["dukascopy_refs"].append(str(file_path.relative_to(REPO_ROOT)))

                if "850k" in content or "850000" in content or "850_000" in content:
                    evidence["850k_refs"].append(str(file_path.relative_to(REPO_ROOT)))

                if "5500" in content or "5,500" in content:
                    evidence["5500_refs"].append(str(file_path.relative_to(REPO_ROOT)))

                if "feature" in content.lower() and "build" in content.lower():
                    evidence["feature_build_refs"].append(str(file_path.relative_to(REPO_ROOT)))

                if "hydra" in content.lower() and "m5" in content.lower():
                    evidence["hydra_m5_refs"].append(str(file_path.relative_to(REPO_ROOT)))

                if "gate" in content.lower() or "PASS" in content or "BLOCKED" in content:
                    evidence["gate_refs"].append(str(file_path.relative_to(REPO_ROOT)))
            except:
                pass

    # Deduplicate
    for key in evidence:
        evidence[key] = list(set(evidence[key]))[:10]  # Top 10

    return evidence


def generate_markdown(datasets: list, evidence: dict) -> str:
    """Generate markdown report."""
    lines = [
        "# HYDRA Dataset Provenance Audit",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Engine:** {'Polars' if USE_POLARS else 'Pandas'}",
        "",
        "## Summary",
        "",
        f"- **Datasets found:** {len(datasets)}",
    ]

    if datasets:
        valid = [d for d in datasets if "error" not in d]
        if valid:
            newest = max(valid, key=lambda d: d["modified"])
            largest_rows = max(valid, key=lambda d: d["row_count"])
            largest_cols = max(valid, key=lambda d: d["column_count"])

            lines.extend([
                f"- **Newest:** `{newest['path']}` ({newest['modified']})",
                f"- **Largest (rows):** `{largest_rows['path']}` ({largest_rows['row_count']:,} rows)",
                f"- **Largest (cols):** `{largest_cols['path']}` ({largest_cols['column_count']:,} cols)",
            ])

    lines.extend([
        "",
        "## Datasets",
        "",
    ])

    for ds in datasets:
        if "error" in ds:
            lines.append(f"### ❌ {ds['path']}")
            lines.append(f"**Error:** {ds['error']}")
            lines.append("")
            continue

        lines.extend([
            f"### {ds['path']}",
            "",
            f"- **Size:** {ds['size_mb']:.2f} MB",
            f"- **Modified:** {ds['modified']}",
            f"- **Rows:** {ds['row_count']:,}",
            f"- **Columns:** {ds['column_count']:,}",
            f"  - Numeric: {ds['numeric_columns']}",
            f"  - Labels: {ds['label_columns']}",
            f"  - Features: {ds['feature_columns']}",
            f"- **Time column:** {ds['time_column'] or 'N/A'}",
            f"- **Time range:** {ds['min_timestamp'] or 'N/A'} → {ds['max_timestamp'] or 'N/A'}",
            f"- **Constant columns:** {ds['constant_columns']}",
            f"- **Placeholder columns:** {ds['placeholder_columns']}",
            f"- **SHA256 prefix:** {ds['sha256_prefix']}",
            f"- **Columns sample:** {', '.join(ds['columns_sample'][:5])}...",
            "",
        ])

    lines.extend([
        "## Overnight Pipeline Evidence",
        "",
    ])

    for key, refs in evidence.items():
        lines.append(f"### {key.replace('_', ' ').title()}")
        if refs:
            for ref in refs:
                lines.append(f"- `{ref}`")
        else:
            lines.append("- (none)")
        lines.append("")

    return "\n".join(lines)


def main():
    print("="*60)
    print("HYDRA DATASET PROVENANCE AUDIT")
    print("="*60)
    print()

    # Find datasets
    datasets = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue

        for path in scan_dir.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix not in [".parquet", ".csv"]:
                continue

            # Check if HYDRA-like
            name_lower = path.name.lower()
            if not any(pattern in name_lower for pattern in HYDRA_PATTERNS):
                continue

            print(f"Analyzing: {path.relative_to(REPO_ROOT)}")
            ds = analyze_dataset(path)
            datasets.append(ds)

    print()
    print(f"Found {len(datasets)} HYDRA-like datasets")
    print()

    # Search reports/logs
    print("Searching reports/logs for overnight pipeline evidence...")
    evidence = search_reports_logs()
    print()

    # Generate outputs
    json_path = REPO_ROOT / "reports" / "hydra_dataset_provenance.json"
    md_path = REPO_ROOT / "reports" / "hydra_dataset_provenance.md"

    json_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON
    output = {
        "generated": datetime.now().isoformat(),
        "engine": "polars" if USE_POLARS else "pandas",
        "datasets": datasets,
        "overnight_evidence": evidence,
    }

    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"JSON saved: {json_path.relative_to(REPO_ROOT)}")

    # Markdown
    md_content = generate_markdown(datasets, evidence)
    with open(md_path, "w") as f:
        f.write(md_content)

    print(f"Markdown saved: {md_path.relative_to(REPO_ROOT)}")
    print()

    # Console summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print()

    valid = [d for d in datasets if "error" not in d]
    if valid:
        newest = max(valid, key=lambda d: d["modified"])
        largest_rows = max(valid, key=lambda d: d["row_count"])
        largest_cols = max(valid, key=lambda d: d["column_count"])

        print(f"Newest dataset:")
        print(f"  {newest['path']}")
        print(f"  {newest['row_count']:,} rows × {newest['column_count']:,} cols")
        print(f"  {newest['modified']}")
        print()

        print(f"Largest dataset (rows):")
        print(f"  {largest_rows['path']}")
        print(f"  {largest_rows['row_count']:,} rows")
        print()

        print(f"Largest dataset (columns):")
        print(f"  {largest_cols['path']}")
        print(f"  {largest_cols['column_count']:,} cols")
        print()
    else:
        print("No valid datasets found.")
        print()

    # 850K / 5500 check
    has_850k = any("850k" in d.get("path", "").lower() or d.get("row_count", 0) > 800000 for d in valid)
    has_5500 = any(d.get("column_count", 0) > 5000 for d in valid)

    print(f"850K row dataset exists: {'YES' if has_850k else 'NO'}")
    print(f"5500+ feature dataset exists: {'YES' if has_5500 else 'NO'}")
    print()

    if evidence["dukascopy_refs"]:
        print(f"Dukascopy references: {len(evidence['dukascopy_refs'])} files")

    if evidence["850k_refs"]:
        print(f"850K references: {len(evidence['850k_refs'])} files")

    if evidence["5500_refs"]:
        print(f"5500 references: {len(evidence['5500_refs'])} files")

    if evidence["feature_build_refs"]:
        print(f"Feature build references: {len(evidence['feature_build_refs'])} files")

    print()
    print("="*60)


if __name__ == "__main__":
    main()
