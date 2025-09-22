#!/usr/bin/env python3
"""
Tools/make_realized_template_from_struct.py

Create/refresh eval/results/realized_by_origin.csv from existing *_struct_*.csv files.
- Collects all (indicator, horizon) pairs per origin_year (parsed from filename).
- Writes a template with empty 'value' for you to fill.
- If a realized_by_origin.csv already exists, preserves existing values and
  only appends any missing (indicator,origin_year,horizon) rows.

Expected struct files: eval/results/*_struct_YYYY.csv
Each must contain: indicator,horizon and (optionally) q05,q50,q95.

Output: eval/results/realized_by_origin.csv with columns:
  indicator,origin_year,horizon,value
"""

import os, re, glob, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
OUT  = os.path.join(RES, "realized_by_origin.csv")

def parse_oy(path):
    m = re.search(r"_struct_(\d{4})\.csv$", os.path.basename(path))
    return int(m.group(1)) if m else None

def main():
    struct_files = sorted(glob.glob(os.path.join(RES, "*_struct_*.csv")))
    if not struct_files:
        sys.exit("[error] No *_struct_*.csv files found under eval/results")

    rows = []
    for f in struct_files:
        oy = parse_oy(f)
        if oy is None:
            continue
        try:
            df = pd.read_csv(f, usecols=["indicator","horizon"])
        except Exception:
            # Try to read minimally and check columns
            df = pd.read_csv(f)
            if not {"indicator","horizon"}.issubset(df.columns):
                continue
            df = df[["indicator","horizon"]]

        df = df.dropna(subset=["indicator","horizon"])
        df["horizon"] = df["horizon"].astype(int)
        df["origin_year"] = oy
        rows.append(df[["indicator","origin_year","horizon"]])

    if not rows:
        sys.exit("[error] Could not assemble any (indicator,horizon,origin_year) from struct files")

    wanted = pd.concat(rows, ignore_index=True).drop_duplicates().sort_values(
        ["indicator","origin_year","horizon"]
    )

    if os.path.exists(OUT):
        existing = pd.read_csv(OUT)
        need_cols = {"indicator","origin_year","horizon","value"}
        if not need_cols.issubset(existing.columns):
            # If the existing file is malformed, back it up and recreate.
            backup = OUT + ".bak"
            existing.to_csv(backup, index=False)
            print(f"[warn] Existing realized file missing columns {need_cols}. Backed up -> {backup}")
            existing = pd.DataFrame(columns=["indicator","origin_year","horizon","value"])
        else:
            existing["origin_year"] = existing["origin_year"].astype(int)
            existing["horizon"] = existing["horizon"].astype(int)

        # Left-join wanted with existing values
        merged = wanted.merge(
            existing[["indicator","origin_year","horizon","value"]],
            on=["indicator","origin_year","horizon"],
            how="left",
        )
        out = merged[["indicator","origin_year","horizon","value"]]
    else:
        out = wanted.copy()
        out["value"] = ""

    os.makedirs(RES, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[ok] Wrote {os.path.relpath(OUT, ROOT)}  rows={len(out)}")
    print("Fill in the 'value' column with realized outcomes, then proceed.")

if __name__ == "__main__":
    main()
