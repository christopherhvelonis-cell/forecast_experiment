import os, sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

# paths
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "models" / "common"))

from utils import load_indicator

Z95 = 1.6448536269514722

def infer_mu_sigma(q5, q50, q95):
    mu = float(q50)
    sigma = max((float(q95) - float(q5)) / (2 * Z95), 1e-6)
    return mu, sigma

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origins", nargs="+", required=True, type=int)
    ap.add_argument("--h", type=int, default=15)
    ap.add_argument("--in_csv", required=True, help="Quantiles CSV to calibrate (e.g., hsm_quantiles_calibrated.csv)")
    ap.add_argument("--out_csv", default="eval/results/hsm_quantiles_calibrated_mean.csv")
    args = ap.parse_args()

    q = pd.read_csv(args.in_csv)   # columns: indicator,horizon,q5,q50,q95
    if not set(["indicator","horizon","q5","q50","q95"]).issubset(q.columns):
        raise ValueError("Expected columns indicator,horizon,q5,q50,q95 in --in_csv")

    # collect (mu, y) pairs across origins/horizons to fit per-indicator affine correction
    fits = {}
    for ind in args.indicators:
        mus, ys = [], []
        for origin in args.origins:
            s = load_indicator(ind)  # observed series, indexed by year
            # reconstruct mu per horizon from the same quantiles file (assumes latest origin == max(args.origins))
            sub = q[q["indicator"] == ind].set_index("horizon").sort_index()
            for h in range(1, args.h + 1):
                yr = origin + h
                if yr not in s.index or h not in sub.index:
                    continue
                mu, _ = infer_mu_sigma(sub.loc[h,"q5"], sub.loc[h,"q50"], sub.loc[h,"q95"])
                mus.append(mu)
                ys.append(float(s.loc[yr]))
        if len(mus) < 3:
            fits[ind] = (0.0, 1.0)  # a=0, b=1 (no change)
            continue
        X = np.column_stack([np.ones(len(mus)), np.array(mus, dtype=float)])
        y = np.array(ys, dtype=float)
        # OLS for y ~ a + b*mu
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        a, b = float(beta[0]), float(beta[1])
        fits[ind] = (a, b)

    # apply μ' = a + b μ to the SAME quantiles table (keep σ from q5/q95)
    out_rows = []
    for ind in args.indicators:
        a, b = fits[ind]
        sub = q[q["indicator"] == ind].copy()
        # infer sigma from q5/q95 and recompute q5,q50,q95 with shifted mu'
        mu = sub["q50"].astype(float).to_numpy()
        sigma = (sub["q95"].astype(float).to_numpy() - sub["q5"].astype(float).to_numpy()) / (2 * Z95)
        mu_p = a + b * mu
        sigma = np.maximum(sigma, 1e-6)
        sub["q50"] = mu_p
        sub["q5"]  = mu_p - Z95 * sigma
        sub["q95"] = mu_p + Z95 * sigma
        out_rows.append(sub)

    out = pd.concat(out_rows, ignore_index=True)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)

    # also save the fitted (a,b)
    pd.DataFrame([{"indicator": k, "a": v[0], "b": v[1]} for k, v in fits.items()])\
      .to_csv(Path(args.out_csv).with_suffix("").as_posix()+"_means.csv", index=False)

    print(f"[MeanCal] wrote {args.out_csv}")
    print(f"[MeanCal] wrote {Path(args.out_csv).with_suffix('').as_posix()}_means.csv")

if __name__ == "__main__":
    main()
