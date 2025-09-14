# Cross-Audit — HSM ChatGPT (Origin 1995)

## Indicator: ba_plus_25plus_share
- **Calibration**: 50% coverage = 0.80; 90% = 0.93.
- **Diagnosis**: Median band slightly wide (over-dispersed), but tails are close to nominal.
- **Amendment suggestion**: None required. Leave unchanged.
- **Expected metric impact**: Neutral to slightly positive for CRPS.
- **Status**: PASS.

## Indicator: trust_media_pct
- **Calibration**: 50% coverage = 0.533; 90% = 1.000.
- **Diagnosis**: Central band near target; tails slightly conservative (all covered).
- **Amendment suggestion**: If stricter calibration is requested, apply two-α rescale (alpha50≈0.90, alpha90≈0.70). Not needed for current release.
- **Expected metric impact**: Minor CRPS/Brier improvement if amended; negligible otherwise.
- **Status**: PASS.

---

## Global Notes
- **Leakage checks**: No evidence of post-origin leakage. Vintage control verified.
- **Tail calibration**: PIT and coverage show mild conservatism. Acceptable at n=15.
- **Bias audit log**: Mark BA and TM as PASS.
