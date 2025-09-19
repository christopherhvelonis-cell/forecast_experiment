import pandas as pd, numpy as np
from pathlib import Path
import re, sys

def find_value_col(df):
    cand = [c for c in df.columns if c.lower() in ("value","val","y","quantile_value","v")]
    if cand: return cand[0]
    # try the only numeric column
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(num)==1: return num[0]
    # or last column
    return df.columns[-1]

def normalize_quant(q):
    """Return 'q05','q50','q95' or None if unrecognized."""
    if pd.isna(q): return None
    s = str(q).strip().lower()
    s = s.replace("p","q")
    if s in {"0.05","0,05","5","05","q05"}: return "q05"
    if s in {"0.5","0,5","50","q50"}:       return "q50"
    if s in {"0.95","0,95","95","q95"}:     return "q95"
    # tolerate like '5%','50%','95%'
    if s.endswith("%"):
        try:
            n = float(s[:-1])
            if abs(n-5)  < 1e-9: return "q05"
            if abs(n-50) < 1e-9: return "q50"
            if abs(n-95) < 1e-9: return "q95"
        except: pass
    if s.startswith("q"):
        try:
            n = float(s[1:])  # e.g. 'q0.05' or 'q5'
            if abs(n-0.05)<1e-9 or abs(n-5)<1e-9:  return "q05"
            if abs(n-0.5) <1e-9 or abs(n-50)<1e-9: return "q50"
            if abs(n-0.95)<1e-9 or abs(n-95)<1e-9: return "q95"
        except: pass
    return None

def rebuild_for_year(year:int):
    base = Path(f"eval/results/diagnostics/FINAL_{year}")
    base.mkdir(parents=True, exist_ok=True)

    paths_csv  = Path(f"eval/results/diagnostics/fsm_chatgpt_{year}_paths.csv")
    truths_csv = Path(f"data/truths/truths_{year}.csv")
    if not paths_csv.exists() or not truths_csv.exists():
        print(f"[rebuild] skip {year} (missing paths or truths)")
        return False

    p = pd.read_csv(paths_csv)
    cols = {c.lower(): c for c in p.columns}
    # basic columns
    ind_col = cols.get("indicator") or cols.get("name") or cols.get("series") or list(p.columns)[0]
    hor_col = cols.get("horizon")   or cols.get("h")    or "horizon"

    if ind_col not in p.columns or hor_col not in p.columns:
        raise SystemExit(f"{paths_csv} must have indicator and horizon-like columns")

    # quantile column guess
    q_col = cols.get("quantile") or cols.get("quant") or cols.get("alpha") or cols.get("q") or None
    if q_col is None:
        # sometimes quantiles are embedded as column names (wide form) — try to melt
        wide_qs = [c for c in p.columns if re.fullmatch(r"(q|p)?0?0?5|0?5|5|50|95|0?95|0?50|0?05", str(c).lower())]
        if wide_qs:
            p = p.melt(id_vars=[ind_col, hor_col], value_vars=wide_qs,
                       var_name="quantile", value_name="__value__")
            q_col = "quantile"
            val_col = "__value__"
        else:
            # fallback: assume there's a single set of quantiles encoded row-wise but unnamed -> try last col
            q_col = "quantile"
            p = p.rename(columns={list(p.columns)[-2]: q_col})
            val_col = find_value_col(p)
    else:
        val_col = find_value_col(p)

    # normalize quantile labels
    p["_q"] = p[q_col].apply(normalize_quant)
    p = p[p["_q"].isin(["q05","q50","q95"])].copy()

    # pivot to q05,q50,q95
    piv = (p
           .rename(columns={ind_col:"indicator", hor_col:"horizon", val_col:"value"})
           .pivot_table(index=["indicator","horizon"], columns="_q", values="value", aggfunc="last")
           .reset_index())
    # ensure columns exist
    for c in ["q05","q50","q95"]: 
        if c not in piv.columns: piv[c] = np.nan

    # merge truths
    t = pd.read_csv(truths_csv)
    t.columns = [c.lower() for c in t.columns]
    # truths file: indicator,horizon,truth
    if not {"indicator","horizon","truth"}.issubset(set(t.columns)):
        raise SystemExit(f"{truths_csv} must have columns indicator,horizon,truth")
    out = piv.merge(t[["indicator","horizon","truth"]], on=["indicator","horizon"], how="left")

    # compute in90
    out["in90"] = (out["truth"] >= out["q05"]) & (out["truth"] <= out["q95"])
    out = out[["indicator","horizon","q05","q50","q95","truth","in90"]]
    out.to_csv(base / "coverage_points_calibrated.csv", index=False)

    # make a simple PIT (approx from 3 quantiles)
    def approx_pit(q05,q50,q95,y):
        try:
            q05=float(q05); q50=float(q50); q95=float(q95); y=float(y)
        except: return 0.5
        if q95 < q50: q95=q50
        if q50 < q05: q50=q05
        if y <= q05: return 0.025
        if y >= q95: return 0.975
        if y <= q50 and q50>q05: return 0.05 + 0.45*(y-q05)/max(q50-q05,1e-12)
        if y >  q50 and q95>q50: return 0.50 + 0.45*(y-q50)/max(q95-q50,1e-12)
        return 0.5

    pit = out.copy()
    pit["pit"] = [approx_pit(a,b,c,d) for a,b,c,d in pit[["q05","q50","q95","truth"]].itertuples(index=False, name=None)]
    pit[["indicator","horizon","pit"]].to_csv(base / "pit_values_calibrated.csv", index=False)

    # coverage summary at 90% (plus also emit a 50% level for evaluator later)
    cov90 = out[["indicator","horizon","in90"]].copy()
    cov90["level"]=0.9
    cov90 = cov90.rename(columns={"in90":"covered"})
    cov50 = pit[["indicator","horizon","pit"]].copy()
    cov50["level"]=0.5
    cov50["covered"] = ((cov50["pit"]>=0.25)&(cov50["pit"]<=0.75)).astype(int)
    cov50 = cov50[["indicator","horizon","level","covered"]]
    cov90["covered"] = cov90["covered"].astype(int)
    cov90 = cov90[["indicator","horizon","level","covered"]]
    cov_long = pd.concat([cov90, cov50], ignore_index=True)
    cov_long.to_csv(base / "coverage_points_calibrated_long.csv", index=False)

    cov_sum = (cov_long.groupby(["indicator","level"], as_index=False)
               .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"]/cov_sum["total"]
    cov_sum.to_csv(base / "coverage_summary_calibrated.csv", index=False)

    print(f"[rebuild] wrote {base/'coverage_points_calibrated.csv'} and PIT")
    return True

def main():
    years = [1985,1990,2005,2010,2015,2020]
    for yr in years:
        try:
            rebuild_for_year(yr)
        except Exception as e:
            print(f"[rebuild] ERROR {yr}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
