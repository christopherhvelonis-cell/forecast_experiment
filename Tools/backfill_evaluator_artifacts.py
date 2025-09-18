import os, sys
import pandas as pd

def backfill(out_dir):
    out_dir = os.path.abspath(out_dir)
    mpath = os.path.join(out_dir, "metrics_by_horizon.csv")
    if not os.path.exists(mpath):
        print(f"[backfill] skip: {mpath} missing")
        return

    m = pd.read_csv(mpath)
    # loss_differences.csv
    need = {"indicator","horizon","covered_50_rate","covered_90_rate"}
    if need.issubset(m.columns):
        ld = m[list(need)].copy()
        ld["loss50_abs_error"] = (ld["covered_50_rate"] - 0.5).abs()
        ld["loss90_abs_error"] = (ld["covered_90_rate"] - 0.9).abs()
        ld.to_csv(os.path.join(out_dir, "loss_differences.csv"), index=False)
        print(f"[backfill] wrote loss_differences.csv -> {out_dir}")
    else:
        print(f"[backfill] skip loss_differences: columns missing in {mpath}")

    # crps_brier_summary.csv (compatibility file)
    cov_path = os.path.join(out_dir, "coverage_overall.csv")
    if os.path.exists(cov_path):
        cov = pd.read_csv(cov_path)
        cmap = {c.lower(): c for c in cov.columns}
        def col(*names):
            for n in names:
                if n in cmap: return cmap[n]
            return None
        ind = col("indicator")
        c50 = col("cov50_overall","covered_50_rate","0.5","50%","50")
        c90 = col("cov90_overall","covered_90_rate","0.9","90%","90")

        cols = [x for x in [ind,c50,c90] if x]
        base = cov[cols].copy() if cols else pd.DataFrame()
        if ind and ind != "indicator": base = base.rename(columns={ind:"indicator"})
        if c50 and c50 != "cov50_overall": base = base.rename(columns={c50:"cov50_overall"})
        if c90 and c90 != "cov90_overall": base = base.rename(columns={c90:"cov90_overall"})
    else:
        base = pd.DataFrame(columns=["indicator","cov50_overall","cov90_overall"])

    for c in ["indicator","cov50_overall","cov90_overall"]:
        if c not in base.columns: base[c] = pd.NA

    base["crps_mean"]  = pd.NA
    base["brier_mean"] = pd.NA
    base.to_csv(os.path.join(out_dir, "crps_brier_summary.csv"), index=False)
    print(f"[backfill] wrote crps_brier_summary.csv -> {out_dir}")

if __name__ == "__main__":
    for d in sys.argv[1:]:
        backfill(d)
