import os, sys
from pathlib import Path
import numpy as np
import pandas as pd

# --- Path fixes: make sure models/common is importable ---
REPO = Path(__file__).resolve().parent
COMMON_DIR = REPO / "models" / "common"
sys.path.insert(0, str(COMMON_DIR))
sys.path.insert(0, str(REPO / "models" / "HSM_chatgpt"))

from utils import load_indicator        # from models/common/utils.py
from models.HSM_chatgpt.hsm import hsm_forecast

# --- CRPS helpers (Gaussian closed form) ---
def _phi(z): return np.exp(-0.5*z*z)/np.sqrt(2*np.pi)
def _Phi(z): return 0.5*(1.0+np.erf(z/np.sqrt(2)))
def crps_gaussian(y, mu, sigma):
    sigma = np.maximum(sigma, 1e-9)
    z = (y - mu) / sigma
    return sigma * (z * (2.0 * _Phi(z) - 1.0) + 2.0 * _phi(z) - 1.0/np.sqrt(np.pi))

def _infer_mu_sigma_from_quantiles(qrow):
    """Given q5,q50,q95 for one horizon, infer mu≈q50, sigma from spread."""
    mu = float(qrow["q50"])
    spread = float(qrow["q95"] - qrow.get("q5", qrow["q95"]))  # guard if q5 missing
    sigma = max(spread / 3.2897, 1e-6)  # 3.2897 ≈ z95 - z05
    return mu, sigma

def evaluate_hsm(indicators, origins, H=15, out_csv="eval/results/hsm_crps_summary.csv"):
    rows = []
    for origin in origins:
        qdict = hsm_forecast(indicators, origin, H)
        for ind in indicators:
            s = load_indicator(ind)  # year-indexed series
            for h in range(1, H+1):
                target_year = origin + h
                if target_year not in s.index:
                    continue
                y = float(s.loc[target_year])
                qrow = qdict[ind].loc[h]
                mu, sigma = _infer_mu_sigma_from_quantiles(qrow)
                crps = float(crps_gaussian(np.array([y]), np.array([mu]), np.array([sigma]))[0])
                rows.append({"indicator": ind, "origin": origin, "horizon": h,
                             "y": y, "mu": mu, "sigma": sigma, "crps": crps})
    df = pd.DataFrame(rows)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df

if __name__ == "__main__":
    # Example with ANES (will have few targets)
    indicators = ["anes_V242270", "anes_V242271"]
    origins = [2024]
    df = evaluate_hsm(indicators, origins, H=15, out_csv="eval/results/hsm_crps_anes.csv")
    print(f"[Evaluator] wrote eval/results/hsm_crps_anes.csv with {len(df)} rows")
