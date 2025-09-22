#!/usr/bin/env python3
"""
Normalize eval/results/perf_by_model.csv so it has columns:
indicator,horizon,origin_year,model,composite

Heuristics:
- If a 'composite' column already exists, keep it.
- Else if there's 'loss' or 'composite_loss', use that.
- Else if there are both CRPS and Brier columns, make composite = 0.5*crps + 0.5*brier.
- Else, try to build from quantiles + realized truths (pinball at 0.05,0.5,0.95).
"""
import os, sys, numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
PERF = os.path.join(RES, "perf_by_model.csv")
QBM  = os.path.join(RES, "quantiles_by_model.csv")
TRUTH= os.path.join(RES, "realized_by_origin.csv")
OUT  = PERF  # in-place normalize

def pinball(y, q, tau):
    u = y - q
    return tau*np.maximum(u,0.0) + (tau-1.0)*np.minimum(u,0.0)

def composite_from_quantiles(qbm, truth):
    TAUS = [0.05, 0.5, 0.95]
    m = qbm.merge(truth, on=["indicator","origin_year","horizon"])
    rows = []
    for (ind,h,oy,mdl), g in m.groupby(["indicator","horizon","origin_year","model"]):
        y = float(g["truth"].iloc[0])
        losses=[]
        for t in TAUS:
            gi = g.loc[np.isclose(g["quantile"].astype(float), t), "value"]
            if gi.empty: continue
            losses.append(float(pinball(y, float(gi.iloc[0]), t)))
        if losses:
            rows.append(dict(indicator=str(ind), horizon=int(h), origin_year=int(oy),
                             model=str(mdl), composite=float(np.mean(losses))))
    return pd.DataFrame(rows)

def main():
    if not os.path.exists(PERF):
        raise SystemExit(f"[error] missing {os.path.relpath(PERF, ROOT)}")
    df = pd.read_csv(PERF)
    need_keys = {"indicator","horizon","origin_year","model"}
    if not need_keys.issubset(df.columns):
        miss = need_keys - set(df.columns)
        raise SystemExit(f"[error] perf_by_model missing keys: {miss}")

    # Fast paths
    if "composite" in df.columns:
        out = df.copy()
    elif "composite_loss" in df.columns:
        out = df.rename(columns={"composite_loss":"composite"}).copy()
    elif "loss" in df.columns:
        out = df.rename(columns={"loss":"composite"}).copy()
    elif {"crps","brier"}.issubset(df.columns):
        out = df.copy()
        out["composite"] = 0.5*out["crps"].astype(float) + 0.5*out["brier"].astype(float)
    else:
        # Build from quantiles + truths
        if not (os.path.exists(QBM) and os.path.exists(TRUTH)):
            raise SystemExit("[error] no composite/loss columns and cannot rebuild: quantiles/truths missing.")
        q = pd.read_csv(QBM)
        t = pd.read_csv(TRUTH).rename(columns={"value":"truth"})
        needq = {"indicator","horizon","origin_year","model","quantile","value"}
        needt = {"indicator","horizon","origin_year","truth"}
        if not needq.issubset(q.columns) or not needt.issubset(t.columns):
            raise SystemExit("[error] inputs for rebuild missing required columns.")
        comp = composite_from_quantiles(q, t)
        out = df.drop(columns=[c for c in df.columns if c=="composite"], errors="ignore") \
                .merge(comp, on=["indicator","horizon","origin_year","model"], how="left")
        if out["composite"].isna().any():
            raise SystemExit("[error] failed to compute composite for some rows.")

    # Type safety + write
    out = out.copy()
    out["indicator"] = out["indicator"].astype(str)
    out["horizon"] = out["horizon"].astype(int)
    out["origin_year"] = out["origin_year"].astype(int)
    out["model"] = out["model"].astype(str)
    out["composite"] = out["composite"].astype(float)

    out.to_csv(OUT, index=False)
    print(f"[ok] normalized perf_by_model.csv -> columns: {list(out.columns)}  rows={len(out)}")

if __name__ == "__main__":
    main()
