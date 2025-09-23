# Tools/normalize_proxy_schema.py
#!/usr/bin/env python3
import argparse, os, re, sys
import pandas as pd

# Known alias sets we'll try to map into lo50/hi50/lo90/hi90
ALIASES = {
    "lo90": ["lo90","lower90","low90","l90","p05","q05","quantile_0.05","lo_90","lower_90","__lo_90__"],
    "hi90": ["hi90","upper90","high90","h90","p95","q95","quantile_0.95","hi_90","upper_90","__hi_90__"],
    "lo50": ["lo50","lower50","low50","l50","p25","q25","quantile_0.25","lo_50","lower_50","__lo_50__"],
    "hi50": ["hi50","upper50","high50","h50","p75","q75","quantile_0.75","hi_50","upper_50","__hi_50__"],
}

def normkey(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.strip().lower())

def resolve_col(df: pd.DataFrame, requested: str | None, candidates: list[str]) -> str | None:
    """Resolve a column name by exact, case-insensitive, and fuzzy key match."""
    if requested:
        # try exact
        if requested in df.columns: return requested
        # try case-insensitive exact
        lower = {c.lower(): c for c in df.columns}
        if requested.lower() in lower: return lower[requested.lower()]
        # try fuzzy normalized
        fmap = {normkey(c): c for c in df.columns}
        rk = normkey(requested)
        if rk in fmap: return fmap[rk]
    # otherwise use aliases
    # exact first
    for cand in candidates:
        if cand in df.columns: return cand
    # case-insensitive
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower: return lower[cand.lower()]
    # fuzzy
    fmap = {normkey(c): c for c in df.columns}
    for cand in candidates:
        ck = normkey(cand)
        if ck in fmap: return fmap[ck]
    return None

def main(in_csv, out_csv, indicator, indicator_col="indicator", horizon_col="horizon",
         lo90=None, hi90=None, lo50=None, hi50=None, fallback_width_pp=None):
    if not os.path.exists(in_csv):
        print(f"[error] missing {in_csv}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(in_csv)

    # ensure indicator column exists and matches target
    if indicator_col not in df.columns:
        df[indicator_col] = indicator
    else:
        df[indicator_col] = indicator

    # ensure horizon exists; if not, make 1..N
    if horizon_col not in df.columns:
        df[horizon_col] = range(1, len(df) + 1)

    # try to resolve band columns (explicit first, then aliases)
    lo90_col = resolve_col(df, lo90, ALIASES["lo90"])
    hi90_col = resolve_col(df, hi90, ALIASES["hi90"])
    lo50_col = resolve_col(df, lo50, ALIASES["lo50"])
    hi50_col = resolve_col(df, hi50, ALIASES["hi50"])

    out = df.copy()

    # rename any resolved cols into canonical names
    ren = {}
    if lo90_col: ren[lo90_col] = "lo90"
    if hi90_col: ren[hi90_col] = "hi90"
    if lo50_col: ren[lo50_col] = "lo50"
    if hi50_col: ren[hi50_col] = "hi50"
    if ren:
        out = out.rename(columns=ren)

    have_90 = {"lo90","hi90"}.issubset(out.columns)
    have_50 = {"lo50","hi50"}.issubset(out.columns)

    # optional fallback: if no bands are found, synthesize loose 90% bands
    # from a central column (mean/median/value) and +/- fallback_width_pp percent.
    if not (have_90 or have_50):
        center_candidates = ["value","mean","median","center","q50","p50","quantile_0.50"]
        center_col = resolve_col(out, None, center_candidates)
        if center_col and fallback_width_pp is not None:
            frac = float(fallback_width_pp) / 100.0
            out["lo90"] = out[center_col] * (1.0 - frac)
            out["hi90"] = out[center_col] * (1.0 + frac)
            have_90 = True

    if not (have_90 or have_50):
        print("[error] could not find any recognized band columns. "
              "Expected some of lo90/hi90 or lo50/hi50 (or aliases like p05/p95).",
              file=sys.stderr)
        sys.exit(2)

    keep = [indicator_col, horizon_col] + [c for c in ["lo50","hi50","lo90","hi90"] if c in out.columns]
    out = out[keep].copy()
    out[horizon_col] = out[horizon_col].astype(int)

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"[ok] normalized -> {out_csv}  rows={len(out)}  cols={list(out.columns)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--indicator", required=True)
    ap.add_argument("--indicator_col", default="indicator")
    ap.add_argument("--horizon_col", default="horizon")
    # explicit source column names (before renaming)
    ap.add_argument("--lo90", default=None)
    ap.add_argument("--hi90", default=None)
    ap.add_argument("--lo50", default=None)
    ap.add_argument("--hi50", default=None)
    # fallback: synthesize 90% bands from a center column if nothing is found
    ap.add_argument("--fallback_width_pp", type=float, default=None,
                    help="if set (e.g. 10), create lo90/hi90 = center*(1±width%) when no bands are found")
    args = ap.parse_args()
    main(**vars(args))
