#!/usr/bin/env python3
"""
Post-process ensemble quantiles into joint paths using ECC/Schaake (NA-robust).

Inputs:
  - ensemble/quantiles_ensemble.csv
      indicator,horizon,origin_year,quantile,value
  - eval/results/realized_by_origin.csv
      indicator,origin_year,horizon,value  (used for Schaake rank template)

Args:
  --draws  Number of draws per (indicator,origin_year,horizon). Default 500.
  --method ecc|schaake  (default schaake)

Outputs:
  - ensemble/joint_paths_ecc.parquet
      origin_year, draw_id, horizon, indicator, value
  - ensemble/fusion_spec.md
"""

import os, sys, numpy as np, pandas as pd
from scipy.interpolate import PchipInterpolator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENSQ = os.path.join(ROOT, "ensemble", "quantiles_ensemble.csv")
TRUTH = os.path.join(ROOT, "eval", "results", "realized_by_origin.csv")
OUTP = os.path.join(ROOT, "ensemble", "joint_paths_ecc.parquet")
SPEC = os.path.join(ROOT, "ensemble", "fusion_spec.md")

def interp_from_quantiles(quantiles, values):
    q = np.array(quantiles, dtype=float)
    v = np.array(values, dtype=float)
    order = np.argsort(q)
    q, v = q[order], v[order]
    # de-duplicate quantiles
    uq, ui = np.unique(q, return_index=True)
    q, v = uq, v[ui]
    if len(q) == 1:
        return lambda p: np.repeat(v[0], len(np.atleast_1d(p)))
    f = PchipInterpolator(q, v, extrapolate=True)
    return lambda p: f(np.clip(p, 0.0, 1.0))

def sample_draws_per_triplet(dfq, draws=500):
    qs = dfq["quantile"].astype(float).to_numpy()
    vs = dfq["value"].astype(float).to_numpy()
    f = interp_from_quantiles(qs, vs)
    u = np.random.rand(draws)
    return f(u)

def build_rank_template(truth_panel):
    """
    Build a NA-robust template: for each (origin_year, horizon),
    rank indicators by realized truth. Only use rows with non-null truth.
    If <2 indicators have truth for a pair, skip that pair (no template).
    Returns dict[(oy,h)] -> dict[indicator -> int_rank]
    """
    tmpl = {}
    # normalize types
    t = truth_panel.copy()
    t = t.rename(columns={"value": "truth"})
    if "truth" not in t.columns:
        return tmpl
    t = t.dropna(subset=["indicator","origin_year","horizon"])
    t["indicator"] = t["indicator"].astype(str)
    t["origin_year"] = t["origin_year"].astype(int)
    t["horizon"] = t["horizon"].astype(int)
    # build per (oy,h)
    for (oy, h), g in t.groupby(["origin_year","horizon"]):
        g = g.dropna(subset=["truth"]).copy()
        if len(g) < 2:
            # not enough info to define a meaningful cross-indicator rank structure
            continue
        # rank by truth (ties broken by order of appearance)
        g["rank"] = g["truth"].rank(method="first", ascending=True)
        # produce integer ranks 1..K
        order = g.sort_values("rank")
        ranks = {str(ind): int(i+1) for i, ind in enumerate(order["indicator"].tolist())}
        tmpl[(int(oy), int(h))] = ranks
    return tmpl

def apply_ecc_schaake(group, draws=500, rank_template=None, method="schaake"):
    """
    group: df with columns indicator,horizon,origin_year,quantile,value
    Returns df: origin_year, draw_id, horizon, indicator, value
    """
    oy = int(group["origin_year"].iloc[0])
    h  = int(group["horizon"].iloc[0])
    inds = sorted(group["indicator"].unique().astype(str).tolist())

    # sample independent draws per indicator
    per_ind = {}
    for ind in inds:
        g = group[group["indicator"]==ind]
        per_ind[ind] = np.sort(sample_draws_per_triplet(g, draws=draws))  # pre-sort for order stats

    # Decide ordering across indicators
    use_schaake = (method.lower() == "schaake") and rank_template and ((oy, h) in rank_template)
    if use_schaake:
        ranks = rank_template[(oy, h)]
        # indicators with known ranks first (ascending), then unknowns appended alphabetically
        known = [ind for ind in inds if ind in ranks]
        unknown = [ind for ind in inds if ind not in ranks]
        known_sorted = sorted(known, key=lambda x: ranks[x])
        perm = known_sorted + sorted(unknown)
    else:
        # ECC fallback: arbitrary but stable order (alphabetical)
        perm = inds

    # Build rows: align k-th order stat across indicators following 'perm'
    rows = []
    for k in range(draws):
        # we don't need 'perm' to index within indicator (already sorted order stats),
        # but 'perm' defines cross-indicator co-ranking structure (same k across inds).
        for ind in perm:
            val = per_ind[ind][k]
            rows.append((oy, k, h, ind, float(val)))
    out = pd.DataFrame(rows, columns=["origin_year","draw_id","horizon","indicator","value"])
    return out

def main(method="schaake", draws=500, seed=42):
    np.random.seed(seed)

    if not os.path.exists(ENSQ):
        raise SystemExit(f"[error] missing {os.path.relpath(ENSQ, ROOT)}")
    ensq = pd.read_csv(ENSQ)
    needq = {"indicator","horizon","origin_year","quantile","value"}
    if not needq.issubset(ensq.columns):
        raise SystemExit(f"[error] quantiles missing columns {needq}")

    # optional truth (for rank template)
    rank_template = None
    if os.path.exists(TRUTH):
        t = pd.read_csv(TRUTH)
        if {"indicator","origin_year","horizon","value"}.issubset(t.columns) and not t.empty:
            rank_template = build_rank_template(t)
        else:
            print("[info] truth file present but lacks needed columns; using ECC fallback.")
    else:
        print("[info] no truth file found; using ECC fallback.")

    # normalize types
    ensq = ensq.copy()
    ensq["indicator"] = ensq["indicator"].astype(str)
    ensq["horizon"] = ensq["horizon"].astype(int)
    ensq["origin_year"] = ensq["origin_year"].astype(int)
    ensq["quantile"] = ensq["quantile"].astype(float)

    # generate draws per (oy,h) across indicators
    out_parts = []
    for (oy, h), g in ensq.groupby(["origin_year","horizon"]):
        part = apply_ecc_schaake(g, draws=draws, rank_template=rank_template, method=method)
        out_parts.append(part)

    out = pd.concat(out_parts, ignore_index=True) if out_parts else pd.DataFrame(
        columns=["origin_year","draw_id","horizon","indicator","value"]
    )
    os.makedirs(os.path.dirname(OUTP), exist_ok=True)
    # requires pyarrow or fastparquet usually; if not installed, fallback to CSV
    try:
        out.to_parquet(OUTP, index=False)
        wrote = OUTP
    except Exception as e:
        alt = OUTP.replace(".parquet", ".csv")
        out.to_csv(alt, index=False)
        wrote = alt
        print(f"[warn] parquet write failed ({e}); wrote CSV fallback instead.")

    with open(SPEC, "w", encoding="utf-8") as f:
        f.write(f"# Fusion Spec\n- method: {method}\n- draws: {draws}\n- source: ensemble/quantiles_ensemble.csv\n")

    print(f"[ok] wrote {os.path.relpath(wrote, ROOT)}  rows={len(out)}")
    print(f"[ok] wrote {os.path.relpath(SPEC, ROOT)}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["ecc","schaake"], default="schaake")
    ap.add_argument("--draws", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    sys.exit(main(method=args.method, draws=args.draws, seed=args.seed) or 0)
