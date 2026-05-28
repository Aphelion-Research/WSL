# GPU Training Quick Start (H200)

## Setup (30 seconds)

```bash
git clone https://github.com/YOUR_USERNAME/Dominion.git
cd Dominion
pip install -r requirements_gpu.txt
```

## Run Training

```bash
python scripts/train_multi_style_gpu_h200.py /path/to/hydra_xauusd_feature_fabric_v1.parquet --output-dir ./output
```

## Output

- `output/training_report_gpu.json` - Full metrics
- `output/model_comparison.png` - 4-panel visualization

## What It Does

- Loads 4.1GB dataset (647 features, 789K samples)
- Trains 10 XGBoost GPU models (3 styles: scalper/day/swing)
- Class-weighted training + early stopping
- Full metrics: accuracy, precision, recall, F1, confusion matrix
- Top 10 feature importance per model
- Ranking table sorted by F1

## Models Trained

1. **Scalper (5 bars = 25 min)**: Fast, Deep, Aggressive
2. **Day Trader (72 bars = 6 hours)**: Fast, Deep, Aggressive  
3. **Swing Trader (288 bars = 24 hours)**: Fast, Deep
4. **Multi-Style (all horizons)**: Light, Deep

## H200 Optimizations

- float32 precision (full GPU bandwidth)
- max_bin=512 (H200 can handle it)
- gpu_hist tree method
- Class-weighted training
- Early stopping (patience=50)

## Expected Time

~10-20 minutes on H200 for all 10 models
