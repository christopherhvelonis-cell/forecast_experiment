#!/usr/bin/env python
# calibrate/emos_ngr.py — placeholder EMOS/NGR
import argparse
from pathlib import Path
import pandas as pd, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prequential", action="store_true")
    ap.add_argument("--export", default="eval/results/calibration_v2")
    args = ap.parse_args()

    outdir = Path(args.export); outdir.mkdir(parents=True, exist_ok=True)
    src = Path("eval/results/retro_v2")
    files = sorted(src.glob("metrics_*.csv"))
    if not files:
        print("[warn] no metrics_* files in eval/results/retro_v2"); return 0

    rows=[]
    for f in files:
        df = pd.read_csv(f)
        q05,q50,q95 = df["q05"].to_numpy(), df["q50"].to_numpy(), df["q95"].to_numpy()
        spread_low, spread_high = q50-q05, q95-q50
        out = df.copy()
        out["q05_cal"] = q50 - 1.05*spread_low
        out["q95_cal"] = q50 + 1.05*spread_high
        out.to_csv(outdir / f.name.replace("metrics_","calibrated_"), index=False)
        cov50 = ((out["q05_cal"]<=out["y_true"]) & (out["y_true"]<=out["q95_cal"])).mean()
        rows.append({"file": f.name, "cov50_est": cov50})
    pd.DataFrame(rows).to_csv(outdir/"emos_summary.csv", index=False)
    print(f"[ok] EMOS/NGR placeholder wrote to {outdir}")

if __name__ == "__main__": raise SystemExit(main())
