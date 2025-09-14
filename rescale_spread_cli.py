# rescale_spread_cli.py
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

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
    ap = argparse.ArgumentParser(description="Multiply (q5,q95) spreads around q50 by alpha.")
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--indicator", required=True)
    ap.add_argument("--alpha", type=float, required=True)
    args = ap.parse_args()

    df = norm_cols(pd.read_csv(args.in_csv))
    mask = df["indicator"] == args.indicator
    sub = df.loc[mask].copy()
    if sub.empty:
        raise SystemExit(f"No rows for indicator {args.indicator!r} in {args.in_csv}")

    a = args.alpha
    # rescale around q50
    sub["q5"]  = sub["q50"] + (sub["q5"]  - sub["q50"]) * a
    sub["q95"] = sub["q50"] + (sub["q95"] - sub["q50"]) * a

    out = pd.concat([df.loc[~mask], sub], ignore_index=True)
    out.to_csv(args.out_csv, index=False)
    print(f"[rescale] indicator={args.indicator} alpha={a:.3f}")
    print(f"[rescale] wrote: {args.out_csv}")

if __name__ == "__main__":
    main()
