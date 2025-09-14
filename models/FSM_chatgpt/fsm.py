# models/FSM_chatgpt/fsm.py
"""
FSM (Forward Simulation Model) - ChatGPT version, self-contained.

- For each indicator, fit a simple local-level-with-drift model to history <= origin:
      y_t = level_t + eps_t
      level_t = level_{t-1} + drift + eta_t
  eps_t ~ N(0, sigma_obs^2), eta_t ~ N(0, sigma_state^2)

- Simulate N paths forward for H_scored and H_scenario (same engine; caller decides which to save).
- Export distributional quantiles (q5, q50, q95) by horizon.

Notes:
- No external "postprocessing" imports (e.g., Schaake/ECC). This file stands alone.
- If you want dependence restoration (ECC/Schaake) across indicators, do it downstream in the ensemble layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")
MIN_HISTORY = 8
Z05 = 1.6448536269514722  # Phi^{-1}(0.95)


def _load_indicator_series(indicator: str) -> pd.DataFrame:
    path = DATA_DIR / f"{indicator}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Processed file not found for indicator '{indicator}': {path}")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "year" not in df.columns:
        # try to infer year from any year-like column or index
        year_col = None
        for c in df.columns:
            if c.startswith("year"):
                year_col = c
                break
        if year_col is not None:
            df = df.rename(columns={year_col: "year"})
        else:
            years = pd.to_datetime(df.index, errors="coerce").year
            df = df.assign(year=years).reset_index(drop=True)

    # value column
    value_col = None
    if "value" in df.columns:
        value_col = "value"
    elif indicator.lower() in df.columns:
        value_col = indicator.lower()
    else:
        numeric_candidates = [c for c in df.columns if c != "year" and pd.api.types.is_numeric_dtype(df[c])]
        if numeric_candidates:
            value_col = numeric_candidates[0]
    if value_col is None:
        raise ValueError(f"No numeric value column in {path}. Need 'value' or '{indicator}'.")

    out = df[["year", value_col]].dropna().rename(columns={value_col: "value"})
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"]).astype({"year": int}).sort_values("year").reset_index(drop=True)
    return out


@dataclass
class LLParams:
    drift: float
    sigma_obs: float
    sigma_state: float
    last_level: float


def _estimate_ll_params(y: np.ndarray) -> LLParams:
    """
    Ultra-simple moment-ish estimates:
      - drift = mean(diff(y))
      - sigma_state approximated by std of differenced level residuals
      - sigma_obs from residual std around local level (rough proxy)
    This is heuristic but adequate for generating broad scenario distributions.
    """
    if len(y) < 3:
        # fallback conservative
        return LLParams(drift=0.0, sigma_obs=float(np.std(y) if len(y) else 1.0),
                        sigma_state=float(np.std(y) if len(y) else 1.0),
                        last_level=float(y[-1]) if len(y) else 0.0)

    dy = np.diff(y)
    drift = float(np.nanmean(dy))
    # rough state noise as variability of dy around drift
    sigma_state = float(np.nanstd(dy - drift, ddof=1))
    if not np.isfinite(sigma_state) or sigma_state <= 1e-12:
        sigma_state = max(1e-6, float(np.nanstd(dy, ddof=1)))

    # observation noise as residuals around simple local-level with drift
    # reconstruct level recursively with drift
    level = [float(y[0])]
    for t in range(1, len(y)):
        level.append(level[-1] + drift)
    level = np.asarray(level)
    resid = y - level
    sigma_obs = float(np.nanstd(resid, ddof=1))
    if not np.isfinite(sigma_obs) or sigma_obs <= 1e-12:
        sigma_obs = max(1e-6, 0.1 * sigma_state)

    return LLParams(drift=drift, sigma_obs=sigma_obs, sigma_state=sigma_state, last_level=float(y[-1]))


def _simulate_paths(params: LLParams, h: int, n_paths: int, shocks: bool = False, lam: float = 0.0, shock_scale: float = 1.0) -> np.ndarray:
    """
    Simulate forward paths: shape (n_paths, h)
    If shocks=True, draw Poisson(k) shocks per step with Gaussian severities (mean 0, sd=shock_scale*sigma_state).
    """
    rng = np.random.default_rng(12345)
    level = np.full((n_paths,), params.last_level, dtype=float)
    paths = np.zeros((n_paths, h), dtype=float)

    for t in range(h):
        # state innovation
        eta = rng.normal(0.0, params.sigma_state, size=n_paths)
        level = level + params.drift + eta

        if shocks and lam > 0.0:
            k = rng.poisson(lam, size=n_paths)
            # sum of k shocks with Gaussian severities; variance adds
            shock = rng.normal(0.0, shock_scale * params.sigma_state, size=(n_paths,)) * k.astype(float)
            level = level + shock

        # observation
        eps = rng.normal(0.0, params.sigma_obs, size=n_paths)
        y_t = level + eps
        paths[:, t] = y_t

    return paths


def fsm_forecast(indicators: List[str], origin: int, h_scored: int = 15, h_scenario: int = 40, n_paths: int = 10000,
                 enable_shocks: bool = False, lam: float = 0.0, shock_scale: float = 1.0) -> Dict[str, pd.DataFrame]:
    """
    Returns:
      {
        "scored":   DataFrame[indicator, horizon, q5, q50, q95],
        "scenario": DataFrame[indicator, horizon, q5, q50, q95]
      }
    """
    rows_scored: List[Dict] = []
    rows_scen: List[Dict] = []

    for ind in indicators:
        df = _load_indicator_series(ind)
        df_tr = df[df["year"] <= origin]
        if len(df_tr) < MIN_HISTORY:
            # not enough history, skip quietly
            continue

        y = df_tr["value"].to_numpy(dtype=float)
        params = _estimate_ll_params(y)

        # scored horizons
        paths_s = _simulate_paths(params, h_scored, n_paths, shocks=enable_shocks, lam=lam, shock_scale=shock_scale)
        q50_s = np.median(paths_s, axis=0)
        q05_s = np.quantile(paths_s, 0.05, axis=0)
        q95_s = np.quantile(paths_s, 0.95, axis=0)
        for k in range(1, h_scored + 1):
            rows_scored.append(dict(indicator=ind, horizon=k, q5=float(q05_s[k - 1]), q50=float(q50_s[k - 1]), q95=float(q95_s[k - 1])))

        # scenario horizons
        paths_l = _simulate_paths(params, h_scenario, n_paths, shocks=enable_shocks, lam=lam, shock_scale=shock_scale)
        q50_l = np.median(paths_l, axis=0)
        q05_l = np.quantile(paths_l, 0.05, axis=0)
        q95_l = np.quantile(paths_l, 0.95, axis=0)
        for k in range(1, h_scenario + 1):
            rows_scen.append(dict(indicator=ind, horizon=k, q5=float(q05_l[k - 1]), q50=float(q50_l[k - 1]), q95=float(q95_l[k - 1])))

    out = {
        "scored": pd.DataFrame(rows_scored, columns=["indicator", "horizon", "q5", "q50", "q95"]),
        "scenario": pd.DataFrame(rows_scen, columns=["indicator", "horizon", "q5", "q50", "q95"]),
    }
    return out
