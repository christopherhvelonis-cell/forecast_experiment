#!/usr/bin/env python3
"""
Tools/discover_make_perf.py

Scan eval/results for any CSV that can be turned into a long per-model
metrics file with columns:
  indicator,horizon,origin_year,model,metric,loss

It handles both:
- Already-long files (have 'metric' + 'loss')
- Wide files with columns like 'composite','crps','brier' (it melts them)

Heuristics:
- Model column may be named 'model' or inferred from a column like 'source',
  'builder', or from the filename prefix (e.g., 'hsm_*' -> model='hsm').
- Required keys: indicator, horizon, origin_year.

Outputs:
  eval/results/perf_by_model.csv
"""

import os, sys, glob, re
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RES  = os.path.abspath(os.path.join(ROOT, "..", "eval", "results"))

LOSS_NAMES = {"composite","crps","brier",
              "loss_composite","loss_crps","loss_brier"}

KEYS = ["indicator","horizon","origin_year"]
MODEL_CANDIDATES = ["model","source","builder","base_model","algo"]

def find_csvs():
    return [p for p in glob.glob(os.path.join(RES, "*.csv"))]

def normalize_cols(df):
    # trim whitespace; lower a map but keep original names
    cols = {c.lower().strip(): c for c in df.columns}
    return cols

def infer_model_column(df, path):
    cols = normalize_cols(df)
    for c in MODEL_CANDIDATES:
        if c in cols: return cols[c]
    # Infer from filename prefix if looks like 'hsm_xxx.csv' or 'fsm_xxx.csv'
    fn = os.path.basename(path).lower()
    m = re.match(r"(hsm|fsm|grok_hsm|grok_fsm)[_\-].*", fn)
    if m:
        model_name = m.group(1)
        return model_name  # signal: constant model name for this file
    return None

def usable(df):
    cols = set(c.lower().strip() for c in df.columns)
    return set(KEYS).issubset(cols)

def try_make_long_from(path):
    try:
        df = pd.read_csv(path)
    except Exception:
        return None

    if not usable(df):
        return None

    cols = normalize_cols(df)
    # Identify (indicator,horizon,origin_year)
    base = df[[cols["indicator"], cols["horizon"], cols["origin_year"]]].copy()
    base.columns = ["indicator","horizon","origin_year"]

    # Determine model
    model_col = infer_model_column(df, path)
    if model_col is None:
        # Fail if we cannot infer a model
        return None

    if model_col in df.columns:
        base["model"] = df[model_col].astype(str)
        wide_source = df
    else:
        # Fixed model derived from filename
        base["model"] = model_col
        wide_source = df

    # Case A: Already long
    if ("metric" in normalize_cols(wide_source)) and ("loss" in normalize_cols(wide_source)):
        cols2 = normalize_cols(wide_source)
        long_df = wide_source[[cols["indicator"],cols["horizon"],cols["origin_year"],
                               cols2["metric"], cols2["loss"]]].copy()
        long_df.columns = ["indicator","horizon","origin_year","metric","loss"]
        # attach model (from column or fixed)
        if model_col in wide_source.columns:
            long_df["model"] = wide_source[model_col].astype(str).values
        else:
            long_df["model"] = model_col
        return long_df

    # Case B: Wide -> melt known loss columns
    loss_cols = [c for c in wide_source.columns if c.lower().strip() in LOSS_NAMES]
    if not loss_cols:
        return None

    id_vars = [cols["indicator"], cols["horizon"], cols["origin_year"]]
    if model_col in wide_source.columns:
        id_vars.append(model_col)

    melted = wide_source.melt(
        id_vars=id_vars,
        value_vars=loss_cols,
        var_name="metric",
        value_name="loss"
    ).copy()

    # Normalize
    melted.rename(columns={
        cols["indicator"]:"indicator",
        cols["horizon"]:"horizon",
        cols["origin_year"]:"origin_year"
    }, inplace=True)

    if model_col in wide_source.columns:
        melted.rename(columns={model_col:"model"}, inplace=True)
    else:
        melted["model"] = model_col

    # clean metric names (strip 'loss_' prefix)
    melted["metric"] = melted["metric"].str.lower().str.replace("^loss_", "", regex=True)
    melted["horizon"] = melted["horizon"].astype(int)
    melted["origin_year"] = melted["origin_year"].astype(int)
    melted["loss"] = pd.to_numeric(melted["loss"], errors="coerce")

    long_df = melted[["indicator","horizon","origin_year","model","metric","loss"]].dropna(subset=["loss"])
    return long_df if not long_df.empty else None

def main():
    csvs = find_csvs()
    candidates = []
    for p in csvs:
        out = try_make_long_from(p)
        if out is not None and not out.empty:
            candidates.append((p, out))

    if not candidates:
        sys.exit("[error] No suitable CSVs found to synthesize perf_by_model.csv. "
                 "Ensure you have a per-model metrics file with keys "
                 "(indicator,horizon,origin_year, [model or inferable]).")

    # Pick the largest (most rows)
    best_path, best = max(candidates, key=lambda t: len(t[1]))
    best["metric"] = best["metric"].str.lower()
    best["loss"] = best["loss"].astype(float)

    dst = os.path.join(RES, "perf_by_model.csv")
    best.to_csv(dst, index=False)
    print(f"[ok] Wrote {dst}  rows={len(best)}  (source={os.path.basename(best_path)})")

if __name__ == "__main__":
    main()
