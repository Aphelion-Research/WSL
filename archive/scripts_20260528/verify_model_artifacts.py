#!/usr/bin/env python3
"""Verify HYDRA model artifacts."""
import json
import os
from pathlib import Path

def check_artifact(model_path):
    """Check single model artifact."""
    print(f"\n=== {model_path} ===")

    model_exists = Path(model_path).exists()
    meta_path = model_path + ".meta.json"
    meta_exists = Path(meta_path).exists()

    # Check for zombie artifact
    if meta_exists and not model_exists:
        print(f"ZOMBIE_ARTIFACT: Metadata exists but model missing")
        print(f"  .meta.json: {meta_path}")
        print(f"  .bin: {model_path} (MISSING)")
        return False

    if not model_exists:
        print(f"MISSING: {model_path}")
        return False

    size = os.path.getsize(model_path)
    print(f"Model file: exists, size={size} bytes")

    if size == 0:
        print("ERROR: Model file is empty")
        return False

    if not meta_exists:
        print(f"MISSING: {meta_path}")
        return False

    print(f"Metadata file: exists")

    try:
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        required = [
            "model_name",
            "model_type",
            "direction_mode",
            "n_features",
            "selected_feature_indices",
            "normalization_means",
            "normalization_stds",
            "threshold_long",
            "threshold_short",
            "model_edge_verdict",
            "model_excess_return_pct",
        ]

        missing = [k for k in required if k not in meta]
        if missing:
            print(f"ERROR: Missing metadata keys: {missing}")
            return False

        print(f"  model_name: {meta['model_name']}")
        print(f"  model_type: {meta['model_type']}")
        print(f"  direction_mode: {meta['direction_mode']}")
        print(f"  n_features: {meta['n_features']}")
        print(f"  selected_features: {len(meta['selected_feature_indices'])} indices")
        print(f"  normalization: {len(meta['normalization_means'])} means, {len(meta['normalization_stds'])} stds")
        print(f"  threshold_long: {meta['threshold_long']}")
        print(f"  threshold_short: {meta['threshold_short']}")
        print(f"  edge_verdict: {meta['model_edge_verdict']}")
        print(f"  excess_return: {meta['model_excess_return_pct'] * 100:.2f}%")

        if len(meta['selected_feature_indices']) == 0:
            print("ERROR: No selected features")
            return False

        if meta['model_type'] not in ['logistic', 'conservative', 'passive_aggressive']:
            print(f"WARNING: Unsupported model type: {meta['model_type']}")

        print("VALID")
        return True

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("HYDRA Model Artifact Verification")
    print("=" * 60)

    long_model = "runs/models/hydra_long.bin"
    short_model = "runs/models/hydra_short.bin"

    long_valid = check_artifact(long_model)
    short_valid = check_artifact(short_model)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Long specialist: {'VALID' if long_valid else 'INVALID'}")
    print(f"Short specialist: {'VALID' if short_valid else 'INVALID'}")

    if long_valid and short_valid:
        print("\nAll artifacts verified successfully!")
        return 0
    else:
        print("\nSome artifacts missing or invalid.")
        return 1


if __name__ == "__main__":
    exit(main())
