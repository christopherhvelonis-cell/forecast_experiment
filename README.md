# README

This repository contains calibrated forecasts for origin 1995 and ensemble outputs.

## Key Artifacts
- release\FINAL_hsm_chatgpt_1995.csv
- release\FINAL_ensemble_1995_equal.csv
- release\coverage_summary_calibrated.csv
- release\coverage_summary_calibrated_ensemble.csv
- release\final_report.md
- release\release_manifest.md

## How to Reproduce (core)
1. Build FINAL (already done).
2. Verify diagnostics: `verify_calibrated_cli.py --calibrated_csv ... --out_dir ...`
3. Build ensemble: `tools\ensemble_equal_cli.py --list_file configs\ensemble_models_1995.txt --out_csv eval\results\calibrated\FINAL_ensemble_1995_equal.csv`
4. Re-verify ensemble diagnostics.
5. (Optional) Non-US checks: `validation_nonUS\nonus_check_cli.py ...`

## Scenario Materials
- reports\scenarios\baseline.md | optimistic.md | stress.md | wildcard.md
- reports\scenarios\overlap_matrix.csv
### Switch ensemble metric
- Use CRPS:  Use-Weights crps
- Use Brier: Use-Weights brier

Outputs go to eval/results/ensemble_retro_v2_postcal/metrics_ENSEMBLE.csv.
Provenance: eval/results/ensemble_retro_v2_postcal/ENSEMBLE_SOURCE.txt and eports/release_manifest.json.
