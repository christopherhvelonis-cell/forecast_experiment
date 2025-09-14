# alpha_solver_cli.py
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    ren = {}
    if 'h' in df.columns and 'horizon' not in df.columns: ren['h'] = 'horizon'
    if 'q05' in df.columns and 'q5' not in df.columns: ren['q05'] = 'q5'
    if 'p5'  in df.columns and 'q5' not in df.columns: ren['p5']  = 'q5'
    if 'p95' in df.columns and 'q95' not in df.columns: ren['p95'] = 'q95'
    if 'q0.5' in df.columns and 'q50' not in df.columns: ren['q0.5'] = 'q50'
    if 'median' in df.columns and 'q50' not in df.columns: ren['median'] = 'q50'
    if 'variable' in df.columns and 'indicator' not in df.columns: ren['variable'] = 'indicator'
    if 'series' in df.columns and 'indicator' not in df.columns: ren['series'] = 'indicator'
    if ren: df = df.rename(columns=ren)
    return df

def main():
    ap = argparse.ArgumentParser(description="Compute minimal alpha to achieve 90% coverage given q50/q95 and truth.")
    ap.add_argument("--calibrated_csv", required=True)
    ap.add_argument("--truth_csv", required=True)
    ap.add_argument("--indicator", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--h", type=int, required=True)
    args = ap.parse_args()

    qdf = norm_cols(pd.read_csv(args.calibrated_csv))
    qsub = qdf[qdf["indicator"] == args.indicator].copy()
    if qsub.empty:
        raise SystemExit(f"No rows for indicator {args.indicator!r} in calibrated_csv")

    tdf = pd.read_csv(args.truth_csv)
    tdf.columns = [c.strip().lower() for c in tdf.columns]
    if "year" not in tdf.columns:
        tdf["year"] = pd.to_datetime(tdf["date"], errors="coerce").dt.year
    tdf = tdf.dropna(subset=["year","value"]).astype({"year": int})

    rows = []
    for k in range(1, args.h+1):
        y = args.origin + k
        r = qsub[qsub["horizon"]==k]
        t = tdf[tdf["year"]==y]
        if r.empty or t.empty:
            continue
        q50 = float(r["q50"].values[0])
        q95 = float(r["q95"].values[0])
        truth = float(t["value"].values[0])
        spread = abs(q95 - q50)  # verifier uses this for 90% band
        miss_margin = abs(truth - q50) - spread
        rows.append(dict(year=y, q50=q50, q95=q95, truth=truth, spread=spread, miss_margin=miss_margin))

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No overlap between forecast horizons and truth years.")

    # Current coverage at 90% level using your verifier’s logic: |y - q50| <= (q95 - q50)
    covered_now = (abs(df["truth"] - df["q50"]) <= df["spread"]).sum()
    total = len(df)
    # Minimal alpha to cover each miss: need alpha * spread >= |y - q50|  => alpha >= |y - q50|/spread
    misses = df[abs(df["truth"] - df["q50"]) > df["spread"]].copy()
    if misses.empty:
        print(f"[alpha] already at or above 90%: {covered_now}/{total}")
        print("[alpha] alpha_min = 1.0")
        return

    # guard against zero spreads
    eps = 1e-12
    misses["alpha_needed"] = abs(misses["truth"] - misses["q50"]) / (misses["spread"] + eps)
    alpha_min = float(misses["alpha_needed"].max()) * 1.01  # 1% safety margin
    print(f"[alpha] current coverage: {covered_now}/{total} = {covered_now/total:.3f}")
    print(f"[alpha] minimal alpha to cover all misses: {alpha_min:.3f}")
    print("[alpha] details of misses:")
    print(misses[["year","q50","q95","truth","spread","alpha_needed"]].to_string(index=False))

if __name__ == "__main__":
    main()
