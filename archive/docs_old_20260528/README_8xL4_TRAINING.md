# 100 Model Training - 8x L4 GPUs

## Hardware Specs
- **GPUs:** 8x NVIDIA L4
- **vCPUs:** 96
- **RAM:** 384GB
- **Strategy:** Sequential training with round-robin GPU assignment

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/Dominion.git
cd Dominion
pip install -r requirements_gpu.txt
pip install GPUtil  # For GPU monitoring

# Run training
python scripts/train_100_models_8xL4.py /path/to/hydra_xauusd_feature_fabric_v1.parquet --output-dir ./output_100models
```

## What It Does

Trains **100 diverse XGBoost models** across 3 trading styles:
- **30 Scalper models** (5 bars = 25 min)
- **35 Day Trader models** (72 bars = 6 hours)
- **25 Swing Trader models** (288 bars = 24 hours)
- **10 Multi-Style models** (all horizons)

### Model Variety
- Depths: 10-40
- Learning rates: 0.01, 0.02, 0.03, 0.05
- Tree counts: 600-1400
- Subsample rates: 0.8-0.95
- Column sample rates: 0.8-0.9

## GPU Utilization Strategy

- **Round-robin assignment:** Model N assigned to GPU (N-1) % 8
- **12 threads per model:** 96 vCPUs / 8 GPUs = 12 threads
- **Max bins:** 512 (L4 optimized)
- **Full float32 precision** (no compromises)
- **Sequential training** (1 model at a time for stability)

## Live Logging

Real-time output shows:
- Timestamp on every line
- Current model ID, name, hyperparams
- Assigned GPU (0-7)
- Training progress bar per model
- Test metrics immediately after completion
- Progress summary every 10 models
- GPU load & VRAM usage per model

## Outputs

### Per Model
- `output_100models/result_001.json` through `result_100.json`

### Final Report
- `output_100models/training_report_100models.json`
  - Top 20 models ranked by F1
  - Best model per style
  - Full statistics (mean, std, min, max F1)
  - All 100 model results

### Visualizations
- `output_100models/100models_analysis.png`
  - Top 30 F1 bar chart
  - F1 distribution histogram
  - Training time vs F1 scatter
  - Style comparison boxplot

## Expected Performance

- **Time:** 15-30 minutes total (10-20s per model avg)
- **Throughput:** ~200-400 models/hour
- **F1 Range:** 0.50-0.65 (typical for financial data)
- **GPU Load:** 80-95% per assigned GPU during training
- **VRAM Usage:** 8-12GB per GPU

## Progress Tracking

Watch output for:
```
[HH:MM:SS] MODEL 1/100 [ID=1]: Scalper_D10_LR1
[HH:MM:SS]   Assigned GPU: 0/8
[HH:MM:SS]   Training 700 trees on GPU 0...
  GPU0 Scalper_D10_LR1: 100%|███████| 700/700 [00:15<00:00, 45tree/s, loss=0.8234]
[HH:MM:SS]   ✓ Complete: 15.3s | Best iter: 650/700
[HH:MM:SS]     Test Acc: 0.5234 | F1: 0.5189 | Prec: 0.5156 | Rec: 0.5234
[HH:MM:SS]     GPU0: 92% load, 78% VRAM
```

Every 10 models:
```
[HH:MM:SS]   Progress: 10/100 models complete
[HH:MM:SS]   Avg F1: 0.5234 | Best F1: 0.5456
[HH:MM:SS]   Avg time: 17.2s/model
```

## Tips

- **Monitor:** `watch -n 1 nvidia-smi` in separate terminal
- **Logs:** Pipe to file: `python script.py ... | tee training.log`
- **Resume:** Script saves incrementally - check existing result_*.json files
- **Memory:** Should use ~20-30GB RAM, ~80GB VRAM total across 8 GPUs
