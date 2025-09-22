#!/usr/bin/env python3
"""
Score meta-stacked ensemble vs equal-weight baseline with robust overlap logic.

Inputs:
  ensemble/quantiles_ensemble.csv  (indicator,horizon,origin_year,quantile,value)
  eval/results/quantiles_by_model.csv
  eval/results/realized_by_origin.csv           (indicator,origin_year,horizon,value)

Outputs:
  eval/results/metrics_by_horizon_ensemble.csv  (both methods, long)
  eval/results/ensemble_vs_equal_weight.csv     (inner-join overlap only)
  + prints diagnostics: sizes and overlap share
"""
import os, sys, numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
ENS_IN   = os.path.join(ROOT, "ensemble", "quantiles_ensemble.csv")
QBM_IN   = os.path.join(RES, "quantiles_by_model.csv")
TRUTH_IN = os.path.join(RES, "realized_by_origin.csv")

METRICS_OUT = os.path.join(RES, "metrics_by_horizon_ensemble.csv")
COMPARE_OUT = os.path.join(RES, "ensemble_vs_equal_weight.csv")
TAUS = [0.05, 0.5, 0.95]

def pinball(y, q, tau):
    u = y - q
    return tau*np.maximum(u,0.0) + (tau-1.0)*np.minimum(u,0.0)

def score_quantiles(df_q, truth, method_tag):
    # df_q: indicator,horizon,origin_year,quantile,value
    m = df_q.merge(truth, on=["indicator","origin_year","horizon"], how="inner")
    rows = []
    for (ind,h,oy), g in m.groupby(["indicator","horizon","origin_year"]):
        y = float(g["truth"].iloc[0])
        losses = []
        for tau in TAUS:
            qi = g.loc[np.isclose(g["quantile"].astype(float), tau), "value"]
            if qi.empty: continue
            losses.append(float(pinball(y, float(qi.iloc[0]), tau)))
        if losses:
            rows.append(dict(indicator=str(ind), horizon=int(h), origin_year=int(oy),
                             metric="composite", loss=float(np.mean(losses)),
                             method=method_tag))
    return pd.DataFrame(rows)

def build_equal_weight_quantiles(qbm):
    # Average the same quantile across models for each triplet
    g = (qbm.groupby(["indicator","horizon","origin_year","quantile"], as_index=False)["value"]
             .mean())
    return g

def main():
    # Load inputs
    for path in [ENS_IN, QBM_IN, TRUTH_IN]:
        if not os.path.exists(path):
            raise SystemExit(f"[error] missing input: {os.path.relpath(path, ROOT)}")
    ens = pd.read_csv(ENS_IN)
    qbm = pd.read_csv(QBM_IN)
    truth = pd.read_csv(TRUTH_IN).rename(columns={"value":"truth"})
    # Coerce types
    for df in (ens, qbm):
        df["quantile"] = df["quantile"].astype(float)
        df["horizon"] = df["horizon"].astype(int)
        df["origin_year"] = df["origin_year"].astype(int)
        df["indicator"] = df["indicator"].astype(str)
    truth["horizon"] = truth["horizon"].astype(int)
    truth["origin_year"] = truth["origin_year"].astype(int)
    truth["indicator"] = truth["indicator"].astype(str)

    # Score ensemble
    ens_sc = score_quantiles(ens[["indicator","horizon","origin_year","quantile","value"]], truth, "meta_stack")
    # Build + score equal-weight baseline
    eq_q = build_equal_weight_quantiles(qbm)
    eq_sc = score_quantiles(eq_q, truth, "equal_weight")

    # Write long table
    out_long = pd.concat([ens_sc, eq_sc], ignore_index=True)
    out_long = out_long.sort_values(["indicator","origin_year","horizon","method"])
    os.makedirs(RES, exist_ok=True)
    out_long.to_csv(METRICS_OUT, index=False)
    print(f"[ok] wrote {METRICS_OUT}  rows={len(out_long)}")

    # Robust overlap comparison (inner-join on triplet)
    key = ["indicator","origin_year","horizon"]
    cmp = ens_sc.merge(eq_sc, on=key, how="inner", suffixes=("_meta","_eq"))
    if not cmp.empty:
        cmp["delta_meta_minus_eq"] = cmp["loss_meta"] - cmp["loss_eq"]
    cmp.to_csv(COMPARE_OUT, index=False)
    print(f"[ok] wrote {COMPARE_OUT}  rows={len(cmp)}")

    # Diagnostics
    ens_keys = set(map(tuple, ens_sc[key].itertuples(index=False, name=None)))
    eq_keys  = set(map(tuple, eq_sc[key].itertuples(index=False, name=None)))
    inter = ens_keys & eq_keys
    print(f"[diag] meta_stack triplets: {len(ens_keys)} | equal_weight triplets: {len(eq_keys)} | overlap: {len(inter)}")
    if len(inter):
        d = cmp["delta_meta_minus_eq"].dropna()
        if len(d):
            print(f"[summary] mean Δ(meta−eq) = {d.mean():.6f}  (neg = good), share_better={(d<0).mean():.1%}")

if __name__ == "__main__":
    sys.exit(main() or 0)
