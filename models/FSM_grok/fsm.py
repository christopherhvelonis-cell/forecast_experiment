# models/FSM_grok/fsm.py
from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd
from scipy.stats import poisson, t
from copulae import GaussianCopula

from models.common.utils import make_origin_panel, save_quantiles_csv

def fsm_forecast(
    indicators: List[str],
    origin_year: int,
    H_scored: int = 15,
    H_scenario: int = 40,
    n_paths: int = 10000,
    lam: float = 0.2,
    t_df: float = 4.0
) -> Dict[str, Dict[str, Dict[int, Dict[str, float]]]]:
    """Simulate indicator paths with random walk and shocks, ECC post-processed."""
    print(f"[DEBUG] Starting fsm_forecast for origin {origin_year}")
    panel = make_origin_panel(indicators, origin_year, min_len=8)
    data = pd.DataFrame({ind: s for ind, s in panel.items()}).dropna(how='any')
    print(f"[DEBUG] Data shape after dropna: {data.shape}")
    
    # Normalize data
    means = data.mean()
    stds = data.std()
    data_normalized = (data - means) / stds
    print(f"[DEBUG] Normalized data means: {means}, stds: {stds}")
    
    # Estimate drifts and volatilities, handle NaN and enforce minimum volatility
    drifts = data_normalized.diff().mean().fillna(0.0)
    volatilities = data_normalized.diff().std().fillna(0.1).clip(lower=0.1)  # Minimum volatility of 0.1
    print(f"[DEBUG] Drifts: {drifts}, Volatilities: {volatilities}")
    
    # Simulate paths
    res: Dict[str, Dict[str, Dict[int, Dict[str, float]]]] = {"scored": {ind: {} for ind in indicators}, "scenario": {ind: {} for ind in indicators}}
    paths_scored = np.zeros((len(indicators), n_paths, H_scored))
    paths_scenario = np.zeros((len(indicators), n_paths, H_scenario))
    
    for i, ind in enumerate(indicators):
        mu = means[ind]
        sigma = volatilities[ind]
        last_observed = data_normalized[ind].iloc[-1]
        print(f"[DEBUG] Processing indicator {ind}, mu={mu}, sigma={sigma}, last_observed={last_observed}")
        for j in range(n_paths):
            print(f"[DEBUG] Simulation path {j} for {ind}")
            x = last_observed
            for h in range(max(H_scored, H_scenario)):
                eps = np.random.normal(0.0, sigma)
                s = t.rvs(t_df, scale=sigma) if poisson.rvs(lam) > 0 else 0.0
                x = x + drifts[ind] + eps + s
                if h < H_scored:
                    paths_scored[i, j, h] = mu + stds[ind] * x
                if h < H_scenario:
                    paths_scenario[i, j, h] = mu + stds[ind] * x
    print(f"[DEBUG] Simulation completed, paths_scored shape: {paths_scored.shape}")

    # Quantiles
    print("[DEBUG] Calculating quantiles")
    for i, ind in enumerate(indicators):
        for h in range(1, H_scored + 1):
            p = paths_scored[i, :, h-1]
            res["scored"][ind][h] = {
                "q05": float(np.quantile(p, 0.05)),
                "q50": float(np.quantile(p, 0.50)),
                "q95": float(np.quantile(p, 0.95)),
            }
        for h in range(1, H_scenario + 1):
            p = paths_scenario[i, :, h-1]
            res["scenario"][ind][h] = {
                "q05": float(np.quantile(p, 0.05)),
                "q50": float(np.quantile(p, 0.50)),
                "q95": float(np.quantile(p, 0.95)),
            }

    # ECC post-processing
    print("[DEBUG] Starting ECC post-processing")
    corr = pd.read_csv("data/processed/corr_matrix.csv", index_col=0)
    corr = corr.loc[indicators, indicators]
    copula = GaussianCopula(dim=len(indicators))
    print(f"[DEBUG] Copula dim: {copula.dim}, Correlation matrix shape: {corr.shape}")
    sample_data = np.random.multivariate_normal(mean=np.zeros(len(indicators)), cov=corr.values, size=1000)
    copula.fit(sample_data)
    for key, H in [("scored", H_scored), ("scenario", H_scenario)]:
        quantiles = np.array([[[res[key][ind][h]["q05"], res[key][ind][h]["q50"], res[key][ind][h]["q95"]] for h in range(1, H+1)] for ind in indicators])
        print(f"[DEBUG] Quantiles shape: {quantiles.shape}")
        samples = copula.random(n_paths)  # Shape: (n_paths, dim)
        print(f"[DEBUG] Samples shape from copula.random: {samples.shape}")
        quantiles_joint = np.zeros((n_paths, H, len(indicators), 3))
        for i in range(n_paths):
            print(f"[DEBUG] Processing sample {i} for ECC")
            for j, ind in enumerate(indicators):
                for h in range(H):
                    quantiles_joint[i, h, j, 0] = np.percentile(samples[i, j], 5)
                    quantiles_joint[i, h, j, 1] = np.percentile(samples[i, j], 50)
                    quantiles_joint[i, h, j, 2] = np.percentile(samples[i, j], 95)
        print(f"[DEBUG] Quantiles_joint shape: {quantiles_joint.shape}")
        for i, ind in enumerate(indicators):
            for h in range(1, H + 1):
                res[key][ind][h] = {
                    "q05": float(np.mean(quantiles_joint[:, h-1, i, 0])),
                    "q50": float(np.mean(quantiles_joint[:, h-1, i, 1])),
                    "q95": float(np.mean(quantiles_joint[:, h-1, i, 2])),
                }

    # Calibration
    print("[DEBUG] Starting calibration")
    for ind in indicators:
        s = panel[ind]
        diffs = [s.iloc[-1] - res["scored"][ind][1]["q50"]]
        mean_adj = float(np.nanmean(diffs)) if diffs else 0.0
        sigma_scale = np.std(s) / np.std([res["scored"][ind][h]["q50"] for h in range(1, H_scored+1)]) if H_scored > 0 else 1.0
        for key in ["scored", "scenario"]:
            H = H_scored if key == "scored" else H_scenario
            for h in range(1, H + 1):
                res[key][ind][h]["q05"] = res[key][ind][h]["q05"] * sigma_scale + mean_adj
                res[key][ind][h]["q50"] = res[key][ind][h]["q50"] * sigma_scale + mean_adj
                res[key][ind][h]["q95"] = res[key][ind][h]["q95"] * sigma_scale + mean_adj

    # Event probabilities
    print("[DEBUG] Calculating event probabilities")
    event_probs = {
        'trust_below_20': [(res["scored"][ind][h]["q50"] < 20) if ind == 'public_trust_government' else np.nan for h in [1, 3, 5, 10, 15]],
        'turnout_above_65': [(res["scored"][ind][h]["q50"] >= 65) if ind == 'vep_turnout_pct' else np.nan for h in [1, 3, 5, 10, 15]],
        'polarization_above_50': [(res["scored"][ind][h]["q50"] > 50) if ind == 'mass_public_polarization' else np.nan for h in [1, 3, 5, 10, 15]],
    }
    pd.DataFrame(event_probs, index=[2026, 2028, 2030, 2035, 2040]).to_csv("models/FSM_grok/event_probs.csv")

    print("[DEBUG] Returning results")
    return res

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--h_scored", type=int, default=15)
    ap.add_argument("--h_scenario", type=int, default=40)
    ap.add_argument("--n_paths", type=int, default=10000)
    ap.add_argument("--lam", type=float, default=0.2)
    ap.add_argument("--t_df", type=float, default=4.0)
    ap.add_argument("--out_scored", type=str, required=True)
    ap.add_argument("--out_scenario", type=str, required=True)
    args = ap.parse_args()

    res = fsm_forecast(
        args.indicators, args.origin, args.h_scored, args.h_scenario, args.n_paths, args.lam, args.t_df
    )
    save_quantiles_csv(res["scored"], Path(args.out_scored))
    save_quantiles_csv(res["scenario"], Path(args.out_scenario))
    print(f"[FSM_grok] wrote {args.out_scored} and {args.out_scenario}")

if __name__ == "__main__":
    main()