models/HSM_grok/model_card.md
HSM Grok Model Card

Type: Multivariate state-space model (Kalman filter) with ECC
Complexity (P): 18 (6 states for 3 indicators + covariances)
Indicators: mass_public_polarization (affective), public_trust_government, vep_turnout_pres_pct
Training: Post-1985, min 8 years history, rolling origins (1985–2020)
Preprocessing: UTF-8, YE resampling, carry-forward imputation, z-score normalization
Leakage Controls: Vintage 2025-08-21/22/24, no future data
Breaks: Detected via ruptures or annotations (e.g., 2015 for real_gdp_growth)
Calibration: Mean-adjusted, sigma-scaled, PIT verified (50/90% coverage)
Outputs: q05/q50/q95 in predictions.csv, event_probs.csv, diagnostics.csv
Notes: ECC via GaussianCopula, λ=0.1, more robust than HSM_chatgpt
