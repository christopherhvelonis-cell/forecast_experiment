# -*- coding: utf-8 -*-
#!/usr/bin/env python
# ensemble/apply_weights.py
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

MODEL_CANDIDATES = ["HSM_chatgpt","FSM_chatgpt","HSM_grok","FSM_grok"]

def read_per_model(origins, folder="models", sub="eval/retro_v2_postcal"):
    out={}
    for m in MODEL_CANDIDATES:
        base = Path(folder) / m / sub
        files = sorted(base.glob("metrics_*.csv"))
        if not files: continue
        rows=[]
        for f in files:
            origin = int(f.stem.split("_")[1])
            if origin not in origins: continue
            df = pd.read_csv(f); df["origin"]=origin
            rows.append(df[["origin","h","crps","brier","q05","q50","q95","y_true"]])
        if rows: out[m]=pd.concat(rows, ignore_index=True)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="ensemble/results_fforma/weights_by_h_median.csv")
    ap.add_argument("--outdir",  default="eval/results/ensemble_retro_v2_postcal")
    ap.add_argument("--origins", nargs="*", type=int)
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    retro = Path("eval/results/retro_v2_postcal")
    origins = args.origins or sorted({int(p.stem.split("_")[1]) for p in retro.glob("metrics_*.csv")})

    W = pd.read_csv(args.weights)
    weight_cols = [c for c in W.columns if c.startswith("w_")]
    avail_models = [c[2:] for c in weight_cols]

    per_model = read_per_model(origins)
    if not per_model:
        print("[err] No per-model metrics found under models/*/eval/retro_v2_postcal/."); return 1

    models = [m for m in avail_models if m in per_model]
    if not models:
        print("[err] No overlap between weight columns and available models."); return 2

    long=[]
    for m in models:
        df = per_model[m].copy(); df["model"]=m; long.append(df)
    long = pd.concat(long, ignore_index=True)
    Wm = W[["h"] + [f"w_{m}" for m in models]].copy()
    long = long.merge(Wm, on="h", how="left")

    def wavg(g, cols, wcols):
        ws = g[wcols].iloc[0].to_numpy()
        xs = g[cols].to_numpy()
        return float((xs * ws).sum())

    out_rows=[]
    for (origin,h), g in long.groupby(["origin","h"]):
        wcols = [f"w_{m}" for m in models]
        q05 = wavg(g, ["q05"]*len(models), wcols)
        q50 = wavg(g, ["q50"]*len(models), wcols)
        q95 = wavg(g, ["q95"]*len(models), wcols)
        crps_ens = wavg(g, ["crps"]*len(models), wcols)
        brier_ens = wavg(g, ["brier"]*len(models), wcols)
        crps_ew  = float(g["crps"].mean())
        brier_ew = float(g["brier"].mean())
        y_true = float(g["y_true"].iloc[0]) if "y_true" in g else np.nan
        out_rows.append({"origin":origin,"h":h,"q05":q05,"q50":q50,"q95":q95,
                         "crps_ens":crps_ens,"crps_ew":crps_ew,"brier_ens":brier_ens,"brier_ew":brier_ew,"y_true":y_true})
    ens = pd.DataFrame(out_rows).sort_values(["origin","h"])
    ens.to_csv(outdir / "metrics_ENSEMBLE.csv", index=False)
    print(f"[ok] wrote {outdir}/metrics_ENSEMBLE.csv with {len(ens)} rows"); return 0

if __name__ == "__main__":
    import sys; sys.exit(main())
