# Tools/fsm_paths_to_diag.py
import argparse
from pathlib import Path
import re
import numpy as np
import pandas as pd

META_COLS = {"indicator","horizon","year","date","time","t","draw","trial","seed",
             "quantile","q","q05","q50","q95","truth","lower","upper","lo","hi",
             "p05","p50","p95","model","method","scenario","run_id","id","uid"}

PREF_VALUE = ["value","yhat","y_pred","pred","prediction","path","path_value",
              "sample","draw_value","sim","sim_value","forecast","y"]

DRAW_WIDE_RE = re.compile(r"^(draw|path|sim|yhat|y|pred)(_|\d)", re.I)

def coerce_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c.lower() in ("indicator","horizon"):
            continue
        out[c] = pd.to_numeric(out[c], errors="ignore")
    return out

def melt_if_wide(df: pd.DataFrame) -> pd.DataFrame | None:
    """Detect wide format (many numeric draw columns) and melt -> long with column 'value'."""
    non_meta = [c for c in df.columns if c.lower() not in META_COLS and c.lower() not in ("indicator","horizon")]
    numeric_candidates = [c for c in non_meta if pd.api.types.is_numeric_dtype(df[c])]
    # Heuristic: wide if >=3 numeric non-meta cols OR names look like draw/sim/path*
    looks_like_wide = (
        len(numeric_candidates) >= 3
        or any(DRAW_WIDE_RE.search(c) for c in non_meta)
    )
    if looks_like_wide and numeric_candidates:
        long = df.melt(id_vars=[c for c in df.columns if c.lower() in ("indicator","horizon")],
                       value_vars=numeric_candidates,
                       var_name="draw_col", value_name="value")
        return long.dropna(subset=["value"])
    return None

def pick_value_col_long(df: pd.DataFrame) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for k in PREF_VALUE:
        if k in cols_lower and pd.api.types.is_numeric_dtype(df[cols_lower[k]]):
            return cols_lower[k]
    # fallback: first numeric non-meta column
    for c in df.columns:
        if c.lower() in META_COLS or c.lower() in ("indicator","horizon"):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths_csv", required=True)
    ap.add_argument("--truths_csv", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    paths_raw = pd.read_csv(args.paths_csv)
    truths = pd.read_csv(args.truths_csv)

    # required keys
    for col in ["indicator","horizon"]:
        if col not in paths_raw.columns:
            raise SystemExit(f"paths CSV must contain column '{col}'")
    for col in ["indicator","horizon","truth"]:
        if col not in truths.columns:
            raise SystemExit(f"truths CSV must contain column '{col}'")

    paths = coerce_numeric_cols(paths_raw)

    # --- Case A: quantiles already present (q05/q50/q95) ---
    has_qs = all(q in paths.columns for q in ["q05","q50","q95"]) and \
             all(pd.api.types.is_numeric_dtype(paths[q]) for q in ["q05","q50","q95"])
    if has_qs:
        qwide = paths[["indicator","horizon","q05","q50","q95"]].copy()
        diag = qwide.merge(truths, on=["indicator","horizon"], how="inner")
        diag["in90"] = (diag["truth"] >= diag["q05"]) & (diag["truth"] <= diag["q95"])
        cov_points = diag[["indicator","horizon","q05","q50","q95","truth","in90"]]

        def summarize(g):
            return pd.Series({"n": len(g), "covered_90": g["in90"].mean() if len(g) else np.nan})
        cov_sum_by_ind = cov_points.groupby("indicator", as_index=False).apply(summarize)
        cov_sum_by_ind.index = range(len(cov_sum_by_ind))  # clean index
        cov_sum_overall = summarize(cov_points)

        # PIT not available from quantiles-only → emit NaN PIT to satisfy downstream readers
        pit = truths[["indicator","horizon"]].copy()
        pit["pit"] = np.nan

        out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        qwide.to_csv(out_dir / "quantiles_calibrated.csv", index=False)
        cov_points.to_csv(out_dir / "coverage_points_calibrated.csv", index=False)
        cov_sum_by_ind.to_csv(out_dir / "coverage_summary_calibrated.csv", index=False)
        pit.to_csv(out_dir / "pit_values.csv", index=False)
        print(f"[diag] (quantiles-only) wrote to {out_dir}")
        return

    # --- Case B: wide draws → melt ---
    melted = melt_if_wide(paths)
    if melted is not None:
        value_col = "value"
        work = melted
    else:
        # --- Case C: long but unknown value column ---
        value_col = pick_value_col_long(paths)
        if value_col is None:
            raise SystemExit("Could not find a numeric path-value column in paths CSV.")
        work = paths[["indicator","horizon", value_col]].copy()

    # quantiles from draws
    qs = (
        work.groupby(["indicator","horizon"], as_index=False)[value_col]
            .quantile([0.05, 0.50, 0.95])
            .rename(columns={value_col: "quantile_value"})
    )
    qs["q"] = qs.groupby(["indicator","horizon"]).cumcount().map({0:0.05,1:0.5,2:0.95})
    qwide = (qs.pivot(index=["indicator","horizon"], columns="q", values="quantile_value")
               .rename(columns={0.05:"q05", 0.5:"q50", 0.95:"q95"})
               .reset_index())

    # PIT & coverage
    df = work.merge(truths[["indicator","horizon","truth"]], on=["indicator","horizon"], how="inner")
    pit = (
        df.assign(le=(df[value_col] <= df["truth"]))
          .groupby(["indicator","horizon"], as_index=False)["le"].mean()
          .rename(columns={"le":"pit"})
    )
    diag = qwide.merge(truths, on=["indicator","horizon"], how="inner")
    diag["in90"] = (diag["truth"] >= diag["q05"]) & (diag["truth"] <= diag["q95"])
    cov_points = diag[["indicator","horizon","q05","q50","q95","truth","in90"]].copy()

    def summarize(g):
        return pd.Series({"n": len(g), "covered_90": g["in90"].mean() if len(g) else np.nan})
    cov_sum_by_ind = cov_points.groupby("indicator", as_index=False).apply(summarize)
    cov_sum_by_ind.index = range(len(cov_sum_by_ind))

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    qwide.to_csv(out_dir / "quantiles_calibrated.csv", index=False)
    cov_points.to_csv(out_dir / "coverage_points_calibrated.csv", index=False)
    cov_sum_by_ind.to_csv(out_dir / "coverage_summary_calibrated.csv", index=False)
    pit.to_csv(out_dir / "pit_values.csv", index=False)
    print(f"[diag] wrote to {out_dir}")

if __name__ == "__main__":
    main()
