models/FSM_grok/model_card.md
FSM Grok Model Card

Type: Random walk with drift and Poisson shocks (t-distributed, df=4)
Complexity (P): 12 (mean, drift, sigma, shock params for 3 indicators)
Indicators: mass_public_polarization (affective), public_trust_government, vep_turnout_pres_pct
Training: Post-1985, min 8 years history
Preprocessing: UTF-8, YE resampling, carry-forward imputation, z-score normalization
Leakage Controls: Vintage 2025-08-21/22/24
Breaks: Shocks calibrated to historical breaks (e.g., 2015)
Calibration: Mean-adjusted, sigma-scaled, PIT verified (50/90% coverage)
Outputs: q05/q50/q95 in scenarios.csv, event_probs.csv, diagnostics.csv
Notes: ECC via GaussianCopula, λ=0.1, 10,000 paths
