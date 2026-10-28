# ADR 0002: Mandated Seasonal-Naive Baseline Benchmark

## Status
Accepted

## Context
Time-series forecasting models often claim high accuracy without empirical comparison against simple statistical baselines. In tourism demand, weekly (7-day) and annual (12-month) cyclicalities are prominent. Overly complex neural or autoregressive models risk overfitting without delivering actionable accuracy improvements over a simple seasonal repeat.

## Decision
We mandate that:
1. Every forecast execution must fit and evaluate a **Seasonal-Naive baseline** ($y_t = y_{t-m}$, where $m=7$ for daily data).
2. Train-validation partitioning must strictly adhere to **chronological ordering** without random observation shuffling.
3. Candidate models are evaluated using both **Mean Absolute Error (MAE)** and **Mean Absolute Scaled Error (MASE)** against in-sample seasonal naive errors.
4. The user interface must explicitly display whether the candidate model won or lost against the seasonal naive benchmark.

## Consequences
- **Positive**: Complete transparency, avoidance of false algorithmic superiority claims, and robust performance benchmarking.
- **Negative**: Simple datasets with low variance may show candidate models failing to beat the naive baseline, requiring analyst awareness.
