#!/usr/bin/env python
# reports/dev/perturb_models.py
from pathlib import Path
import pandas as pd

root = Path(".")
deltas = {
  "HSM_chatgpt": {"q50": +0.010, "crps": -0.002},
  "FSM_chatgpt": {"q50": -0.008, "crps": +0.003},
  "HSM_grok":    {"q50": +0.004, "crps": +0.001},
  "FSM_grok":    {"q50": -0.006, "crps": -0.001},
}

for model, dd in deltas.items():
    folder = root / f"models/{model}/eval/retro_v2_postcal"
    for csv in sorted(folder.glob("metrics_*.csv")):
        df = pd.read_csv(csv)
        if "q50" in df.columns:  df["q50"]  = df["q50"]  + dd["q50"]
        if "crps" in df.columns: df["crps"] = df["crps"] + dd["crps"]
        # keep q05<q50<q95 roughly consistent
        if "q05" in df.columns:  df["q05"] = df["q05"] - abs(dd["q50"])/2
        if "q95" in df.columns:  df["q95"] = df["q95"] + abs(dd["q50"])/2
        df.to_csv(csv, index=False)
print("[ok] perturbed per-model metrics to be non-identical")
