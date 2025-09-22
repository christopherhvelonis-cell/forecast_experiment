#!/usr/bin/env python3
"""
Rebuild a minimal stacking_features.csv from perf_by_model.csv.

Requires perf_by_model.csv with columns:
  indicator,horizon,origin_year,model,composite

Outputs eval/results/stacking_features.csv with columns:
  indicator,horizon,origin_year,model,
  const,h,oy,loss_model,loss_centered,rank_within_h,models_in_group

These are numeric and stable features so the learner can run on small samples.
"""

import os
import argparse
import numpy as np
import pandas as pd

def main(perf_path, out_path):
    if not os.path.exists(perf_path):
        raise SystemExit(f"[error] missing {perf_path}")
    perf = pd.read_csv(perf_path)

    need = {"indicator","horizon","origin_year","model","composite"}
    if not need.issubset(perf.columns):
        miss = need - set(perf.columns)
        raise SystemExit(f"[error] perf_by_model.csv missing columns: {miss}")

    perf = perf.copy()
    perf["indicator"] = perf["indicator"].astype(str)
    perf["horizon"] = perf["horizon"].astype(int)
    perf["origin_year"] = perf["origin_year"].astype(int)
    perf["model"] = perf["model"].astype(str)
    perf["composite"] = perf["composite"].astype(float)

    # One row per (indicator,horizon,origin_year,model)
    base = perf.groupby(["indicator","horizon","origin_year","model"], as_index=False)["composite"].mean()

    # Group stats per (indicator,horizon) so we can generalize across origins
    grp = base.groupby(["indicator","horizon"])
    mean_by_group = grp["composite"].transform("mean")
    count_by_group = grp["model"].transform("nunique")
    # Rank: lower loss = better rank (1 is best). Convert to numeric feature.
    rank_by_group = grp["composite"].rank(method="average", ascending=True)

    feats = base.assign(
        const = 1.0,
        h = base["horizon"].astype(float),
        oy = base["origin_year"].astype(float),
        loss_model = base["composite"].astype(float),
        loss_centered = base["composite"].astype(float) - mean_by_group.astype(float),
        rank_within_h = rank_by_group.astype(float),
        models_in_group = count_by_group.astype(float),
    )[[
        "indicator","horizon","origin_year","model",
        "const","h","oy","loss_model","loss_centered","rank_within_h","models_in_group"
    ]].sort_values(["indicator","horizon","origin_year","model"])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    feats.to_csv(out_path, index=False)
    print(f"[ok] rebuilt stacking features -> {out_path}  rows={len(feats)}  cols={len(feats.columns)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--perf", required=True, help="eval/results/perf_by_model.csv")
    ap.add_argument("--out", required=True, help="eval/results/stacking_features.csv")
    args = ap.parse_args()
    main(args.perf, args.out)
