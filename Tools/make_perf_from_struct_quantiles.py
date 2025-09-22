#!/usr/bin/env python3
"""
Tools/make_perf_from_struct_quantiles.py

Build eval/results/perf_by_model.csv in LONG format from per-model quantile
files like:
  eval/results/hsm_struct_1985.csv
  eval/results/fsm_struct_1990.csv
  eval/results/grok_hsm_struct_2000.csv
Each file should contain: indicator,horizon,q05,q50,q95.

We also need realized values:
  eval/results/realized_by_origin.csv
with columns: indicator,origin_year,horizon,value

Outputs:
  eval/results/perf_by_model.csv
    columns: indicator,horizon,origin_year,model,metric,loss
  where 'metric' currently = 'composite' (a quantile-score proxy average over
  tau in {0.05,0.5,0.95}). You can later recompute CRPS/Brier if available.

Notes:
- Model name is inferred from filename prefix before "_struct_".
  Examples:
    hsm_struct_1985.csv       -> model=hsm, origin_year=1985
    grok_hsm_struct_2000.csv  -> model=grok_hsm, origin_year=2000
- This computes a practical proxy for CRPS using the mean pinball loss across
  q05/q50/q95 (a standard quantile-score aggregation).
"""

import os, re, glob, sys
import numpy as np
import pandas as pd

RES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eval", "results"))

def pinball_loss(y, q, tau):
    # rho_tau(u) = (tau - 1_{u<0}) * u  where u = y - q
    u = y - q
    return np.where(u >= 0, tau * u, (tau - 1.0) * u)

def load_truth(path):
    df = pd.read_csv(path)
    need = {"indicator","origin_year","horizon","value"}
    if not need.issubset(df.columns):
        missing = need - set(df.columns)
        raise SystemExit(f"[error] {path} missing columns: {missing}")
    df = df.copy()
    df["origin_year"] = df["origin_year"].astype(int)
    df["horizon"] = df["horizon"].astype(int)
    df.rename(columns={"value":"truth"}, inplace=True)
    return df

def parse_model_year(fname):
    # e.g., hsm_struct_1985.csv  -> ("hsm", 1985)
    #       grok_hsm_struct_2000.csv -> ("grok_hsm", 2000)
    base = os.path.basename(fname).lower()
    m = re.match(r"(.+?)_struct_(\d{4})\.csv$", base)
    if not m:
        return None, None
    model = m.group(1)
    year = int(m.group(2))
    return model, year

def main():
    truth_path = os.path.join(RES, "realized_by_origin.csv")
    if not os.path.exists(truth_path):
        raise SystemExit("[error] Missing eval/results/realized_by_origin.csv "
                         "with columns: indicator,origin_year,horizon,value")

    truth = load_truth(truth_path)

    files = glob.glob(os.path.join(RES, "*_struct_*.csv"))
    if not files:
        raise SystemExit("[error] No *_struct_*.csv files found under eval/results")

    rows = []
    for f in files:
        model, oy = parse_model_year(f)
        if model is None:
            continue
        df = pd.read_csv(f)
        need = {"indicator","horizon","q05","q50","q95"}
        if not need.issubset(df.columns):
            # skip if not a quantile file
            continue

        # join truth for this origin_year
        t = truth[truth["origin_year"] == oy]
        if t.empty:
            # no truths for this origin_year; skip
            continue

        # merge on indicator+horizon
        mrg = df.merge(t, on=["indicator","horizon"], how="inner")
        if mrg.empty:
            continue

        # compute quantile-score proxy (mean pinball across 0.05,0.5,0.95)
        tau_list = [0.05, 0.5, 0.95]
        qcols = {"0.05":"q05", "0.5":"q50", "0.95":"q95"}

        losses = []
        for _, r in mrg.iterrows():
            y = float(r["truth"])
            Ls = []
            for tau in tau_list:
                q = float(r[qcols[str(tau)]])
                L = float(pinball_loss(y, q, tau))
                Ls.append(L)
            losses.append(np.mean(Ls))

        mrg["loss"] = losses
        mrg["model"] = model
        mrg["origin_year"] = oy
        mrg["metric"] = "composite"  # proxy for now

        keep = ["indicator","horizon","origin_year","model","metric","loss"]
        rows.append(mrg[keep])

    if not rows:
        raise SystemExit("[error] Could not assemble any rows. "
                         "Check that realized_by_origin.csv aligns with your *_struct_*.csv "
                         "(matching indicator + horizon, and origin_year from filename).")

    out = pd.concat(rows, axis=0, ignore_index=True)
    out["horizon"] = out["horizon"].astype(int)
    out["origin_year"] = out["origin_year"].astype(int)
    out["loss"] = pd.to_numeric(out["loss"], errors="coerce")

    dst = os.path.join(RES, "perf_by_model.csv")
    out.to_csv(dst, index=False)
    print(f"[ok] Wrote {dst}  rows={len(out)}")

if __name__ == "__main__":
    main()
