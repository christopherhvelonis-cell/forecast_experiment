# models/HSM_chatgpt/hsm.py

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.structural import UnobservedComponents

# ↓↓↓ Lower this so we don't skip everything
MIN_HISTORY = 5
DATA_DIR = Path("data/processed")

def _load_indicator_series(indicator: str) -> pd.DataFrame:
    path = DATA_DIR / f"{indicator}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Processed file not found for indicator '{indicator}': {path}")

    df = pd.read_csv(path)

    # normalize column names
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols

    if "year" not in df.columns:
        for c in df.columns:
            if c.startswith("year"):
                df.rename(columns={c: "year"}, inplace=True)
                break
        if "year" not in df.columns:
            years = pd.to_datetime(df.index, errors="coerce").year
            df = df.assign(year=years).reset_index(drop=True)

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
        raise ValueError(
            f"Could not find a numeric value column in {path}. "
            f"Expected 'value' or '{indicator}', or a single numeric column."
        )

    out = df[["year", value_col]].dropna()
    out.rename(columns={value_col: "value"}, inplace=True)
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"]).astype({"year": int})
    out = out.sort_values("year").reset_index(drop=True)
    return out

def _fit_ucm_and_forecast(y: pd.Series, h: int) -> Dict[str, np.ndarray]:
    y = pd.to_numeric(y, errors="coerce").astype(float)
    y = y.dropna()
    mod = UnobservedComponents(endog=y, level="local level", trend=True)
    res = mod.fit(disp=False)

    fcast = res.get_forecast(steps=h)
    mu = np.asarray(fcast.predicted_mean, dtype=float)
    var_mean = np.asarray(fcast.var_pred_mean, dtype=float)

    sigma2_irreg = 0.0
    for k, v in res.params.items():
        if "sigma2.irregular" in k:
            sigma2_irreg = float(v)
            break

    var = np.clip(var_mean + sigma2_irreg, 1e-12, None)
    sigma = np.sqrt(var)

    z05 = 1.6448536269514722  # Phi^{-1}(0.95)
    q50 = mu
    q95 = mu + z05 * sigma
    q05 = mu - z05 * sigma

    return dict(mu=mu, sigma=sigma, q05=q05, q50=q50, q95=q95)

def hsm_forecast(indicators: List[str], origin: int, h: int = 15) -> pd.DataFrame:
    rows = []
    for ind in indicators:
        df = _load_indicator_series(ind)
        df_train = df[df["year"] <= origin].copy()
        if len(df_train) < MIN_HISTORY:
            print(f"[HSM] skip {ind}: insufficient history up to {origin} (have={len(df_train)}, need>={MIN_HISTORY})")
            continue

        y = df_train.set_index("year")["value"]
        fc = _fit_ucm_and_forecast(y, h=h)
        for k in range(1, h + 1):
            rows.append(
                dict(
                    indicator=ind,
                    horizon=k,
                    q05=float(fc["q05"][k - 1]),
                    q50=float(fc["q50"][k - 1]),
                    q95=float(fc["q95"][k - 1]),
                )
            )

        print(f"[HSM] ok {ind}: wrote {h} horizons (last train year <= {origin})")

    # NOTE: keep q05 here to match your existing files
    out = pd.DataFrame(rows, columns=["indicator", "horizon", "q05", "q50", "q95"])
    if out.empty:
        print("[HSM] WARNING: produced no rows (all indicators skipped).")
    return out
