import pandas as pd
from pathlib import Path

YEARS = [1985,1990,2005,2010,2015,2020]

def rebuild_from_quantiles(year:int):
    final_dir = Path(f"eval/results/diagnostics/FINAL_{year}")
    qfile = final_dir/"quantiles_calibrated.csv"
    tfile = Path(f"data/truths/truths_{year}.csv")
    if not qfile.exists() or not tfile.exists():
        print(f"[regen] skip {year} (missing {qfile} or {tfile})")
        return

    q = pd.read_csv(qfile)
    # normalize
    rename = {c:c.lower() for c in q.columns}
    q = q.rename(columns=rename)
    need = {"indicator","horizon","q05","q50","q95"}
    if not need.issubset(q.columns):
        raise SystemExit(f"{qfile} must include {need}, got {list(q.columns)}")
    for c in ["q05","q50","q95"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")

    t = pd.read_csv(tfile)
    t.columns = [c.lower() for c in t.columns]
    if not {"indicator","horizon","truth"}.issubset(t.columns):
        raise SystemExit(f"{tfile} must include indicator,horizon,truth")
    t["truth"] = pd.to_numeric(t["truth"], errors="coerce")

    df = q.merge(t[["indicator","horizon","truth"]], on=["indicator","horizon"], how="left")
    df["in90"] = (df["truth"] >= df["q05"]) & (df["truth"] <= df["q95"])

    # PIT for later 50% coverage
    def approx_pit(q05,q50,q95,y):
        try:
            q05=float(q05); q50=float(q50); q95=float(q95); y=float(y)
        except: return 0.5
        if q95 < q50: q95 = q50
        if q50 < q05: q50 = q05
        if y <= q05: return 0.025
        if y >= q95: return 0.975
        if y <= q50 and q50>q05: return 0.05 + 0.45*(y-q05)/max(q50-q05,1e-12)
        if y >  q50 and q95>q50: return 0.50 + 0.45*(y-q50)/max(q95-q50,1e-12)
        return 0.5

    pit = df[["indicator","horizon","q05","q50","q95","truth"]].copy()
    pit["pit"] = [approx_pit(a,b,c,d) for a,b,c,d in pit[["q05","q50","q95","truth"]].itertuples(index=False, name=None)]
    pit[["indicator","horizon","pit"]].to_csv(final_dir/"pit_values_calibrated.csv", index=False)

    # Build long-form coverage
    cov90 = df[["indicator","horizon","in90"]].rename(columns={"in90":"covered"})
    cov90["level"] = 0.9
    cov90["covered"] = cov90["covered"].astype(int)

    cov50 = pit[["indicator","horizon","pit"]].copy()
    cov50["covered"] = ((cov50["pit"] >= 0.25) & (cov50["pit"] <= 0.75)).astype(int)
    cov50["level"] = 0.5
    cov50 = cov50[["indicator","horizon","covered","level"]]

    cov = pd.concat([
        cov90[["indicator","horizon","covered","level"]],
        cov50
    ], ignore_index=True)

    # Ensure level numeric and only 0.5 / 0.9
    cov["level"] = pd.to_numeric(cov["level"], errors="coerce").round(2)
    cov = cov[cov["level"].isin([0.5, 0.9])]
    cov.to_csv(final_dir/"coverage_points_calibrated.csv", index=False)

    # summary
    cov_sum = (cov.groupby(["indicator","level"], as_index=False)
                 .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"]/cov_sum["total"]
    cov_sum.to_csv(final_dir/"coverage_summary_calibrated.csv", index=False)

    # tiny preview
    print(f"[regen] {year} levels={sorted(cov['level'].unique())} rows={len(cov)}")
    print(cov.head(6).to_string(index=False), "\n")

def main():
    for y in YEARS:
        rebuild_from_quantiles(y)

if __name__ == "__main__":
    main()
