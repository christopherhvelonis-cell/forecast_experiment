#!/usr/bin/env python3
import argparse, os
import pandas as pd

def main(in_csv, out_csv, indicator, lo90, hi90, lo50=None, hi50=None,
         indicator_col="indicator", horizon_col="horizon"):
    if not os.path.exists(in_csv):
        raise SystemExit(f"[error] missing {in_csv}")
    df = pd.read_csv(in_csv)

    # 1) Ensure indicator column exists and equals the target indicator
    if indicator_col not in df.columns:
        df[indicator_col] = indicator
    else:
        df[indicator_col] = indicator

    # 2) Ensure horizon column exists (fall back to 1..N if absent)
    if horizon_col not in df.columns:
        df[horizon_col] = range(1, len(df) + 1)

    # 3) Map band columns to canonical names expected by nonus_check_cli.py
    rename_map = {}
    if lo90 and lo90 in df.columns: rename_map[lo90] = "lo90"
    if hi90 and hi90 in df.columns: rename_map[hi90] = "hi90"
    if lo50 and lo50 in df.columns: rename_map[lo50] = "lo50"
    if hi50 and hi50 in df.columns: rename_map[hi50] = "hi50"
    if rename_map:
        df = df.rename(columns=rename_map)

    # 4) Minimal schema check
    need_any_90 = {"lo90","hi90"}.issubset(df.columns)
    need_any_50 = {"lo50","hi50"}.issubset(df.columns)
    if not (need_any_90 or need_any_50):
        raise SystemExit("[error] need either lo90/hi90 or lo50/hi50 columns after rename")

    keep_cols = [indicator_col, horizon_col] + [c for c in ["lo50","hi50","lo90","hi90"] if c in df.columns]
    out = df[keep_cols].copy()

    # 5) Coerce types
    out[horizon_col] = out[horizon_col].astype(int)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"[ok] normalized -> {out_csv}  rows={len(out)}  cols={list(out.columns)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--indicator", required=True, help="US indicator name to validate against (e.g., trust_media_pct)")
    ap.add_argument("--lo90", default=None, help="Name of source column for 90% lower band (e.g., __lo_90__)")
    ap.add_argument("--hi90", default=None, help="Name of source column for 90% upper band (e.g., __hi_90__)")
    ap.add_argument("--lo50", default=None, help="Name of source column for 50% lower band (optional)")
    ap.add_argument("--hi50", default=None, help="Name of source column for 50% upper band (optional)")
    ap.add_argument("--indicator_col", default="indicator")
    ap.add_argument("--horizon_col", default="horizon")
    args = ap.parse_args()
    main(**vars(args))
