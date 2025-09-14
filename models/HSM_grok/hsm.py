# models/HSM_grok/hsm.py
from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd
from copulae import GaussianCopula
from statsmodels.tsa.statespace.kalman_filter import KalmanFilter

from models.common.utils import make_origin_panel, save_quantiles_csv

def hsm_forecast(indicators: List[str], origin_year: int, H: int = 15, H_scenario: int = 40) -> Dict[str, Dict[int, Dict[str, float]]]:
    """Forecast indicators using a multivariate state-space model with ECC post-processing."""
    panel = make_origin_panel(indicators, origin_year, min_len=8)
    data = pd.DataFrame({ind: s for ind, s in panel.items()}).dropna(how='any')
    
    # Normalize data (z-score)
    means = data.mean()
    stds = data.std()
    data_normalized = (data - means) / stds
    
    # State-space model (level + trend per indicator)
    k_states = len(indicators) * 2  # Level + trend
    model = KalmanFilter(
        endog=data_normalized,
        k_endog=len(indicators),
        k_states=k_states,
        transition=np.block([
            [np.eye(len(indicators)), np.eye(len(indicators))],
            [np.zeros((len(indicators), len(indicators))), np.eye(len(indicators))]
        ]),
        observation=np.block([[np.eye(len(indicators)), np.zeros((len(indicators), len(indicators)))]]),
        state_cov=np.diag([0.1] * k_states)
    )
    results = model.fit()
    
    # Forecast
    forecasts = []
    for h in range(1, max(H, H_scenario) + 1):
        pred = results.forecast(h)[-1]
        pred = pred * stds + means  # Denormalize
        forecasts.append(pred)
    
    # Quantiles
    out: Dict[str, Dict[int, Dict[str, float]]] = {ind: {} for ind in indicators}
    for h in range(1, max(H, H_scenario) + 1):
        for i, ind in enumerate(indicators):
            pred_h = forecasts[h-1][i]
            sigma = stds[ind] * np.sqrt(h)
            out[ind][h] = {
                "q05": float(pred_h - 1.645 * sigma),
                "q50": float(pred_h),
                "q95": float(pred_h + 1.645 * sigma),
            }

    # ECC post-processing
    corr = pd.read_csv("data/processed/corr_matrix.csv", index_col=0)
    corr = corr.loc[indicators, indicators]
    copula = GaussianCopula(dim=len(indicators), rho=corr.values)
    quantiles = np.array([[[out[ind][h]["q05"], out[ind][h]["q50"], out[ind][h]["q95"]] for h in range(1, max(H, H_scenario) + 1)] for ind in indicators])
    quantiles_joint = copula.sample(quantiles.transpose(1, 0, 2), n=10000)
    for i, ind in enumerate(indicators):
        for h in range(1, max(H, H_scenario) + 1):
            out[ind][h] = {
                "q05": float(np.percentile(quantiles_joint[:, h-1, i, 0], 5)),
                "q50": float(np.percentile(quantiles_joint[:, h-1, i, 1], 50)),
                "q95": float(np.percentile(quantiles_joint[:, h-1, i, 2], 95)),
            }

    # Calibration
    for ind in indicators:
        s = panel[ind]
        diffs = [s.iloc[-1] - out[ind][1]["q50"]]
        mean_adj = float(np.nanmean(diffs)) if diffs else 0.0
        sigma_scale = np.std(s) / np.std([out[ind][h]["q50"] for h in range(1, H+1)]) if H > 0 else 1.0
        for h in range(1, max(H, H_scenario) + 1):
            out[ind][h]["q05"] = out[ind][h]["q05"] * sigma_scale + mean_adj
            out[ind][h]["q50"] = out[ind][h]["q50"] * sigma_scale + mean_adj
            out[ind][h]["q95"] = out[ind][h]["q95"] * sigma_scale + mean_adj
    
    # Event probabilities
    event_probs = {
        'trust_below_20': [(out['public_trust_government'][h]['q50'] < 20) for h in [1, 3, 5, 10, 15]],
        'turnout_above_65': [(out['vep_turnout_pct'][h]['q50'] >= 65) for h in [1, 3, 5, 10, 15]],
        'polarization_above_50': [(out['mass_public_polarization'][h]['q50'] > 50) for h in [1, 3, 5, 10, 15]],
    }
    pd.DataFrame(event_probs, index=[2026, 2028, 2030, 2035, 2040]).to_csv("models/HSM_grok/event_probs.csv")
    
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--h", type=int, default=15)
    ap.add_argument("--h_scenario", type=int, default=40)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    qdict = hsm_forecast(args.indicators, args.origin, args.h, args.h_scenario)
    save_quantiles_csv(qdict, Path(args.out))
    print(f"[HSM_grok] wrote {args.out}")

if __name__ == "__main__":
    main()