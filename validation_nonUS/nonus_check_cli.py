#!/usr/bin/env python
import argparse, os, pandas as pd, numpy as np

ALIASES = {
    "q50":  ["q50","p50","median","Q50","P50"],
    "q25":  ["q25","p25","quantile_25","Q25","P25"],
    "q75":  ["q75","p75","quantile_75","Q75","P75"],
    "q05":  ["q05","q5","p05","p5","quantile_5","quantile_05","Q05","Q5","P05","P5"],
    "q95":  ["q95","p95","quantile_95","Q95","P95"],
    "lo50": ["lo_50","lo50","l50","lower50","lower_50","band50_lo","low50","lo-50"],
    "hi50": ["hi_50","hi50","u50","upper50","upper_50","band50_hi","high50","hi-50"],
    "lo90": ["lo_90","lo90","l90","lower90","lower_90","band90_lo","low90","lo-90"],
    "hi90": ["hi_90","hi90","u90","upper90","upper_90","band90_hi","high90","hi-90"],
}

def pick_name(columns, alias_list):
    cols = set(columns)
    for a in alias_list:
        if a in cols: return a
    lower = {c.lower(): c for c in columns}
    for a in alias_list:
        if a.lower() in lower: return lower[a.lower()]
    return None

def detect_or_synthesize_bands(df):
    cols = list(df.columns)
    q50 = pick_name(cols, ALIASES["q50"])
    lo50 = pick_name(cols, ALIASES["lo50"]); hi50 = pick_name(cols, ALIASES["hi50"])
    lo90 = pick_name(cols, ALIASES["lo90"]); hi90 = pick_name(cols, ALIASES["hi90"])
    q25 = pick_name(cols, ALIASES["q25"]);  q75 = pick_name(cols, ALIASES["q75"])
    q05 = pick_name(cols, ALIASES["q05"]);  q95 = pick_name(cols, ALIASES["q95"])

    # 50% from q25/q75 if needed
    if (lo50 is None or hi50 is None) and (q25 and q75):
        df["__lo_50__"] = df[q25]; df["__hi_50__"] = df[q75]
        lo50, hi50 = "__lo_50__", "__hi_50__"

    # 90% from q05/q95 if needed
    if (lo90 is None or hi90 is None) and (q05 and q95):
        df["__lo_90__"] = df[q05]; df["__hi_90__"] = df[q95]
        lo90, hi90 = "__lo_90__", "__hi_90__"

    # Accept if we have at least one band (50 or 90)
    if (lo50 is None or hi50 is None) and (lo90 is None or hi90 is None):
        raise ValueError(
            "Could not detect 50% or 90% bands. "
            f"Available columns: {list(df.columns)}\n"
            "Need lo_50/hi_50 (or q25/q75) and/or lo_90/hi_90 (or q05/q95)."
        )
    return q50, lo50, hi50, lo90, hi90

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final_calibrated_csv", required=True)
    ap.add_argument("--proxy_csv", required=True)      # columns: year,value,indicator,region
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    us = pd.read_csv(args.final_calibrated_csv)
    px = pd.read_csv(args.proxy_csv)

    if "indicator" not in us.columns:
        raise ValueError("FINAL CSV must include 'indicator' column.")

    # Horizon
    hcol = "horizon" if "horizon" in us.columns else None
    if hcol is None:
        for c in ["lead","step","h","H"]:
            if c in us.columns: hcol = c
        if hcol is None:
            if "year" in us.columns:
                us["horizon"] = us["year"] - args.origin; hcol = "horizon"
            else:
                raise ValueError("Could not find/construct a 'horizon' column in FINAL CSV.")

    q50, lo50, hi50, lo90, hi90 = detect_or_synthesize_bands(us)
    print(f"[nonUS] Detected bands → lo50={lo50}, hi50={hi50}, lo90={lo90}, hi90={hi90}")

    # Proxy horizons
    need_px = {"year","value","indicator","region"}
    if not need_px.issubset(px.columns):
        raise ValueError(f"Proxy CSV must have columns {need_px}, found {list(px.columns)}")
    px["horizon"] = px["year"] - args.origin
    px = px[(px["horizon"]>=1) & (px["horizon"]<=15)].copy()

    # Join
    keep_cols = ["indicator", hcol]
    for c in [lo50, hi50, lo90, hi90]:
        if c is not None and c not in keep_cols:
            keep_cols.append(c)
    us_sub = us[keep_cols].copy().rename(columns={hcol:"horizon"})
    df = px.merge(us_sub, on=["indicator","horizon"], how="inner")

    if df.empty:
        raise ValueError(
            "After merge, no rows had available bands for these proxy horizons.\n"
            f"Proxy indicators: {px['indicator'].unique().tolist()}\n"
            f"FINAL indicators: {us['indicator'].unique().tolist()}"
        )

    # Coverage rows
    out = []
    for _,r in df.iterrows():
        base = {"region": r["region"], "indicator": r["indicator"], "horizon": int(r["horizon"])}
        v = r["value"]
        if (lo50 in df.columns) and (hi50 in df.columns) and pd.notna(r.get(lo50)) and pd.notna(r.get(hi50)):
            out.append({**base, "level": 0.5, "covered": int((v >= r[lo50]) and (v <= r[hi50]))})
        if (lo90 in df.columns) and (hi90 in df.columns) and pd.notna(r.get(lo90)) and pd.notna(r.get(hi90)):
            out.append({**base, "level": 0.9, "covered": int((v >= r[lo90]) and (v <= r[hi90]))})

    points = pd.DataFrame(out)
    if points.empty:
        raise ValueError("No usable coverage points could be computed (bands missing or NaN).")

    points = points.sort_values(["indicator","horizon","level"]).reset_index(drop=True)
    points.to_csv(os.path.join(args.out_dir, "coverage_points_nonUS.csv"), index=False)

    # ---- Backward-compatible aggregation (no tuple kwargs) ----
    gb = points.groupby(["region","indicator","level"])["covered"]
    summ = gb.sum().rename("covered").reset_index()
    tot  = gb.count().rename("total").reset_index()
    summ = summ.merge(tot, on=["region","indicator","level"])
    summ["coverage_rate"] = summ["covered"] / summ["total"]
    summ.to_csv(os.path.join(args.out_dir, "coverage_summary_nonUS.csv"), index=False)

    print("Wrote:", os.path.join(args.out_dir, "coverage_points_nonUS.csv"))
    print("Wrote:", os.path.join(args.out_dir, "coverage_summary_nonUS.csv"))

if __name__ == "__main__":
    main()
