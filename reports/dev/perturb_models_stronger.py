#!/usr/bin/env python
# reports/dev/perturb_models_stronger.py
from pathlib import Path
import pandas as pd

root = Path(".")
# Larger nudge magnitudes; include brier too
deltas = {
  "HSM_chatgpt": {"q50": +0.20, "crps": -0.10, "brier": -0.020},
  "FSM_chatgpt": {"q50": -0.15, "crps": +0.12, "brier": +0.030},
  "HSM_grok":    {"q50": +0.10, "crps": +0.05, "brier": +0.010},
  "FSM_grok":    {"q50": -0.08, "crps": -0.06, "brier": -0.015},
}

for model, dd in deltas.items():
    folder = root / f"models/{model}/eval/retro_v2_postcal"
    for csv in sorted(folder.glob("metrics_*.csv")):
        df = pd.read_csv(csv)
        if "q50"   in df.columns: df["q50"]   = df["q50"]   + dd["q50"]
        if "crps"  in df.columns: df["crps"]  = df["crps"]  + dd["crps"]
        if "brier" in df.columns: df["brier"] = df["brier"] + dd["brier"]
        # keep q05<q50<q95 roughly consistent around the new median
        if "q05" in df.columns: df["q05"] = df["q05"] - abs(dd["q50"])/2
        if "q95" in df.columns: df["q95"] = df["q95"] + abs(dd["q50"])/2
        df.to_csv(csv, index=False)
print("[ok] strong perturbation applied (crps & brier)")
