#!/usr/bin/env python3
"""
Tools/make_stacking_features_from_perf.py

Purpose:
  Generate a minimal yet useful stacking_features.csv directly from
  eval/results/perf_by_model.csv so meta-stacking can proceed even if
  bespoke feature engineering hasn't been run yet.

Input:
  --perf   eval/results/perf_by_model.csv
           Columns: indicator,horizon,origin_year,model,metric,loss

  --metric composite|crps|brier  (filters the input rows)

Output:
  eval/results/stacking_features.csv
           One row per (indicator,horizon,origin_year) with columns:
             indicator,horizon,origin_year,
             mean_loss,std_loss,min_loss,max_loss,range_loss,
             n_models,horizon_sq,years_since_first

Notes:
  - These are generic meta-features computed across models' losses.
  - They are simple but often still informative for FFORMA-style weighting.
"""

from __future__ import annotations
import argparse, os
import numpy as np
import pandas as pd

def parse_args():
    p = argparse.ArgumentParser(description="Build stacking_features.csv from perf_by_model.csv")
    p.add_argument("--perf", default="eval/results/perf_by_model.csv")
    p.add_argument("--metric", default="composite", choices=["composite","crps","brier"])
    p.add_argument("--out", default="eval/results/stacking_features.csv")
    return p.parse_args()

def main():
    args = parse_args()
    perf = pd.read_csv(args.perf)
    perf = perf[perf["metric"].str.lower() == args.metric.lower()].copy()

    if perf.empty:
        raise SystemExit(f"[error] No rows for metric={args.metric} in {args.perf}")

    # Ensure numeric
    perf["horizon"] = perf["horizon"].astype(int)
    perf["origin_year"] = perf["origin_year"].astype(int)
    perf["loss"] = perf["loss"].astype(float)

    # Basic features aggregated across available base models
    agg = (perf.groupby(["indicator","horizon","origin_year"])["loss"]
              .agg(mean_loss="mean",
                   std_loss="std",
                   min_loss="min",
                   max_loss="max")
              .reset_index())
    agg["std_loss"] = agg["std_loss"].fillna(0.0)
    agg["range_loss"] = agg["max_loss"] - agg["min_loss"]

    # Count models per group
    n_models = (perf.groupby(["indicator","horizon","origin_year"])["model"]
                    .nunique().reset_index(name="n_models"))
    feat = agg.merge(n_models, on=["indicator","horizon","origin_year"], how="left")

    # Simple derived features
    first_year = int(feat["origin_year"].min())
    feat["horizon_sq"] = feat["horizon"] * feat["horizon"]
    feat["years_since_first"] = feat["origin_year"] - first_year

    # Reorder columns
    cols = ["indicator","horizon","origin_year",
            "mean_loss","std_loss","min_loss","max_loss","range_loss",
            "n_models","horizon_sq","years_since_first"]
    feat = feat[cols].sort_values(["indicator","horizon","origin_year"])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    feat.to_csv(args.out, index=False)
    print(f"[ok] Wrote stacking features -> {args.out}  (rows={len(feat)})")

if __name__ == "__main__":
    main()
