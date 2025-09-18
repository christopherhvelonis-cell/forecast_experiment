#!/usr/bin/env python
"""
Evaluator v2 (level-aware): builds Step-11 metrics from Step-8 diagnostics.

Works with coverage_points_calibrated.csv shaped like:
  ['indicator','year','horizon','level','covered']
where 'level' is 0.5 or 0.9 and 'covered' is 0/1 (or True/False).

Inputs:
  --diagnostics_dir : folder containing
      - coverage_points_calibrated.csv
      - coverage_summary_calibrated.csv
      - pit_values_calibrated.csv
  --out_dir         : output folder (created if missing)
  --indicators      : optional space-separated list to keep

Outputs:
  - metrics_by_horizon.csv     : per indicator & horizon, covered_50_rate and covered_90_rate + PIT summaries
  - coverage_overall.csv       : overall 50/90 coverage per indicator (from summary)
  - crps_brier_summary.csv     : placeholders (NaN) + overall coverage (compatibility)
  - loss_differences.csv       : |coverage - nominal| by horizon for 0.5 and 0.9
"""

import argparse, os
import pandas as pd
import numpy as np

REQ_FILES = [
    "coverage_points_calibrated.csv",
    "coverage_summary_calibrated.csv",
    "pit_values_calibrated.csv",
]

def read_required(d):
    paths = {name: os.path.join(d, name) for name in REQ_FILES}
    for name, p in paths.items():
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required file: {p}")
    return (
        pd.read_csv(paths["coverage_points_calibrated.csv"]),
        pd.read_csv(paths["coverage_summary_calibrated.csv"]),
        pd.read_csv(paths["pit_values_calibrated.csv"]),
    )

def coerce_binary(s):
    if s.dtype == bool:
        return s.astype(int)
    if s.dtype == object:
        t = s.astype(str).str.strip().str.lower()
        m = {"true":1,"false":0,"t":1,"f":0,"y":1,"n":0,"yes":1,"no":0,"1":1,"0":0}
        return t.map(m).fillna(pd.to_numeric(t, errors="coerce")).fillna(0).astype(int)
    return (pd.to_numeric(s, errors="coerce").fillna(0) > 0).astype(int)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostics_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--indicators", nargs="*", default=None)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cov_pts, cov_sum, pit_vals = read_required(args.diagnostics_dir)

    # Optional filter
    if args.indicators:
        keep = set(args.indicators)
        cov_pts = cov_pts[cov_pts["indicator"].isin(keep)]
        cov_sum = cov_sum[cov_sum["indicator"].isin(keep)]
        pit_vals = pit_vals[pit_vals["indicator"].isin(keep)]

    # Expect columns exactly as your file:
    # ['indicator','year','horizon','level','covered']
    need = {"indicator","horizon","level","covered"}
    if not need.issubset(set(cov_pts.columns)):
        raise ValueError(f"coverage_points_calibrated.csv must include columns {need}, found {cov_pts.columns.tolist()}")

    cov_pts["covered"] = coerce_binary(cov_pts["covered"])

    # Pivot per indicator,horizon â†’ rates for level 0.5 and 0.9
    # First aggregate mean covered by (indicator,horizon,level), then pivot 'level' to columns
    agg = (cov_pts
           .groupby(["indicator","horizon","level"], as_index=False)["covered"]
           .mean())
    piv = agg.pivot(index=["indicator","horizon"], columns="level", values="covered").reset_index()

    # Rename columns to canonical names
    # After pivot, columns will be something like {0.5, 0.9}; handle strings too just in case
def find_col(df, key):
    """
    Return the column in df that best corresponds to the numeric level key
    (e.g., 0.5 or 0.9). Handles strings like '0.5', '50%', 'p50', 'covered_50_rate', etc.
    Skips non-numeric columns (like 'indicator').
    """
    keyf = float(key)
    for c in df.columns:
        cl = str(c).strip().lower()
        # try numeric match first
        try:
            if float(cl) == keyf:
                return c
        except Exception:
            pass
        # alias matches
        if keyf == 0.5 and cl in {"0.5","50","50%","p50","q50","q_50","covered_50_rate","cov50","cov50_overall"}:
            return c
        if keyf == 0.9 and cl in {"0.9","90","90%","p90","q90","q_90","covered_90_rate","cov90","cov90_overall"}:
            return c
    return None


