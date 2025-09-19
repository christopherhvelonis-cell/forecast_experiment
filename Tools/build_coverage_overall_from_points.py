import os, glob
import pandas as pd

YEARS = [1985,1990,2005,2010,2015,2020]
for y in YEARS:
    fin = os.path.join("eval","results","diagnostics",f"FINAL_{y}","coverage_points_calibrated.csv")
    if not os.path.exists(fin): 
        print(f"[skip] {y}: no coverage_points_calibrated.csv"); 
        continue
    df = pd.read_csv(fin)
    if df.shape[0] == 0 or set(["indicator","horizon","level","covered"]) - set(df.columns):
        print(f"[skip] {y}: header-only or wrong schema"); 
        continue
    # compute overall coverage rate per indicator & level
    cov_overall = (df
        .groupby(["indicator","level"], as_index=False)
        .agg(coverage_rate=("covered","mean"), n=("covered","size")))
    # keep only 0.5/0.9 if present
    lv = set(cov_overall["level"].astype(str))
    if {"0.5","0.9"} & lv:
        cov_overall = cov_overall[cov_overall["level"].astype(str).isin(["0.5","0.9"])]
    # write to the evaluator's out dir
    out_dir = os.path.join("eval","results","v2",f"FINAL_{y}")
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "coverage_overall.csv")
    cov_overall.pivot(index="indicator", columns="level", values="coverage_rate").reset_index().to_csv(out_csv, index=False)
    print(f"[ok] {y}: wrote {out_csv} with {len(cov_overall)} rows")
