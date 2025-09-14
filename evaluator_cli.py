import os, sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from math import erf  # use math.erf, always available

# Paths
REPO = Path(__file__).resolve().parent
COMMON_DIR = REPO / "models" / "common"
HSM_DIR = REPO / "models" / "HSM_chatgpt"
sys.path.insert(0, str(COMMON_DIR))
sys.path.insert(0, str(HSM_DIR))

from utils import load_indicator
from models.HSM_chatgpt.hsm import hsm_forecast

# CRPS (Gaussian)
def _phi(z): 
    return np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)

def _Phi(z): 
    return 0.5 * (1.0 + np.vectorize(erf)(z / np.sqrt(2.0)))

def crps_gaussian(y, mu, sigma):
    sigma = np.maximum(sigma, 1e-9)
    z = (y - mu) / sigma
    return sigma * (z * (2.0 * _Phi(z) - 1.0) + 2.0 * _phi(z) - 1.0/np.sqrt(np.pi))

def infer_mu_sigma(qrow):
    mu = float(qrow["q50"])
    spread = float(qrow["q95"] - qrow.get("q5", qrow["q95"]))
    sigma = max(spread / 3.2897, 1e-6)  # 3.2897 ≈ z95 - z05
    return mu, sigma

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origins", nargs="+", required=True, type=int)
    ap.add_argument("--h", type=int, default=15)
    ap.add_argument("--out", type=str, default="eval/results/hsm_crps.csv")
    args = ap.parse_args()

    rows = []
    for origin in args.origins:
        qdict = hsm_forecast(args.indicators, origin, args.h)
        for ind in args.indicators:
            s = load_indicator(ind)
            for h in range(1, args.h + 1):
                target_year = origin + h
                if target_year not in s.index:
                    continue
                y = float(s.loc[target_year])
                qrow = qdict[ind].loc[h]
                mu, sigma = infer_mu_sigma(qrow)
                crps = float(crps_gaussian(np.array([y]), np.array([mu]), np.array([sigma]))[0])
                rows.append({
                    "indicator": ind, "origin": origin, "horizon": h,
                    "y": y, "mu": mu, "sigma": sigma, "crps": crps
                })
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"[Evaluator] wrote {args.out} with {len(df)} rows")

if __name__ == "__main__":
    main()
