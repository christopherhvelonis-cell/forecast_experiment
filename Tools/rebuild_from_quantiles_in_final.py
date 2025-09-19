import pandas as pd, numpy as np
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

def rebuild_from_quantiles(year:int)->bool:
    final_dir = Path(f"eval/results/diagnostics/FINAL_{year}")
    qfile = final_dir / "quantiles_calibrated.csv"
    tfile = Path(f"data/truths/truths_{year}.csv")
    if not qfile.exists() or not tfile.exists():
        print(f"[rebuildQ] skip {year} (missing {qfile} or {tfile})")
        return False

    q = pd.read_csv(qfile)
    # Normalize expected columns
    cols = {c.lower(): c for c in q.columns}
    need = ["indicator","horizon","q05","q50","q95"]
    missing = [c for c in need if c not in cols]
    # Try a few alternates
    if missing:
        alt = {"indicator":["name","series","variable"],
               "horizon":["h","lead"]}
        for k in ["indicator","horizon"]:
            if k in missing:
                for a in alt[k]:
                    if a in cols:
                        cols[k]=cols[a]
                        missing.remove(k)
                        break
    if any(k not in cols for k in ["indicator","horizon"]) or not {"q05","q50","q95"}.issubset(set(map(str.lower,q.columns))):
        raise SystemExit(f"{qfile} must include indicator,horizon,q05,q50,q95 (got {list(q.columns)})")

    q = q.rename(columns={cols["indicator"]:"indicator", cols["horizon"]:"horizon"})
    # Ensure numeric
    for c in ["q05","q50","q95"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")

    t = pd.read_csv(tfile)
    t.columns = [c.lower() for c in t.columns]
    if not {"indicator","horizon","truth"}.issubset(t.columns):
        raise SystemExit(f"{tfile} must have columns indicator,horizon,truth")
    t["truth"] = pd.to_numeric(t["truth"], errors="coerce")

    df = q.merge(t[["indicator","horizon","truth"]], on=["indicator","horizon"], how="left")
    # in90 and long coverage
    df["in90"] = (df["truth"] >= df["q05"]) & (df["truth"] <= df["q95"])
    cov90 = df[["indicator","horizon","in90"]].copy()
    cov90["level"] = 0.9
    cov90 = cov90.rename(columns={"in90":"covered"})
    cov90["covered"] = cov90["covered"].astype(int)
    cov90 = cov90[["indicator","horizon","level","covered"]]

    # PIT + a derived 50% coverage from PIT central (0.25..0.75)
    pit = df[["indicator","horizon","q05","q50","q95","truth"]].copy()
    pit["pit"] = [approx_pit(a,b,c,d) for a,b,c,d in pit[["q05","q50","q95","truth"]].itertuples(index=False, name=None)]
    pit[["indicator","horizon","pit"]].to_csv(final_dir / "pit_values_calibrated.csv", index=False)

    cov50 = pit[["indicator","horizon","pit"]].copy()
    cov50["level"] = 0.5
    cov50["covered"] = ((cov50["pit"] >= 0.25) & (cov50["pit"] <= 0.75)).astype(int)
    cov50 = cov50[["indicator","horizon","level","covered"]]

    cov_long = pd.concat([cov90, cov50], ignore_index=True)

    # Write files expected by evaluator
    cov_long.to_csv(final_dir / "coverage_points_calibrated.csv", index=False)
    cov_sum = (cov_long.groupby(["indicator","level"], as_index=False)
                        .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"] / cov_sum["total"]
    cov_sum.to_csv(final_dir / "coverage_summary_calibrated.csv", index=False)

    print(f"[rebuildQ] {year}: wrote coverage_points_calibrated.csv (long), coverage_summary_calibrated.csv, pit_values_calibrated.csv")
    return True

def main():
    for y in YEARS:
        try:
            rebuild_from_quantiles(y)
        except Exception as e:
            print(f"[rebuildQ] ERROR {y}: {e}")

if __name__ == "__main__":
    main()
