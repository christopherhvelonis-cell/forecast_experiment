# from repo root
@'
# -*- coding: utf-8 -*-
#!/usr/bin/env python
import numpy as np, pandas as pd
from pathlib import Path
from statsmodels.stats.multitest import multipletests
import scipy.stats as st

SRC = Path("eval/results/ensemble_retro_v2_postcal/metrics_ENSEMBLE.csv")
OUT = Path("eval/results/ensemble_vs_ew_significance.csv")

def dm_simple(d):
    n = len(d); m = float(np.mean(d))
    s = float(np.std(d, ddof=1)) if n>1 else np.nan
    t = m / (s/np.sqrt(n)) if (n>1 and s>0) else np.nan
    p = 2*st.t.sf(abs(t), df=n-1) if (n>1 and np.isfinite(t)) else np.nan
    return m, s, n, t, p

def main():
    df = pd.read_csv(SRC)
    rows=[]
    for h, g in df.groupby("h"):
        d_crps  = (g["crps_ew"].values - g["crps_ens"].values)      # + => ensemble better
        d_brier = (g["brier_ew"].values - g["brier_ens"].values)
        mC,sC,nC,tC,pC = dm_simple(d_crps)
        mB,sB,nB,tB,pB = dm_simple(d_brier)
        rows.append({"h":h,"n":nC,
                     "mean_diff_crps":mC,"t_crps":tC,"p_crps":pC,
                     "mean_diff_brier":mB,"t_brier":tB,"p_brier":pB})
    res = pd.DataFrame(rows).sort_values("h").reset_index(drop=True)
    for pcol, qcol, rejcol in [("p_crps","q_crps","rej_crps"),("p_brier","q_brier","rej_brier")]:
        pvals = res[pcol].to_numpy()
        mask = np.isfinite(pvals)
        q = np.full_like(pvals, np.nan, dtype=float)
        rej = np.full_like(pvals, False, dtype=bool)
        if mask.any():
            r, qvals, _, _ = multipletests(pvals[mask], alpha=0.10, method="fdr_bh")
            q[mask] = qvals; rej[mask] = r
        res[qcol] = q; res[rejcol] = rej
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print(f"[ok] wrote {OUT}")

if __name__ == "__main__":
    raise SystemExit(main())
'@ | Set-Content -Encoding UTF8 .\eval\ens_vs_ew_significance.py

python .\eval\ens_vs_ew_significance.py
type .\eval\results\ensemble_vs_ew_significance.csv
