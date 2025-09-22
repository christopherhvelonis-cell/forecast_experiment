# Inventory Report
_Generated (UTC)_: 2025-09-21T07:47:22

## Folder Tree Check
**Present dirs:**
- [x] `data/raw`
- [x] `data/processed`
- [x] `data/docsheets`
- [x] `models/HSM_chatgpt`
- [x] `models/FSM_chatgpt`
- [x] `models/HSM_grok`
- [x] `models/FSM_grok`
- [x] `eval/results`
- [x] `validation_nonUS`
- [x] `bias_logs`
- [x] `ensemble`
- [x] `reports`
- [x] `configs`
- [x] `Tools`

**Missing dirs:**
- [ ] `eval/metrics`
- [ ] `eval/holdouts`

## Key Files
**Present files:**
- [x] `configs/experiment.yml`
- [x] `configs/scoring.yml`
- [x] `configs/indicators.yml`
- [x] `configs/baselines.yml`
- [x] `data/vintages.md`
- [x] `data/revisions.md`
- [x] `Tools/run_step_15_learn_ensemble.py`
- [x] `Tools/make_stacking_features_from_perf.py`
- [x] `Tools/discover_make_perf.py`
- [x] `Tools/make_perf_from_struct_quantiles.py`
- [x] `Tools/acceptance_gate.ps1`
- [x] `Tools/make_mini_report.py`
- [x] `Tools/make_release_bundle.py`
- [x] `Tools/clean_metrics_files.py`
- [x] `Tools/compute_composite_from_summaries.py`
- [x] `Tools/make_composite_plot.py`
- [x] `Tools/canonicalize_coverage.py`
- [x] `Tools/validate_schema.py`

**Missing files (optional/expected):**
- [ ] `Tools/run_step_15_apply_weights.py`
- [ ] `eval/evaluator_code.py`

## eval/results Summary
- Models discovered: `hsm`
- Origin years: `1985`
- Indicators (unique): `3`
- Horizons (unique): `15`

### Struct files
- `eval\results\hsm_struct_1985.csv`  (model=`hsm`, origin_year=`1985`, indicators=3, horizons=15)

### Standard Result Files
- `eval\results\perf_by_model.csv` → **missing**
- `eval\results\stacking_features.csv` → **missing**
- `eval\results\quantiles_by_model.csv` → **missing**
- `eval\results\event_probs_by_model.csv` → **missing**
- `eval\results\realized_by_origin.csv` → **missing**

## Next Minimal Actions (if continuing Step 15)
- Build `eval/results/perf_by_model.csv` (from evaluator or from struct+truth helper).
- Generate `eval/results/stacking_features.csv` from `perf_by_model.csv`.
- If weights not present: run `Tools/run_step_15_learn_ensemble.py` once perf/features exist.
- Then apply weights via `Tools/run_step_15_apply_weights.py` and re-score.