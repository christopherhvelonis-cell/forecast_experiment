#!/usr/bin/env python3
"""
Find a per-model metrics CSV under eval/results and emit perf_by_model.csv
in long format with columns: indicator,horizon,origin_year,model,metric,loss.
- If it already finds a long-format file, it just writes a cleaned copy.
- If it finds a wide-format file with columns like ['composite','crps','brier'],
  it melts them into (metric, loss).
"""

import os, sys, glob
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RES  = os.path.abspath(os.path.join(ROOT, "..", "eval", "results"))

# Candidates to look for (ordered)
CANDS = [
    "perf_by_model.csv",
    "metrics_by_model.csv",
    "losses_by_model.csv",
    "model_metrics.csv",
    "model_metrics_long.csv",
    "per_model_metrics.csv",
]

def find_candidate():
    # first try known names
    for name in CANDS:
        p = os.path.join(RES, name)
        if os.path.exists(p):
            return p
    # else any csv that has the core keys
    for p in glob.glob(os.path.join(RES, "*.csv")):
        try:
            df = pd.read_csv(p, nrows=5)
        except Exception:
            continue
        cols = set(c.lower() for c in df.columns)
        if {"indicator","horizon","origin_year","model"}.issubset(cols):
            return p
    return None

def main():
    src = find_candidate()
    if not src:
        sys.exit("[error] Could not find a suitable per-model metrics CSV under eval/results")

    df = pd.read_csv(src)
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    lower = {c.lower():c for c in df.columns}
    need = ["indicator","horizon","origin_year","model"]
    if not all(n in lower for n in need):
        sys.exit(f"[error] {src} is missing required keys {need}")

    # Case A: already long format with metric + loss
    if ("metric" in lower) and ("loss" in lower):
        out = df[[lower["indicator"],lower["horizon"],lower["origin_year"],lower["model"],lower["metric"],lower["loss"]]].copy()
        out.columns = ["indicator","horizon","origin_year","model","metric","loss"]
    else:
        # Case B: wide format — find loss-like columns to melt
        score_cols = [c for c in df.columns if c.lower() in {"composite","crps","brier"}]
        if not score_cols:
            sys.exit(f"[error] {src} does not have metric/loss or known wide columns (composite/crps/brier)")
        base = df[[lower["indicator"],lower["horizon"],lower["origin_year"],lower["model"]]].copy()
        melted = df.melt(
            id_vars=[lower["indicator"],lower["horizon"],lower["origin_year"],lower["model"]],
            value_vars=score_cols,
            var_name="metric",
            value_name="loss"
        )
        melted.columns = ["indicator","horizon","origin_year","model","metric","loss"]
        out = melted

    out["horizon"] = out["horizon"].astype(int)
    out["origin_year"] = out["origin_year"].astype(int)
    out["metric"] = out["metric"].str.lower()
    out["loss"] = out["loss"].astype(float)

    dst = os.path.join(RES, "perf_by_model.csv")
    out.to_csv(dst, index=False)
    print(f"[ok] Wrote {dst}  rows={len(out)}  (from {os.path.basename(src)})")

if __name__ == "__main__":
    main()
