#!/usr/bin/env python3
import os, argparse
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENSEMBLE_Q = os.path.join(ROOT, "ensemble", "quantiles_ensemble.csv")
REALIZED   = os.path.join(ROOT, "eval", "results", "realized_by_origin.csv")
OUTDIR     = os.path.join(ROOT, "eval", "results")

def pivot_long_to_wide(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Expect columns: indicator, horizon, origin_year, quantile, value, ...
    Return wide with q05,q50,q95.
    """
    need = {"indicator","horizon","origin_year","quantile","value"}
    if not need.issubset(df_long.columns):
        raise SystemExit("[error] long-format ensemble must have columns "
                         "indicator,horizon,origin_year,quantile,value")

    q = df_long.copy()

    # map quantile values/labels -> q05/q50/q95
    def qname(x):
        s = str(x).strip().lower()
        try:
            v = float(s)
            if abs(v-0.05) < 1e-12: return "q05"
            if abs(v-0.50) < 1e-12: return "q50"
            if abs(v-0.95) < 1e-12: return "q95"
        except Exception:
            pass
        if s in {"0.05","05","5","p05","q05","lower","lwr"}: return "q05"
        if s in {"0.5","50","p50","q50","median"}:           return "q50"
        if s in {"0.95","95","p95","q95","upper","upr"}:     return "q95"
        return None

    q["qcol"] = q["quantile"].map(qname)
    q = q[q["qcol"].isin(["q05","q50","q95"])].copy()
    if q.empty:
        raise SystemExit("[error] could not map quantile values to q05/q50/q95")

    wide = (q.pivot_table(index=["indicator","horizon","origin_year"],
                          columns="qcol", values="value", aggfunc="mean")
              .reset_index())
    missing = [c for c in ["q05","q50","q95"] if c not in wide.columns]
    if missing:
        raise SystemExit(f"[error] after pivot, missing columns: {missing}")
    return wide

def coalesce_truth_cols(df: pd.DataFrame) -> pd.Series:
    """
    After a merge we might have truth_x/truth_y; return a single 'truth' series.
    Preference: truth_y (from realized), then truth_x (pre-filled), else NA.
    """
    if "truth" in df.columns:
        return df["truth"]
    if "truth_y" in df.columns:
        base = df["truth_y"]
        if "truth_x" in df.columns:
            base = base.fillna(df["truth_x"])
        return base
    if "truth_x" in df.columns:
        return df["truth_x"]
    return pd.Series([pd.NA]*len(df), index=df.index, name="truth")

def merge_truth(wide: pd.DataFrame, origin_year: int) -> pd.DataFrame:
    """
    Merge realized truth if available (indicator,origin_year,horizon,value -> truth).
    Always returns a frame with a single 'truth' column.
    """
    out = wide.copy()
    out["year"] = int(origin_year) + out["horizon"].astype(int)
    out["truth"] = pd.NA  # pre-fill so we always have a truth column

    if os.path.exists(REALIZED):
        r = pd.read_csv(REALIZED)
        if {"indicator","origin_year","horizon","value"}.issubset(r.columns):
            rr = (r[r["origin_year"].astype(int) == int(origin_year)]
                    .loc[:, ["indicator","horizon","value"]]
                    .rename(columns={"value":"truth"}))
            out = out.merge(rr, on=["indicator","horizon"], how="left", suffixes=("_x","_y"))

    # coalesce any truth_x/truth_y back into a single 'truth'
    truth = coalesce_truth_cols(out)
    out = out.drop(columns=[c for c in ["truth_x","truth_y"] if c in out.columns], errors="ignore")
    out["truth"] = truth

    out = out[["year","indicator","horizon","q05","q50","q95","truth"]]
    out = out.sort_values(["indicator","horizon"]).reset_index(drop=True)
    return out

def main(origin_year: int, out_csv: str | None):
    if not os.path.exists(ENSEMBLE_Q):
        raise SystemExit(f"[error] missing {os.path.relpath(ENSEMBLE_Q, ROOT)}")

    raw = pd.read_csv(ENSEMBLE_Q)
    cols = set(raw.columns)

    # Path A: long format (what you have)
    if {"indicator","horizon","origin_year","quantile","value"}.issubset(cols):
        long = raw[["indicator","horizon","origin_year","quantile","value"]].copy()
        long["origin_year"] = long["origin_year"].astype(int)
        if (long["origin_year"] == int(origin_year)).any():
            long = long[long["origin_year"] == int(origin_year)].copy()
        wide = pivot_long_to_wide(long)

    # Path B: already wide
    elif {"indicator","horizon","origin_year","q05","q50","q95"}.issubset(cols):
        wide = raw[["indicator","horizon","origin_year","q05","q50","q95"]].copy()
        if (wide["origin_year"] == int(origin_year)).any():
            wide = wide[wide["origin_year"] == int(origin_year)].copy()
    else:
        raise SystemExit("[error] ensemble\\quantiles_ensemble.csv is neither recognized long format "
                         "nor wide (q05,q50,q95).")

    if wide.empty:
        raise SystemExit(f"[error] no rows to write for origin_year={origin_year}")

    final_df = merge_truth(wide, origin_year)

    if out_csv is None:
        out_csv = os.path.join(OUTDIR, f"FINAL_{origin_year}_calibrated.csv")
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    final_df.to_csv(out_csv, index=False)
    print(f"[ok] wrote {os.path.relpath(out_csv, ROOT)}  rows={len(final_df)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", type=int, required=True, help="Origin year, e.g. 1995")
    ap.add_argument("--out_csv", default=None)
    a = ap.parse_args()
    main(a.origin, a.out_csv)
