import pandas as pd
from pathlib import Path

YEARS = [1985,1990,2005,2010,2015,2020]

def approx_pit(q05,q50,q95,y):
    try:
        q05=float(q05); q50=float(q50); q95=float(q95); y=float(y)
    except:
        return 0.5
    if q95 < q50: q95 = q50
    if q50 < q05: q50 = q05
    if y <= q05: return 0.025
    if y >= q95: return 0.975
    if y <= q50 and q50>q05: return 0.05 + 0.45*(y-q05)/max(q50-q05,1e-12)
    if y >  q50 and q95>q50: return 0.50 + 0.45*(y-q50)/max(q95-q50,1e-12)
    return 0.5

def rebuild_one(y:int):
    final_dir = Path(f"eval/results/diagnostics/FINAL_{y}")
    qfile = final_dir / "quantiles_calibrated.csv"
    tfile = Path(f"data/truths/truths_{y}.csv")
    if not qfile.exists() or not tfile.exists():
        print(f"[force] skip {y} (missing {qfile} or {tfile})")
        return

    q = pd.read_csv(qfile)
    cols = {c.lower(): c for c in q.columns}
    need = {"indicator","horizon","q05","q50","q95"}
    if not need.issubset(set(cols)):
        raise SystemExit(f"{qfile} must have columns {sorted(need)}; got {list(q.columns)}")

    q = q.rename(columns={cols["indicator"]:"indicator", cols["horizon"]:"horizon"})
    for c in ["q05","q50","q95"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")

    t = pd.read_csv(tfile)
    t.columns = [c.lower() for c in t.columns]
    if not {"indicator","horizon","truth"}.issubset(t.columns):
        raise SystemExit(f"{tfile} must have indicator,horizon,truth")
    t["truth"] = pd.to_numeric(t["truth"], errors="coerce")

    df = q.merge(t[["indicator","horizon","truth"]], on=["indicator","horizon"], how="left")

    # Make PIT and 50% coverage from PIT central
    pit = df[["indicator","horizon","q05","q50","q95","truth"]].copy()
    pit["pit"] = [approx_pit(a,b,c,d) for a,b,c,d in pit[["q05","q50","q95","truth"]].itertuples(index=False, name=None)]
    pit_out = pit[["indicator","horizon","pit"]].copy()
    pit_out.to_csv(final_dir / "pit_values_calibrated.csv", index=False)

    # 90% covered from q05..q95, 50% covered from PIT in [0.25, 0.75]
    cov90 = df[["indicator","horizon"]].copy()
    cov90["level"] = 0.9
    cov90["covered"] = ((df["truth"] >= df["q05"]) & (df["truth"] <= df["q95"])).astype(int)

    cov50 = pit_out[["indicator","horizon","pit"]].copy()
    cov50["level"] = 0.5
    cov50["covered"] = ((cov50["pit"] >= 0.25) & (cov50["pit"] <= 0.75)).astype(int)
    cov50 = cov50.drop(columns=["pit"])

    cov = pd.concat([cov90, cov50], ignore_index=True)
    # final hygiene
    cov["horizon"] = pd.to_numeric(cov["horizon"], errors="coerce").astype("Int64")
    cov["level"] = pd.to_numeric(cov["level"], errors="coerce")
    cov["covered"] = pd.to_numeric(cov["covered"], errors="coerce").clip(0,1).astype(int)
    cov = cov.dropna(subset=["indicator","horizon","level","covered"])
    cov = cov.sort_values(["indicator","horizon","level"])
    cov.to_csv(final_dir / "coverage_points_calibrated.csv", index=False)

    # summary (not strictly needed by evaluator but good to have)
    cov_sum = (cov.groupby(["indicator","level"], as_index=False)
                 .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"]/cov_sum["total"]
    cov_sum.to_csv(final_dir / "coverage_summary_calibrated.csv", index=False)

    print(f"[force] {y}: rows={len(cov)}  levels={sorted(cov['level'].unique().tolist())}")

def main():
    for y in YEARS:
        rebuild_one(y)

if __name__ == "__main__":
    main()
