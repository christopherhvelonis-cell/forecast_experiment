# validation_nonUS/nonus_check_cli.py
#!/usr/bin/env python3
import argparse, os, sys, re
import pandas as pd

BAND_ALIASES = {
    "lo90": ["lo90","lower90","low90","l90","p05","q05","quantile_0.05","lo_90","lower_90","__lo_90__"],
    "hi90": ["hi90","upper90","high90","h90","p95","q95","quantile_0.95","hi_90","upper_90","__hi_90__"],
    "lo50": ["lo50","lower50","low50","l50","p25","q25","quantile_0.25","lo_50","lower_50","__lo_50__","__lo_50"],
    "hi50": ["hi50","upper50","high50","h50","p75","q75","quantile_0.75","hi_50","upper_50","__hi_50__","__hi_50"],
}

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).strip().lower())

def find_col(df: pd.DataFrame, explicit: str|None, candidates: list[str]) -> str|None:
    if explicit:
        # exact, case-insensitive, fuzzy
        if explicit in df.columns: return explicit
        lower = {c.lower(): c for c in df.columns}
        if explicit.lower() in lower: return lower[explicit.lower()]
        fmap = {norm(c): c for c in df.columns}
        if norm(explicit) in fmap: return fmap[norm(explicit)]
    # aliases
    for c in candidates:
        if c in df.columns: return c
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower: return lower[c.lower()]
    fmap = {norm(c): c for c in df.columns}
    for c in candidates:
        if norm(c) in fmap: return fmap[norm(c)]
    return None

def load_final(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Expect columns: year, indicator, horizon, q05,q50,q95,truth (truth optional)
    # Accept also: lo90/hi90, lo50/hi50 (but we only need q50 for center if present)
    need = {"indicator","horizon"}
    if not need.issubset(df.columns):
        raise ValueError(f"[final] missing columns {need - set(df.columns)} in {path}")
    # ensure types
    df["indicator"] = df["indicator"].astype(str)
    df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce").astype("Int64")
    return df

def load_proxy(path: str, target_indicator: str, assume_horizons: int|None) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path)
    orig_cols = df.columns.tolist()

    # indicator: if absent, add; otherwise coerce to target
    if "indicator" not in df.columns:
        df["indicator"] = target_indicator
    else:
        df["indicator"] = target_indicator

    # horizon: if absent and user provided assume_horizons, synthesize 1..N
    if "horizon" not in df.columns and assume_horizons:
        n = int(assume_horizons)
        if len(df) == n:
            df["horizon"] = range(1, n+1)
        else:
            # best-effort: make horizons 1..len(df)
            df["horizon"] = range(1, len(df)+1)
    elif "horizon" not in df.columns:
        # still try to recover from a 'year' column by ordering
        if "year" in df.columns:
            df = df.sort_values("year").copy()
            df["horizon"] = range(1, len(df)+1)
        else:
            # we will fail later if horizon still missing
            pass

    # detect bands
    lo90 = find_col(df, None, BAND_ALIASES["lo90"])
    hi90 = find_col(df, None, BAND_ALIASES["hi90"])
    lo50 = find_col(df, None, BAND_ALIASES["lo50"])
    hi50 = find_col(df, None, BAND_ALIASES["hi50"])

    info = dict(
        orig_cols=orig_cols,
        resolved=dict(lo90=lo90, hi90=hi90, lo50=lo50, hi50=hi50),
        n_rows=len(df)
    )

    # rename if present
    ren = {}
    if lo90: ren[lo90] = "lo90"
    if hi90: ren[hi90] = "hi90"
    if lo50: ren[lo50] = "lo50"
    if hi50: ren[hi50] = "hi50"
    if ren:
        df = df.rename(columns=ren)

    have_90 = {"lo90","hi90"}.issubset(df.columns)
    have_50 = {"lo50","hi50"}.issubset(df.columns)
    if not (have_90 or have_50):
        raise ValueError("[nonUS] Proxy file has no usable band columns. "
                         "Provide 90% (lo90/hi90) or 50% (lo50/hi50) bands, or run your normalizer.")

    # coerce numerics & clean
    for c in ["horizon","lo90","hi90","lo50","hi50"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "horizon" not in df.columns:
        raise ValueError("[nonUS] Proxy has no 'horizon' even after recovery. "
                         "Re-run with --assume_horizons 15 (or actual N).")

    # keep only rows with at least one band pair
    keep = df.copy()
    if have_90:
        keep = keep[keep["lo90"].notna() & keep["hi90"].notna()]
    elif have_50:
        keep = keep[keep["lo50"].notna() & keep["hi50"].notna()]

    keep["horizon"] = keep["horizon"].astype("Int64")

    msg = (f"[nonUS] Proxy summary → rows={len(df)} | usable_rows={len(keep)} | "
           f"bands: lo50={have_50} lo90={have_90} | "
           f"resolved={info['resolved']} | columns={orig_cols}")
    print(msg)

    return keep, info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final_calibrated_csv", required=True)
    ap.add_argument("--proxy_csv", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--target_indicator", default="trust_media_pct",
                    help="FINAL indicator name to compare against (default trust_media_pct)")
    ap.add_argument("--assume_horizons", type=int, default=15,
                    help="If proxy lacks 'horizon', synthesize 1..N (default 15)")
    args = ap.parse_args()

    final = load_final(args.final_calibrated_csv)
    final = final[final["indicator"].astype(str) == args.target_indicator].copy()
    final = final[final["horizon"].notna()].copy()
    final["horizon"] = final["horizon"].astype("Int64")

    proxy, info = load_proxy(args.proxy_csv, args.target_indicator, args.assume_horizons)

    if proxy.empty:
        raise ValueError("[nonUS] After cleaning, proxy has no usable rows.")

    # pick which bands to use (prefer 90%, else 50%)
    band_pair = ("lo90","hi90") if {"lo90","hi90"}.issubset(proxy.columns) else ("lo50","hi50")
    lo_col, hi_col = band_pair

    # merge on indicator + horizon
    m = (final[["indicator","horizon","q50"]]
         .merge(proxy[["indicator","horizon",lo_col,hi_col]],
                on=["indicator","horizon"], how="inner"))

    if m.empty:
        raise ValueError(f"[nonUS] After merge, no rows overlapped on indicator/horizon.\n"
                         f"Target indicator: {args.target_indicator}\n"
                         f"FINAL horizons present: {sorted(final['horizon'].dropna().unique().tolist())[:10]} ...\n"
                         f"Proxy horizons present: {sorted(proxy['horizon'].dropna().unique().tolist())[:10]} ...")

    # coverage check: center (q50) within band
    m["covered"] = (m["q50"] >= m[lo_col]) & (m["q50"] <= m[hi_col])

    # write outputs
    os.makedirs(args.out_dir, exist_ok=True)
    pt_path = os.path.join(args.out_dir, "coverage_points_nonUS.csv")
    sm_path = os.path.join(args.out_dir, "coverage_summary_nonUS.csv")

    m[["indicator","horizon","q50",lo_col,hi_col,"covered"]].to_csv(pt_path, index=False)

    summary = (m.assign(n=1)
                 .groupby(["indicator"])
                 .agg(n_obs=("n","sum"),
                      share_covered=("covered","mean"))
                 .reset_index())
    summary.to_csv(sm_path, index=False)

    print(f"Wrote: {pt_path}")
    print(f"Wrote: {sm_path}")

if __name__ == "__main__":
    main()
