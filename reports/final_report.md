# Final Report (Origin 1995)

Artifacts: `release/FINAL_hsm_chatgpt_1995.csv`, `release/FINAL_ensemble_1995_equal.csv`.

## Coverage — Single Model (BA a221 + TM α=0.85)

| indicator            |   level |   covered |   total |   coverage_rate |
|:---------------------|--------:|----------:|--------:|----------------:|
| ba_plus_25plus_share |     0.5 |        12 |      15 |        0.8      |
| ba_plus_25plus_share |     0.9 |        14 |      15 |        0.933333 |
| trust_media_pct      |     0.5 |         8 |      15 |        0.533333 |
| trust_media_pct      |     0.9 |        15 |      15 |        1        |

## Coverage — Ensemble (Equal Weight)

| indicator            |   level |   covered |   total |   coverage_rate |
|:---------------------|--------:|----------:|--------:|----------------:|
| ba_plus_25plus_share |     0.5 |        12 |      15 |        0.8      |
| ba_plus_25plus_share |     0.9 |        14 |      15 |        0.933333 |
| trust_media_pct      |     0.5 |         8 |      15 |        0.533333 |
| trust_media_pct      |     0.9 |        15 |      15 |        1        |

## Non-US Validation (Proxies)

**Japan (BA proxy):**

| region   | indicator            |   level |   covered |   total |   coverage_rate |
|:---------|:---------------------|--------:|----------:|--------:|----------------:|
| Japan    | ba_plus_25plus_share |     0.9 |         8 |      10 |             0.8 |

**Brazil (Trust Media proxy):**

| region   | indicator       |   level |   covered |   total |   coverage_rate |
|:---------|:----------------|--------:|----------:|--------:|----------------:|
| Brazil   | trust_media_pct |     0.9 |        10 |      10 |               1 |

## Cross-Indicator Overlap (Ensemble)

| indicator_A          | indicator_B     |   median_dir_agree |   band_overlap_50 |   band_overlap_90 |   h_first |   h_last |
|:---------------------|:----------------|-------------------:|------------------:|------------------:|----------:|---------:|
| ba_plus_25plus_share | trust_media_pct |                  1 |               nan |                 0 |         1 |       15 |

## Notes

- With n=15 horizons, sampling error at 50%/90% is substantial; interpret small deviations cautiously.
- Ensemble currently includes 1 model; more models can be added by appending paths to `configs/ensemble_models_1995.txt` and re-running Step 14.

