cd "C:\Users\Owner\Downloads\forecast_experiment"

@'
#!/usr/bin/env python
# reports/make_readme.py
from pathlib import Path

readme = """
# Forecast Experiment (v1.6)

This repo contains the Universal 40-Year Cultural & Political Forecasting System.

## What's included
- Retro predictions v2 (origins 1985, 1990, 2015, 2020)
- Calibration v2 (EMOS/NGR placeholder + conformal)
- Significance checks (DM-style pre/post with BH-FDR)
- Stacked ensemble (FFORMA-style)
- Scenario narratives (40y)

## Reproduce
```powershell
# venv, deps
py -3.12 -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt

# Step 7 (retro)
python eval/evaluator_code.py --origins 1985 1990 2015 2020 --horizons 1:15 --outdir eval/results/retro_v2 --save-diagnostics pit coverage reliability --save-scenarios 40

# Step 8 (calibration placeholders)
python calibrate/emos_ngr.py --prequential --export eval/results/calibration_v2
python calibrate/conformal.py --mode split --series all --export eval/results/calibration_v2

# Step 7 re-run with calibrated
python eval/evaluator_code.py --origins 1985 1990 2015 2020 --horizons 1:15 --outdir eval/results/retro_v2_postcal --save-diagnostics pit coverage reliability --save-scenarios 40 --use-calibrated

# Step 11 (pre/post sig)
python eval/significance_dm_prepost.py

# Step 14 (FFORMA)
python ensemble/fforma_meta.py --score crps
python ensemble/fforma_meta.py --score brier
python ensemble/apply_weights.py

# Reports
python reports/make_final_report.py
python reports/make_readme.py
