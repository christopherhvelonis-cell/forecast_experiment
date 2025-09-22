#!/usr/bin/env python3
"""
Robust DM tests (meta_stack vs equal_weight) with:
- Method-name normalization (strip/lower/map synonyms)
- Fallback rebuild: if one of the methods is missing, recompute its losses from inputs
  (ensemble/quantiles_ensemble.csv for meta_stack,
   eval/results/quantiles_by_model.csv for equal_weight)
- HAC (Newey–West) at lag L = max(h-1, 0)
- BH-FDR correction

Inputs (primary):
  - eval/results/metrics_by_horizon_ensemble.csv
    columns: indicator,horizon,origin_year,metric,loss,method

Fallback inputs (only used if a method is missing in the metrics):
  - ensemble/quantiles_ensemble.csv            (for meta_stack)
  - eval/results/quantiles_by_model.csv        (for equal_weight)
  - eval/results/realized_by_origin.csv        (truths)

Outputs:
  - eval/results/significance_dm.csv
"""

import os, math
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
METRICS = os.path.join(RES, "metrics_by_horizon_ensemble.csv")
Q_ENSEMBLE = os.path.join(ROOT, "ensemble", "quantiles_ensemble.csv")
Q_BY_MODEL = os.path.join(RES, "quantiles_by_model.csv")
TRUTH_IN   = os.path.join(RES, "realized_by_origin.csv")
OUT = os.path.join(RES, "significance_dm.csv")

TAUS = [0.05, 0.5, 0.95]

def norm_method(m: str) -> str:
    if not isinstance(m, str): return ""
    x = m.strip().lower().replace("-", "_").replace(" ", "_")
    if x in {"meta", "stack", "fforma", "meta_stack", "meta_stacked", "metastack"}:
        return "meta_stack"
    if x in {"eq", "equal", "equal_weight", "equalweighted", "equal_weights"}:
        return "equal_weight"
    return x

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
    # average the same quantile across models
    return (qbm.groupby(["indicator","horizon","origin_year","quantile"], as_index=False)["value"]
               .mean())

def newey_west_variance(d, L):
    x = np.asarray(d, float)
    T = len(x)
    if T == 0:
        return np.nan
    mu = np.mean(x)
    e = x - mu
    gamma0 = np.dot(e, e) / T
    var = gamma0
    for l in range(1, min(L, T-1) + 1):
        w = 1.0 - l/(L+1.0)  # Bartlett weights
        cov = np.dot(e[l:], e[:-l]) / T
        var += 2.0 * w * cov
    return var / T  # variance of sample mean

def benjamini_hochberg(pvals):
    p = np.array(pvals, float)
    n = len(p)
    order = np.argsort(p)
    ranked = np.empty(n, float)
    cummin = 1.0
    for i, idx in enumerate(order[::-1], start=1):
        k = n - i + 1
        adj = p[idx] * n / k
        cummin = min(cummin, adj)
        ranked[idx] = cummin
    return np.minimum(ranked, 1.0)

def ensure_series(df):
    """Return two dataframes: meta_sc, eq_sc with cols indicator,horizon,origin_year,loss."""
    df = df.copy()
    df["method"] = df["method"].apply(norm_method)
    df = df[df["metric"].str.lower()=="composite"]
    meta_sc = df[df["method"]=="meta_stack"][["indicator","horizon","origin_year","loss"]].copy()
    eq_sc   = df[df["method"]=="equal_weight"][["indicator","horizon","origin_year","loss"]].copy()

    have_meta = not meta_sc.empty
    have_eq   = not eq_sc.empty
    if have_meta and have_eq:
        return meta_sc, eq_sc

    # Fallback rebuild(s)
    truth = pd.read_csv(TRUTH_IN).rename(columns={"value":"truth"})
    for c in ["indicator","origin_year","horizon"]:
        truth[c] = truth[c].astype({"indicator":str,"origin_year":int,"horizon":int}[c])

    if not have_meta and os.path.exists(Q_ENSEMBLE):
        ens = pd.read_csv(Q_ENSEMBLE)
        ens["quantile"] = ens["quantile"].astype(float)
        ens["horizon"] = ens["horizon"].astype(int)
        ens["origin_year"] = ens["origin_year"].astype(int)
        ens["indicator"] = ens["indicator"].astype(str)
        meta_sc = score_quantiles(ens[["indicator","horizon","origin_year","quantile","value"]], truth, "meta_stack") \
                    [["indicator","horizon","origin_year","loss"]]

    if not have_eq and os.path.exists(Q_BY_MODEL):
        qbm = pd.read_csv(Q_BY_MODEL)
        qbm["quantile"] = qbm["quantile"].astype(float)
        qbm["horizon"] = qbm["horizon"].astype(int)
        qbm["origin_year"] = qbm["origin_year"].astype(int)
        qbm["indicator"] = qbm["indicator"].astype(str)
        eq_q = build_equal_weight_quantiles(qbm)
        eq_sc = score_quantiles(eq_q, truth, "equal_weight") \
                  [["indicator","horizon","origin_year","loss"]]

    return meta_sc, eq_sc

def main():
    if not os.path.exists(METRICS):
        raise SystemExit(f"[error] missing {os.path.relpath(METRICS, ROOT)}")
    df = pd.read_csv(METRICS)
    need = {"indicator","horizon","origin_year","metric","loss","method"}
    if not need.issubset(df.columns):
        miss = need - set(df.columns)
        raise SystemExit(f"[error] metrics file missing columns: {miss}")

    meta_sc, eq_sc = ensure_series(df)
    if meta_sc.empty or eq_sc.empty:
        raise SystemExit("[error] need both meta_stack and equal_weight (even after rebuild).")

    # join on triplets
    key = ["indicator","horizon","origin_year"]
    piv = meta_sc.merge(eq_sc, on=key, how="inner", suffixes=("_meta","_eq"))
    if piv.empty:
        raise SystemExit("[error] no overlapping triplets between meta and eq series.")

    rows, pvals = [], []
    for (ind, h), g in piv.groupby(["indicator","horizon"]):
        g = g.sort_values("origin_year")
        d = (g["loss_meta"] - g["loss_eq"]).to_numpy()  # negative is good
        n = len(d)
        if n < 3:
            continue
        L = max(int(h) - 1, 0)
        var_mean = newey_west_variance(d, L=L)
        if not np.isfinite(var_mean) or var_mean <= 0:
            continue
        dm = float(np.mean(d) / math.sqrt(var_mean))
        p = 2.0 * (1.0 - student_t.cdf(abs(dm), df=n-1))
        pvals.append(p)
        rows.append(dict(indicator=str(ind), horizon=int(h), n_obs=int(n),
                         mean_delta=float(np.mean(d)), dm_stat=dm, p_value=p))

    out = pd.DataFrame(rows)
    if not out.empty:
        out["p_fdr"] = benjamini_hochberg(out["p_value"].to_numpy())
        out["significant"] = out["p_fdr"] < 0.10
    os.makedirs(RES, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[ok] wrote {OUT} rows={len(out)}")
    if not out.empty:
        win_share = (out["mean_delta"] < 0).mean()
        sig_share = (out["significant"] == True).mean()
        print(f"[summary] share(meta < eq)={win_share:.1%} | share(significant FDR 10%)={sig_share:.1%}")

if __name__ == "__main__":
    main()
