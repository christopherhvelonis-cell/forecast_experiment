# calibrate_sigma_cli.py
"""
Coverage calibration via sigma scaling on quantile CSVs.

- INPUT:  quantile CSV with columns [indicator, horizon, q5|q05, q50, q95]
          (produced by run_hsm.py / run_fsm.py / grok runners)
- TRUTH:  loaded from data/processed/<indicator>.csv with columns [year, value]
- ORIGINS: one or more origin years to use for measuring empirical coverage
          (we compare forecasts for horizon k to actual value at year=origin+k when available)
- METHOD: For each indicator, find a multiplicative alpha on tails so that
          P(y_true in [q5', q95']) ≈ target_cov, where:
              q5'  = q50 + alpha * (q5 - q50)
              q95' = q50 + alpha * (q95 - q50)

- OUTPUT:
    --out <path>.csv               calibrated quantiles for the input file
    (and a companion) <path>_scales.csv with per-indicator alpha and coverage stats

This script does NOT refit models; it ONLY reads the provided quantiles and rescales spreads.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

DATA_DIR = Path("data/processed")
MIN_HISTORY = 8


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make columns lowercase and normalize quantile names so downstream
    code can rely on: indicator, horizon, q5, q50, q95
    Accepts q05 -> q5 and common variants.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # rename common variants
    renames = {}
    cols = set(df.columns)

    # indicator / horizon
    if "indicator" not in cols:
        # sometimes "series" or "variable"
        if "series" in cols:
            renames["series"] = "indicator"
        elif "variable" in cols:
            renames["variable"] = "indicator"

    if "horizon" not in cols:
        if "h" in cols:
            renames["h"] = "horizon"
        elif "step" in cols:
            renames["step"] = "horizon"

    # median
    if "q50" not in cols:
        if "q0.5" in cols:
            renames["q0.5"] = "q50"
        elif "median" in cols:
            renames["median"] = "q50"
        elif "p50" in cols:
            renames["p50"] = "q50"

    # lower tail: q5 OR q05
    if "q5" not in cols:
        if "q05" in cols:
            renames["q05"] = "q5"
        elif "p5" in cols:
            renames["p5"] = "q5"
        elif "q0.05" in cols:
            renames["q0.05"] = "q5"

    # upper tail: q95
    if "q95" not in cols:
        if "p95" in cols:
            renames["p95"] = "q95"
        elif "q0.95" in cols:
            renames["q0.95"] = "q95"

    if renames:
        df = df.rename(columns=renames)

    expected = {"indicator", "horizon", "q5", "q50", "q95"}
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(
            f"Input file must contain columns {sorted(expected)}; missing {missing}. "
            f"Got columns: {df.columns.tolist()}"
        )

    # cast numeric
    df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce").astype(int)
    for c in ["q5", "q50", "q95"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _load_truth_series(indicator: str) -> pd.DataFrame:
    path = DATA_DIR / f"{indicator}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Truth series not found for '{indicator}': {path}")
    df = pd.read_csv(path)
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols
    if "year" not in df.columns:
        for c in df.columns:
            if c.startswith("year"):
                df = df.rename(columns={c: "year"})
                break
    if "year" not in df.columns:
        years = pd.to_datetime(df.index, errors="coerce").year
        df = df.assign(year=years).reset_index(drop=True)

    # choose value column
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

    out = df[["year", value_col]].dropna()
    out = out.rename(columns={value_col: "value"})
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"]).astype({"year": int})
    out = out.sort_values("year").reset_index(drop=True)
    return out


def _coverage_for_alpha(qdf_ind: pd.DataFrame, truth: pd.DataFrame, origin: int, h: int, alpha: float) -> tuple[int, int]:
    covered = 0
    total = 0
    for k in range(1, h + 1):
        y_year = origin + k
        row = qdf_ind.loc[qdf_ind["horizon"] == k]
        if row.empty:
            continue
        trow = truth.loc[truth["year"] == y_year]
        if trow.empty:
            continue
        y_true = float(trow["value"].values[0])
        q50 = float(row["q50"].values[0])
        q5 = float(row["q5"].values[0])
        q95 = float(row["q95"].values[0])
        lo = q50 + alpha * (q5 - q50)
        hi = q50 + alpha * (q95 - q50)
        if min(lo, hi) <= y_true <= max(lo, hi):
            covered += 1
        total += 1
    return covered, total


def _binary_search_alpha(qdf_ind: pd.DataFrame, truth: pd.DataFrame, origins: List[int], h: int, target_cov: float) -> tuple[float, float, float]:
    # baseline coverage (alpha = 1)
    cov_num = 0
    cov_den = 0
    for O in origins:
        n, d = _coverage_for_alpha(qdf_ind, truth, O, h, alpha=1.0)
        cov_num += n
        cov_den += d
    cov_before = (cov_num / cov_den) if cov_den > 0 else np.nan

    if cov_den == 0:
        return 1.0, np.nan, np.nan
    if not np.isnan(cov_before) and abs(cov_before - target_cov) <= 0.005:
        return 1.0, cov_before, cov_before

    lo, hi = 0.25, 8.0
    best_alpha = 1.0
    best_err = 1e9

    for _ in range(30):
        mid = (lo + hi) / 2.0
        cnum = 0
        cden = 0
        for O in origins:
            n, d = _coverage_for_alpha(qdf_ind, truth, O, h, alpha=mid)
            cnum += n
            cden += d
        cov_mid = (cnum / cden) if cden > 0 else 0.0
        err = abs(cov_mid - target_cov)
        if err < best_err:
            best_err = err
            best_alpha = mid
        if cov_mid < target_cov:
            lo = mid  # widen
        else:
            hi = mid  # narrow

    # coverage after
    cnum = 0
    cden = 0
    for O in origins:
        n, d = _coverage_for_alpha(qdf_ind, truth, O, h, alpha=best_alpha)
        cnum += n
        cden += d
    cov_after = (cnum / cden) if cden > 0 else np.nan
    return float(best_alpha), float(cov_before), float(cov_after)


def main():
    ap = argparse.ArgumentParser(description="Sigma scaling calibration for quantile CSVs.")
    ap.add_argument("--in", dest="in_path", required=True, help="Input quantiles CSV (indicator,horizon,q5|q05,q50,q95)")
    ap.add_argument("--out", dest="out_path", required=True, help="Output calibrated quantiles CSV")
    ap.add_argument("--origins", nargs="+", type=int, required=True, help="Origin years to use for coverage measurement")
    ap.add_argument("--indicators", nargs="+", required=True, help="List of indicators included in the CSV")
    ap.add_argument("--h", type=int, default=15, help="Max scored horizon")
    ap.add_argument("--target_cov", type=float, default=0.90, help="Target middle coverage (e.g., 0.90)")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --- load and normalize quantile file ---
    qdf_raw = pd.read_csv(in_path)
    qdf = _normalize_columns(qdf_raw)

    # --- per-indicator alpha search ---
    alphas: Dict[str, float] = {}
    scales_rows = []

    for ind in args.indicators:
        qdf_ind = qdf.loc[qdf["indicator"] == ind, ["indicator", "horizon", "q5", "q50", "q95"]].copy()
        if qdf_ind.empty:
            # not present in this file → leave as-is
            alphas[ind] = 1.0
            scales_rows.append(dict(indicator=ind, alpha=1.0, coverage_before=np.nan, coverage_after=np.nan))
            continue

        # load truth
        try:
            truth = _load_truth_series(ind)
        except Exception:
            alphas[ind] = 1.0
            scales_rows.append(dict(indicator=ind, alpha=1.0, coverage_before=np.nan, coverage_after=np.nan))
            continue

        # require some pre-origin history in at least one origin
        usable = False
        for O in args.origins:
            if (truth["year"] <= O).sum() >= MIN_HISTORY:
                usable = True
                break
        if not usable:
            alphas[ind] = 1.0
            scales_rows.append(dict(indicator=ind, alpha=1.0, coverage_before=np.nan, coverage_after=np.nan))
            continue

        alpha, cov_before, cov_after = _binary_search_alpha(
            qdf_ind=qdf_ind, truth=truth, origins=args.origins, h=args.h, target_cov=args.target_cov
        )
        alphas[ind] = alpha
        scales_rows.append(
            dict(
                indicator=ind,
                alpha=float(alpha),
                coverage_before=(float(cov_before) if not np.isnan(cov_before) else np.nan),
                coverage_after=(float(cov_after) if not np.isnan(cov_after) else np.nan),
            )
        )

    # --- apply scaling to all rows present ---
    def _apply_alpha(row):
        a = alphas.get(row["indicator"], 1.0)
        q50, q5, q95 = float(row["q50"]), float(row["q5"]), float(row["q95"])
        row["q5"] = q50 + a * (q5 - q50)
        row["q95"] = q50 + a * (q95 - q50)
        return row

    calibrated = qdf.copy().apply(_apply_alpha, axis=1)

    # --- write outputs ---
    calibrated.to_csv(out_path, index=False)
    scales_path = out_path.with_name(out_path.stem + "_scales.csv")
    pd.DataFrame(scales_rows, columns=["indicator", "alpha", "coverage_before", "coverage_after"]).to_csv(scales_path, index=False)

    print(f"[calibrate_sigma] wrote:\n  - {out_path}\n  - {scales_path}")


if __name__ == "__main__":
    main()
