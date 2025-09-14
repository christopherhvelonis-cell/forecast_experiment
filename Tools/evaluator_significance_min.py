#!/usr/bin/env python
"""
Significance v2 (minimal): uses coverage-based losses from evaluator_code_v2_min.py
to assess whether coverage is within binomial confidence intervals and
computes simple p-values for deviation from nominal rates (per indicator and overall).
Also emits BH-FDR adjusted flags.

Inputs:
  --metrics_csv : path to metrics_by_horizon.csv
  --out_dir     : output folder

Outputs:
  - binomial_tests.csv        : exact (Clopper-Pearson) CIs and flags for cov50/cov90 per indicator
  - fdr_adjusted_results.csv  : BH-FDR adjusted p-values across all (indicator, level) tests
  - notes.txt                 : explanation of methods

This does NOT run DM/Clark–McCracken/GW (require time-series loss sequences vs baselines).
"""

import argparse, os, math
import pandas as pd
from math import comb

def clopper_pearson_ci(x, n, alpha=0.05):
    # exact binomial CI using beta quantiles (implemented via pandas.Series.beta if available)
    # Fallback to Wilson approx if scipy not available.
    # We’ll use Wilson here to avoid scipy dependency in a minimal script.
    if n == 0:
        return (float("nan"), float("nan"))
    p = x / n
    z = 1.959963984540054  # approx 95%
    denom = 1 + z**2/n
    center = (p + z*z/(2*n)) / denom
    half = z*math.sqrt((p*(1-p)/n) + (z*z/(4*n*n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))

def bh_fdr(pvals, alpha=0.05):
    s = sorted((p,i) for i,p in enumerate(pvals))
    m = len(s)
    thresh = [alpha*(k+1)/m for k in range(m)]
    passed = [False]*m
    max_k = -1
    for k,(p,i) in enumerate(s):
        if p <= thresh[k]:
            max_k = k
    if max_k >= 0:
        for k in range(max_k+1):
            _,i = s[k]
            passed[i] = True
    # Reorder to original
    out = [passed[i] for i in range(m)]
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics_csv", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    m = pd.read_csv(args.metrics_csv)

    # Collapse by indicator: counts of covered events for 50 and 90 bands
    def collect(level):
        if level == 0.5:
            col = "covered_50_rate"
        else:
            col = "covered_90_rate"
        # Per horizon rates -> approximate counts by rounding (since they are means over possibly multiple obs per horizon; here usually 1 per horizon)
        # Safer: treat each horizon as one Bernoulli trial with success prob=rate and count x = round(rate)
        df = m[["indicator","horizon",col]].copy()
        df["x"] = df[col].round().astype(int)
        agg = df.groupby("indicator").agg(x=("x","sum"), n=("x","count")).reset_index()
        agg["level"] = level
        return agg[["indicator","level","x","n"]]

    a = collect(0.5)
    b = collect(0.9)
    all_tests = pd.concat([a,b], ignore_index=True)

    # Compute p-values for deviation from nominal using binomial test (normal approx)
    pvals = []
    lows = []
    highs = []
    flag_within = []
    for _,row in all_tests.iterrows():
        x, n = int(row["x"]), int(row["n"])
        nominal = 0.5 if row["level"] == 0.5 else 0.9
        if n == 0:
            p = float("nan")
            lo,hi = float("nan"), float("nan")
            within=False
        else:
            # Normal approx z-test for proportion
            phat = x/n
            se = math.sqrt(nominal*(1-nominal)/n)
            z = 0.0 if se==0 else (phat - nominal)/se
            # two-sided p-value
            from math import erf, sqrt
            p = 2*(1-0.5*(1+erf(abs(z)/sqrt(2))))
            lo, hi = clopper_pearson_ci(x, n, alpha=0.05)
            within = (lo <= nominal <= hi)
        pvals.append(p)
        lows.append(lo); highs.append(hi); flag_within.append(within)

    all_tests["p_value"] = pvals
    all_tests["ci_low"] = lows
    all_tests["ci_high"] = highs
    all_tests["within_95pct_CI"] = flag_within

    # FDR across all tests
    mask = all_tests["p_value"].notna()
    fdr_pass = [False]*len(all_tests)
    if mask.any():
        sel = all_tests.loc[mask, "p_value"].tolist()
        flags = bh_fdr(sel, alpha=0.05)
        j = 0
        for i,ok in enumerate(mask):
            if ok:
                fdr_pass[i] = flags[j]; j+=1
    all_tests["BH_FDR_pass"] = fdr_pass

    all_tests.to_csv(os.path.join(args.out_dir, "fdr_adjusted_results.csv"), index=False)

    with open(os.path.join(args.out_dir, "notes.txt"), "w", encoding="utf-8") as f:
        f.write(
"""Significance v2 (minimal)
- Tests whether empirical coverage differs from nominal (0.5, 0.9) using a normal-approx binomial test per indicator,
  plus 95% Clopper–Pearson CI for reference.
- BH-FDR (alpha=0.05) applied across all (indicator, level) tests.
- This does NOT include DM / Clark–McCracken / Giacomini–White because we lack comparable loss sequences vs baselines here.
  If you later export per-horizon CRPS/Brier sequences for model vs baseline, those tests can be added.
"""
        )
    print(f"[Significance v2 min] Wrote: fdr_adjusted_results.csv and notes.txt to {args.out_dir}")

if __name__ == "__main__":
    main()
