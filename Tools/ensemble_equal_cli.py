#!/usr/bin/env python
import argparse, os, pandas as pd

# Canonical columns we will produce if available
CANON = ["q05","q50","q95","q25","q75","lo_50","hi_50","lo_90","hi_90"]
KEYS = ["indicator","horizon"]

def load_paths(list_file):
    with open(list_file, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def normalize(df):
    # keep keys + any known quantile/band columns
    keep = [c for c in df.columns if c in KEYS or c.lower() in ["q5","q05","q50","q95","q25","q75","lo_50","hi_50","lo_90","hi_90"]]
    df = df[keep].copy()

    # map aliases to canonical names
    colmap = {}
    # allow 'q5' to be treated as 'q05'
    if "q5" in df.columns and "q05" not in df.columns:
        colmap["q5"] = "q05"
    # accept case variants
    for c in list(df.columns):
        lc = c.lower()
        if lc == "q5" and "q05" not in colmap: colmap[c] = "q05"
        if lc == "q50" and "q50" not in colmap: colmap[c] = "q50"
        if lc == "q95" and "q95" not in colmap: colmap[c] = "q95"
        if lc == "q25" and "q25" not in colmap: colmap[c] = "q25"
        if lc == "q75" and "q75" not in colmap: colmap[c] = "q75"
        if lc == "lo_50" and "lo_50" not in colmap: colmap[c] = "lo_50"
        if lc == "hi_50" and "hi_50" not in colmap: colmap[c] = "hi_50"
        if lc == "lo_90" and "lo_90" not in colmap: colmap[c] = "lo_90"
        if lc == "hi_90" and "hi_90" not in colmap: colmap[c] = "hi_90"

    df = df.rename(columns=colmap)

    # sanity
    for k in KEYS:
        if k not in df.columns:
            raise ValueError(f"Input missing required key column '{k}'. Columns={df.columns.tolist()}")
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list_file", required=True, help="Text file: one calibrated FINAL CSV per line")
    ap.add_argument("--out_csv", required=True, help="Output ensemble CSV")
    args = ap.parse_args()

    paths = load_paths(args.list_file)
    if not paths:
        raise ValueError("No model paths found in --list_file")

    dfs = []
    for i, p in enumerate(paths):
        if not os.path.exists(p):
            raise FileNotFoundError(f"Not found: {p}")
        d = pd.read_csv(p)
        d = normalize(d)
        d["__model__"] = i
        dfs.append(d)

    big = pd.concat(dfs, ignore_index=True)

    # numeric-mean aggregation across models for all available canonical columns
    num_cols = [c for c in CANON if c in big.columns]
    if not num_cols:
        # If only q50 exists, still allow pass-through mean on q50
        if "q50" in big.columns:
            num_cols = ["q50"]
        else:
            raise ValueError(f"No recognized quantile/band columns found to average. Columns={big.columns.tolist()}")

    agg_dict = {c: "mean" for c in num_cols}
    ens = (big.groupby(KEYS, as_index=False)[num_cols].mean())

    # keep keys + aggregated columns
    ens = ens[KEYS + num_cols].sort_values(KEYS).reset_index(drop=True)

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    ens.to_csv(args.out_csv, index=False)
    print(f"[ensemble_equal] wrote {args.out_csv} rows={len(ens)} from n_inputs={len(paths)} with cols={num_cols}")

if __name__ == "__main__":
    main()
