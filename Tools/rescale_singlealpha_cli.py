#!/usr/bin/env python
import argparse, os, re
import pandas as pd

ALIASES = {
    "q50": ["q50","p50","quantile_50","median","Q50"],
    "q05": ["q05","q5","p05","p5","quantile_5","quantile_05","Q05","Q5"],
    "q95": ["q95","p95","quantile_95","Q95"],
    "q25": ["q25","p25","quantile_25","Q25"],
    "q75": ["q75","p75","quantile_75","Q75"],
    # Some exports already have band edges:
    "lo50": ["lo_50","l50","lo50","lower50"],
    "hi50": ["hi_50","u50","hi50","upper50"],
    "lo90": ["lo_90","l90","lo90","lower90"],
    "hi90": ["hi_90","u90","hi90","upper90"],
}

def pick(colnames, keys):
    for k in keys:
        if k in colnames: return k
    return None

def find_first(colnames, alias_key):
    ali = [a for a in ALIASES[alias_key] if a in colnames]
    return ali[0] if ali else None

def ensure_bands(df, colnames):
    # Find q50
    q50 = find_first(colnames, "q50")
    if not q50:
        raise ValueError("Could not find a 50th percentile column among: " + str(ALIASES["q50"]))

    # Try to find existing band edges
    lo50 = find_first(colnames, "lo50")
    hi50 = find_first(colnames, "hi50")
    lo90 = find_first(colnames, "lo90")
    hi90 = find_first(colnames, "hi90")

    # If missing, try to synthesize from quantiles
    q25 = find_first(colnames, "q25")
    q75 = find_first(colnames, "q75")
    q05 = find_first(colnames, "q05")
    q95 = find_first(colnames, "q95")

    # 50% band
    if lo50 is None or hi50 is None:
        if q25 and q75:
            df["lo_50"] = df[q25]
            df["hi_50"] = df[q75]
            lo50, hi50 = "lo_50","hi_50"
        else:
            raise ValueError("No (lo_50,hi_50) and cannot synthesize: missing q25/q75.")

    # 90% band
    if lo90 is None or hi90 is None:
        if q05 and q95:
            df["lo_90"] = df[q05]
            df["hi_90"] = df[q95]
            lo90, hi90 = "lo_90","hi_90"
        else:
            raise ValueError("No (lo_90,hi_90) and cannot synthesize: missing q05/q95.")

    # Return canonical names actually present in df
    colnames = set(df.columns)
    return q50, lo50, hi50, lo90, hi90

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--indicator", required=False, help="If set, restrict to rows with this indicator")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    df = pd.read_csv(args.in_csv)

    mask = pd.Series(True, index=df.index)
    if args.indicator and "indicator" in df.columns:
        mask = (df["indicator"] == args.indicator)

    q50, lo50, hi50, lo90, hi90 = ensure_bands(df, set(df.columns))

    def shrink_around_median(row, lo, hi, a):
        m = row[q50]
        row[lo] = m + a * (row[lo] - m)
        row[hi] = m + a * (row[hi] - m)
        return row

    # Appl
