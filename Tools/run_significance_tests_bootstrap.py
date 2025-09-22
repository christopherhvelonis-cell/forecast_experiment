#!/usr/bin/env python3
"""
Block-bootstrap significance for meta_stack vs equal_weight with robust fallbacks
and optional horizon pooling (to increase sample size).

- Normalizes method names in metrics_by_horizon_ensemble.csv
- If a method is missing, rebuilds its losses directly from inputs:
    * meta_stack  -> ensemble/quantiles_ensemble.csv + realized_by_origin.csv
    * equal_weight-> eval/results/quantiles_by_model.csv + realized_by_origin.csv
- Uses moving-block bootstrap to test mean loss difference.
- Works even with very small T (>=2), though power is limited.
- If there are too few origins per (indicator, horizon), you can pool horizons
  into buckets of size K (e.g., 3 => buckets 1–3, 4–6, ...).

Outputs:
  eval/results/significance_dm_bootstrap.csv
"""

import os, math, numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
METRICS = os.path.join(RES, "metrics_by_horizon_ensemble.csv")
Q_ENSEMBLE = os.path.join(ROOT, "ensemble", "quantiles_ensemble.csv")
Q_BY_MODEL = os.path.join(RES, "quantiles_by_model.csv")
TRUTH_IN   = os.path.join(RES, "realized_by_origin.csv")
OUT = os.path.join(RES, "significance_dm_bootstrap.csv")

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
                             loss=float(np.mean(losses)), method=method_tag))
    return pd.DataFrame(rows)

def build_equal_weight_quantiles(qbm):
    return (qbm.groupby(["indicator","horizon","origin_year","quantile"], as_index=False)["value"]
               .mean())

def ensure_series(df_metrics):
    """Return meta_sc, eq_sc with cols indicator,horizon,origin_year,loss."""
    df = df_metrics.copy()
    df["method"] = df["method"].apply(norm_method)
    df = df[df["metric"].str.lower()=="composite"]
    meta_sc = df[df["method"]=="meta_stack"][["indicator","horizon","origin_year","loss"]].copy()
    eq_sc   = df[df["method"]=="equal_weight"][["indicator","horizon","origin_year","loss"]].copy()

    have_meta = not meta_sc.empty
    have_eq   = not eq_sc.empty
    if have_meta and have_eq:
        return meta_sc, eq_sc

    # Fallback rebuild(s) from quantiles + truths
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

def moving_block_bootstrap_mean(x, B, R=5000, seed=123):
    x = np.asarray(x, float)
    T = len(x)
    if T == 0:
        return np.array([])
    rng = np.random.default_rng(seed)
    B = int(max(1, B))
    if B >= T:
        blocks = [x]
    else:
        blocks = [x[i:i+B] for i in range(0, T-B+1)]
    K = len(blocks)
    m = int(math.ceil(T / float(B)))
    means = np.empty(R, float)
    for r in range(R):
        idx = rng.integers(0, K, size=m)
        sample = np.concatenate([blocks[i] for i in idx])[:T]
        means[r] = sample.mean()
    return means

def horizon_bucket(h, k):
    """Map horizon h (int) to a bucket label of size k: 1..k -> 1, k+1..2k -> 2, ..."""
    h = int(h)
    k = max(1, int(k))
    return (h-1)//k + 1

def main(B=None, R=5000, alpha=0.10, seed=123, pool_k=1):
    if not os.path.exists(METRICS):
        raise SystemExit(f"[error] missing {os.path.relpath(METRICS, ROOT)}")
    dfm = pd.read_csv(METRICS)
    need = {"indicator","horizon","origin_year","metric","loss","method"}
    if not need.issubset(dfm.columns):
        miss = need - set(dfm.columns)
        raise SystemExit(f"[error] metrics file missing columns: {miss}")

    meta_sc, eq_sc = ensure_series(dfm)
    if meta_sc.empty or eq_sc.empty:
        raise SystemExit("[error] need both meta_stack and equal_weight (even after rebuild).")

    key = ["indicator","horizon","origin_year"]
    piv = meta_sc.merge(eq_sc, on=key, how="inner", suffixes=("_meta","_eq"))
    if piv.empty:
        raise SystemExit("[error] no overlapping triplets between meta and eq series.")

    # Optional horizon pooling
    if pool_k > 1:
        piv = piv.copy()
        piv["h_bucket"] = piv["horizon"].apply(lambda h: horizon_bucket(h, pool_k))
        group_keys = ["indicator","h_bucket"]
    else:
        group_keys = ["indicator","horizon"]

    rows = []
    for keys, g in piv.groupby(group_keys):
        g = g.sort_values("origin_year")
        d = (g["loss_meta"].to_numpy() - g["loss_eq"].to_numpy())  # neg is good
        T = len(d)
        if T < 2:
            continue
        # choose block length
        if pool_k > 1:
            # use the *median* horizon in this bucket as a reference for lag
            ref_h = int(g["horizon"].median())
        else:
            ref_h = int(keys[1])  # horizon
        B_eff = max(ref_h, 2) if B is None else int(B)
        boot = moving_block_bootstrap_mean(d, B=B_eff, R=R, seed=seed)
        if boot.size == 0:
            continue
        dbar = float(d.mean())
        p_right = np.mean(boot >= dbar)
        p_left  = np.mean(boot <= dbar)
        p_val = float(min(1.0, 2.0 * min(p_right, p_left)))
        lo, hi = np.percentile(boot, [100*alpha/2, 100*(1-alpha/2)])

        row = dict(
            indicator=str(keys[0]),
            n_obs=int(T),
            mean_delta=dbar, ci_lower=float(lo), ci_upper=float(hi),
            p_value=p_val, significant=bool(p_val < alpha)
        )
        if pool_k > 1:
            row["horizon_bucket"] = int(keys[1])
        else:
            row["horizon"] = int(keys[1])
        rows.append(row)

    # Build output DataFrame (graceful empty handling)
    cols = ["indicator","horizon","n_obs","mean_delta","ci_lower","ci_upper","p_value","significant"]
    if pool_k > 1:
        cols = ["indicator","horizon_bucket","n_obs","mean_delta","ci_lower","ci_upper","p_value","significant"]
    out = pd.DataFrame(rows, columns=cols)
    os.makedirs(RES, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[ok] wrote {OUT} rows={len(out)}")
    if not out.empty:
        win_share = (out["mean_delta"] < 0).mean()
        sig_share = (out["significant"] == True).mean()
        print(f"[summary] share(meta < eq)={win_share:.1%} | share(significant at {int(100*alpha)}%): {sig_share:.1%}")
    else:
        print("[info] no groups had ≥2 observations; try --pool_horizons 3 to pool horizons.")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=None, help="Block length B (default max(h,2))")
    ap.add_argument("--resamples", type=int, default=5000)
    ap.add_argument("--alpha", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--pool_horizons", type=int, default=1, help="Pool horizons into buckets of this size (e.g., 3 => 1–3, 4–6, ...)")
    args = ap.parse_args()
    main(B=args.blocks, R=args.resamples, alpha=args.alpha, seed=args.seed, pool_k=args.pool_horizons)
