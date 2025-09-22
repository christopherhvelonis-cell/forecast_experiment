#!/usr/bin/env python3
"""
Tools/make_quantiles_by_model_from_struct.py

Build eval/results/quantiles_by_model.csv from files like:
  eval/results/hsm_struct_1985.csv
  eval/results/fsm_struct_2000.csv
Each struct file should have: indicator,horizon,q05,q50,q95

Output (long format):
  eval/results/quantiles_by_model.csv
  columns: indicator,horizon,origin_year,model,quantile,value
"""

import os, re, glob, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
OUT  = os.path.join(RES, "quantiles_by_model.csv")

def parse_model_year(fname: str):
    # e.g. hsm_struct_1985.csv  -> model=hsm, origin_year=1985
    #      grok_hsm_struct_2000.csv -> model=grok_hsm, origin_year=2000
    base = os.path.basename(fname).lower()
    m = re.match(r"(.+?)_struct_(\d{4})\.csv$", base)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))

def main():
    files = sorted(glob.glob(os.path.join(RES, "*_struct_*.csv")))
    if not files:
        sys.exit("[error] No *_struct_*.csv files found under eval/results")

    rows = []
    for f in files:
        model, oy = parse_model_year(f)
        if model is None:
            continue
        df = pd.read_csv(f)
        need = {"indicator","horizon","q05","q50","q95"}
        if not need.issubset(df.columns) or df.empty:
            continue
        df = df[["indicator","horizon","q05","q50","q95"]].copy()
        df["origin_year"] = oy
        df["model"] = model

        # melt to long
        long = df.melt(id_vars=["indicator","horizon","origin_year","model"],
                       value_vars=["q05","q50","q95"],
                       var_name="qname", value_name="value")
        qmap = {"q05":0.05, "q50":0.5, "q95":0.95}
        long["quantile"] = long["qname"].map(qmap).astype(float)
        long = long.drop(columns=["qname"])

        # clean types
        long["horizon"] = long["horizon"].astype(int)
        long["origin_year"] = long["origin_year"].astype(int)
        rows.append(long)

    if not rows:
        sys.exit("[error] No valid struct files with required columns were found.")

    out = pd.concat(rows, ignore_index=True)
    out = out[["indicator","horizon","origin_year","model","quantile","value"]] \
             .sort_values(["indicator","origin_year","horizon","model","quantile"])

    os.makedirs(RES, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[ok] Wrote {os.path.relpath(OUT, ROOT)}  rows={len(out)}")

if __name__ == "__main__":
    main()
