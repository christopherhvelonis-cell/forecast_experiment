#!/usr/bin/env python3
"""
Append a short 'Significance (DM + FDR)' section to REPORT.md.
"""

import os, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
SIG  = os.path.join(RES, "significance_dm.csv")
RPT  = os.path.join(ROOT, "REPORT.md")

def main():
    if not os.path.exists(SIG):
        print("[warn] run Tools/run_significance_tests.py first.")
        return
    df = pd.read_csv(SIG)
    if df.empty:
        print("[warn] significance file is empty.")
        return
    mean_delta = df["mean_delta"].mean()
    win_share = (df["mean_delta"] < 0).mean()
    sig_share = (df["significant"] == True).mean()
    lines = []
    lines.append("\n## Significance (DM with HAC, BH-FDR)\n")
    lines.append(f"- Mean Δ(meta − eq) across tested groups: **{mean_delta:.6f}** (neg = good)")
    lines.append(f"- Share(meta better): **{win_share:.1%}**")
    lines.append(f"- Share(significant at FDR 10%): **{sig_share:.1%}**")
    with open(RPT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[ok] appended significance summary to REPORT.md")

if __name__ == "__main__":
    main()
