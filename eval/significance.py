#!/usr/bin/env python
# eval/significance.py — minimal per-horizon summary (placeholder for DM/CC/GW)
import argparse
from pathlib import Path
import pandas as pd

def collect_metrics(folder: Path):
    files = sorted(folder.glob("metrics_*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f); df["__origin"] = int(f.stem.split("_")[1])
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="eval/results/retro_v2_postcal")
    ap.add_argument("--out",   default="eval/results/significance_summary.csv")
    args = ap.parse_args()

    df = collect_metrics(Path(args.indir))
    if df.empty:
        print("[warn] no metrics_* in", args.indir); return 0
    summary = df.groupby("h").agg(
        n=("y_true","count"),
        crps_mean=("crps","mean"),
        brier_mean=("brier","mean"),
        crps_sd=("crps","std"),
        brier_sd=("brier","std"),
    ).reset_index()
    outp = Path(args.out); outp.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(outp, index=False)
    print(f"[ok] wrote {outp}")

if __name__ == "__main__": raise SystemExit(main())
