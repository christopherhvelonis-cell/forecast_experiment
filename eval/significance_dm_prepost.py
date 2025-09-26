#!/usr/bin/env python
import numpy as np, pandas as pd
from pathlib import Path
from math import sqrt
from statsmodels.stats.multitest import multipletests
import scipy.stats as st

PRE  = Path("eval/results/retro_v2")
POST = Path("eval/results/retro_v2_postcal")

def load_side(folder: Path) -> pd.DataFrame:
    rows=[]
    for f in sorted(folder.glob("metrics_*.csv")):
        origin = int(f.stem.split("_")[1])
        df = pd.read_csv(f, usecols=["h","crps","brier"])
        df["origin"]=origin
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def dm_simple(d: np.ndarray):
    n = len(d); m = float(np.mean(d))
    s = float(np.std(d, ddof=1)) if n>1 else np.nan
    t = m / (s/np.sqrt(n)) if (n>1 and s>0) else np.nan
    p = 2*st.t.sf(abs(t), df=n-1) if (n>1 and np.isfinite(t)) else np.nan
    return m, s, n, t, p

def main():
    pre, post = load_side(PRE), load_side(POST)
    if pre.empty or post.empty:
        print("[err] missing pre or post metrics"); return 1
    merged = pre.merge(post, on=["origin","h"], suffixes=("_pre","_post"))

    out_rows=[]
    for h, g in merged.groupby("h"):
        d_crps  = (g["crps_pre"].values  - g["crps_post"].values)
        d_brier = (g["brier_pre"].values - g["brier_post"].values)
        mC,sC,nC,tC,pC = dm_simple(d_crps)
        mB,sB,nB,tB,pB = dm_simple(d_brier)
        out_rows.append({"h": h, "n_origins": nC,
                         "mean_diff_crps": mC, "t_crps": tC, "p_crps": pC,
                         "mean_diff_brier": mB, "t_brier": tB, "p_brier": pB})
    res = pd.DataFrame(out_rows).sort_values("h").reset_index(drop=True)

    for pcol, qcol, rejcol in [("p_crps","q_crps","rej_crps"),
                               ("p_brier","q_brier","rej_brier")]:
        pvals = res[pcol].to_numpy()
        mask = np.isfinite(pvals)
        q = np.full_like(pvals, np.nan, dtype=float)
        rej = np.full_like(pvals, False, dtype=bool)
        if mask.any():
            r, qvals, _, _ = multipletests(pvals[mask], alpha=0.10, method="fdr_bh")
            q[mask] = qvals; rej[mask] = r
        res[qcol] = q; res[rejcol] = rej

    out = Path("eval/results/significance_dm_prepost.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False)
    print(f"[ok] wrote {out}")

if __name__ == "__main__":
    raise SystemExit(main())
