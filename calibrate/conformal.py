#!/usr/bin/env python
# calibrate/conformal.py — placeholder split-conformal widening
import argparse
from pathlib import Path
import pandas as pd, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="split")
    ap.add_argument("--series", default="all")
    ap.add_argument("--export", default="eval/results/calibration_v2")
    args = ap.parse_args()

    outdir = Path(args.export); outdir.mkdir(parents=True, exist_ok=True)
    src = Path("eval/results/retro_v2")
    files = sorted(src.glob("metrics_*.csv"))
    if not files:
        print("[warn] no metrics_* files in eval/results/retro_v2"); return 0

    alpha = 0.10
    for f in files:
        df = pd.read_csv(f)
        q05,q50,q95 = df["q05"].to_numpy(), df["q50"].to_numpy(), df["q95"].to_numpy()
        spread_low, spread_high = q50-q05, q95-q50
        out = df.copy()
        out["q05_conf"] = q50 - (1+alpha)*spread_low
        out["q95_conf"] = q50 + (1+alpha)*spread_high
        out.to_csv(outdir / f.name.replace("metrics_","conformal_"), index=False)
    print(f"[ok] Conformal placeholder wrote to {outdir}")

if __name__ == "__main__": raise SystemExit(main())
