import argparse, pandas as pd, numpy as np
from pathlib import Path

def pct(s, q): return float(np.nanpercentile(s, q))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths_csv", required=True, help="fsm_chatgpt_<YEAR>_paths.csv")
    ap.add_argument("--truths_csv", required=True,
                    help="CSV with realized values. Columns: indicator, horizon, truth")
    ap.add_argument("--out_dir", required=True, help="diagnostics/FINAL_<YEAR>")
    args = ap.parse_args()

    paths = pd.read_csv(args.paths_csv)  # expected: indicator,horizon,path,value
    truths = pd.read_csv(args.truths_csv)  # expected: indicator,horizon,truth

    # --- Quantiles (q05,q25,q50,q75,q95) ---
    qs = (paths
          .groupby(["indicator","horizon"])["value"]
          .agg(q05=lambda s: pct(s,5),
               q25=lambda s: pct(s,25),
               q50=lambda s: pct(s,50),
               q75=lambda s: pct(s,75),
               q95=lambda s: pct(s,95))
          .reset_index())
    (Path(args.out_dir)/"quantiles_calibrated.csv").parent.mkdir(parents=True, exist_ok=True)
    qs.to_csv(Path(args.out_dir)/"quantiles_calibrated.csv", index=False)

    # --- PIT values ---
    # PIT = rank of truth among simulated paths (empirical CDF)
    merged = paths.merge(truths, on=["indicator","horizon"], how="inner")
    # For each (indicator,horizon), PIT = mean( value <= truth )
    pit = (merged.assign(le=lambda d: (d["value"] <= d["truth"]).astype(float))
           .groupby(["indicator","horizon"])["le"].mean()
           .rename("pit").reset_index())
    pit.to_csv(Path(args.out_dir)/"pit_values.csv", index=False)

    # --- Coverage points at levels 0.5 and 0.9 ---
    cov = qs.merge(truths, on=["indicator","horizon"], how="inner")
    cov["covered_90"] = (cov["truth"] >= cov["q05"]) & (cov["truth"] <= cov["q95"])
    cov["covered_50"] = (cov["truth"] >= cov["q25"]) & (cov["truth"] <= cov["q75"])
    # long format: indicator,horizon,level,covered
    rows = []
    for _, r in cov.iterrows():
        rows.append((r["indicator"], r["horizon"], 0.5, bool(r["covered_50"])))
        rows.append((r["indicator"], r["horizon"], 0.9, bool(r["covered_90"])))
    cov_pts = pd.DataFrame(rows, columns=["indicator","horizon","level","covered"])
    cov_pts.to_csv(Path(args.out_dir)/"coverage_points_calibrated.csv", index=False)

    # Optional: a tiny summary
    cov_sum = (cov_pts.groupby(["indicator","level"])["covered"]
               .mean().reset_index()
               .rename(columns={"covered":"empirical_coverage"}))
    cov_sum.to_csv(Path(args.out_dir)/"coverage_summary_calibrated.csv", index=False)

    print(f"[ok] Wrote quantiles_calibrated.csv, pit_values.csv, coverage_points_calibrated.csv, coverage_summary_calibrated.csv -> {args.out_dir}")

if __name__ == "__main__":
    main()
