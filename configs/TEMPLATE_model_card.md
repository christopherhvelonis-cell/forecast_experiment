# Model Card - ${MODEL_ID}

**Type:** (HSM/FSM/Baseline/Ensemble)
**Complexity Count P:** ${P}
**Leakage Controls:** vintages, rolling-origin, nested CV.
**Calibration:** EMOS/NGR (continuous), isotonic/beta-TLP (events), conformal fallback.
**Multivariate Post-Processing:** ECC/Schaake.
**Break Handling:** re-estimation around breaks.
**Limits/Assumptions:**

## Metrics (outer folds / prequential)
- CRPS, Brier, reliability, coverage 50/90, PIT.
- Murphy decomposition (events).
- Skill vs equal-weight (median).
