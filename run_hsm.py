# run_hsm.py
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import pandas as pd

# import your HSM forecast function
from models.HSM_chatgpt.hsm import hsm_forecast

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--indicators", nargs="+", required=True, help="List of indicator names")
    p.add_argument("--origin", type=int, required=True, help="Last year included in training")
    p.add_argument("--h", type=int, default=15, help="Forecast horizon (years)")
    p.add_argument("--out", type=str, required=True, help="Output CSV path")
    return p.parse_args()

def main():
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = hsm_forecast(args.indicators, origin=args.origin, h=args.h)

    # Accept either q05 or q5; standardize to q05 in the file
    if "q5" in df.columns and "q05" not in df.columns:
        df = df.rename(columns={"q5": "q05"})

    # sanity columns (don’t drop rows if a column is missing)
    expected = ["indicator", "horizon", "q05", "q50", "q95"]
    present = [c for c in expected if c in df.columns]
    df = df[present]

    # refuse to write header-only files
    if df.empty:
        print("[run_hsm] ERROR: forecast dataframe is empty — not writing file.")
        sys.exit(1)

    # small debug print
    print("[run_hsm] head:")
    print(df.head(10).to_string(index=False))

    df.to_csv(out_path, index=False)
    print(f"[run_hsm] wrote {len(df)} rows to {out_path}")

if __name__ == "__main__":
    main()
