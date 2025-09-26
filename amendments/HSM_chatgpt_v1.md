# Amendments v1 — HSM_chatgpt
## Targets (≤3)
1) Under/over-dispersion at mid horizons → adjust NGR variance prior / regularization.
2) Leakage guard → enforce origin cutoffs in feature builder (no t>origin).
3) Tail undercoverage → add split-conformal tails (CQR/quantile smoothing) on residuals.

## Rationale & Expected Effect
- CRPS: + (lower is better)
- Brier: +
- Coverage error: ↓ (toward nominal)
## Code/Config touchpoints
- models/HSM_chatgpt/code/*
- calibrate/emos_ngr.py (hyperparams)
- calibrate/conformal.py (enable tails)
## Complexity Count (P): +1
