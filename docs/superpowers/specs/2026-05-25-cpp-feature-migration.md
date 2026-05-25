# C++ Feature Engineering Migration

**Date:** 2026-05-25  
**Target:** 2000+ features, <8min backtest, <300μs real-time

## Architecture

```
dominion_cpp/src/features/
├── noise/          SSA, EMD, VMD, wavelets
├── information/    Entropy, transfer entropy, mutual info
├── multifractal/   MFDFA, Hurst, fractal dimension
├── microstructure/ Hansen-Lunde, TSRV, efficient price
├── jumps/          Lee-Mykland, BNS, Hawkes
├── stochastic_vol/ Heston, SABR, rough vol (QuantLib)
├── causal/         Granger, CCM, DAG learning
├── topology/       Persistent homology (GUDHI)
├── network/        Graph centrality (igraph)
├── copulas/        Tail dependence, time-varying
├── recurrence/     RQA, cross-recurrence
├── ml/             Autoencoders, denoising
├── quantum/        Tensor networks (ITensor)
├── orderflow/      VPIN, Kyle's lambda, adverse selection
└── primitives/     Rolling stats (Eigen SIMD)
```

## Dependencies

- **Core:** Eigen3, Intel MKL, OpenMP
- **Quant:** QuantLib, FFTW3, TA-Lib
- **Advanced:** GUDHI, igraph, ITensor
- **GPU:** DirectML (WSL iGPU)
- **Bindings:** pybind11

## Feature Categories (2000+)

1. **Noise decomposition (150):** SSA, EMD, VMD modes, energy ratios, crossing frequencies
2. **Information theory (120):** Permutation/sample/approximate entropy, transfer entropy, mutual info, complexity
3. **Multifractal (100):** MFDFA, Hurst, fractal dimension, Hölder exponents, singularity spectrum
4. **Microstructure noise (80):** Hansen-Lunde, pre-averaging, TSRV, efficient price, signal-to-noise
5. **Jump detection (70):** Lee-Mykland, BNS, bipower variation, Hawkes intensity
6. **Stochastic vol (150):** Heston params (kappa, theta, sigma), SABR, rough vol, realized GARCH
7. **Causal (100):** PC, GES, LiNGAM, rolling Granger, CCM
8. **TDA (60):** Betti numbers, persistence lifetimes, Wasserstein distance
9. **Order flow (120):** VPIN, OFI, Kyle's lambda, adverse selection
10. **Network (90):** Centrality, MST, community detection
11. **Copulas (80):** Gaussian/t/Clayton/Gumbel, tail dependence
12. **Recurrence (70):** Recurrence rate, determinism, laminarity
13. **ML denoising (100):** Autoencoder features, noise residuals, stability scores
14. **Quantum (50):** Tensor rank, entanglement entropy
15. **Primitives (600):** Rolling mean/std/skew/kurt, correlations, returns (many windows)

## CPU/GPU Split

**CPU:** Sequential features, model fitting, causal inference, real-time critical path  
**GPU (DirectML):** Matrix ops, correlations, FFT, PCA, network algorithms

## Performance Targets

- Batch backtest: <8min (9 years, 1M+ bars)
- Real-time update: <300μs
- Training rebuild: <4min
- Cache: 20GB mmap

## Point-in-Time Safety

All features shift by 1: feature[t] uses only data ≤ t-1. Automated tests verify no lookahead.

## Python Interface

```python
import dominion.features as df

# Batch
features = df.compute_all(bars, mode='batch', cpu_threads=20, use_gpu=True)

# Real-time
engine = df.RealtimeEngine()
for tick in stream:
    features = engine.update(tick)
```
