#!/usr/bin/env python3
"""
Append a short 'Ensemble vs Equal-Weight' section to REPORT.md
using eval/results/ensemble_vs_equal_weight.csv.
"""

import os, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
CMP  = os.path.join(RES, "ensemble_vs_equal_weight.csv")
RPT  = os.path.join(ROOT, "REPORT.md")

def main():
    if not os.path.exists(CMP):
        print("[warn] comparison file not found; run Tools/score_ensemble_from_quantiles.py first.")
        return
    df = pd.read_csv(CMP)
    if "delta_meta_minus_eq" not in df.columns or df.empty:
        print("[warn] comparison lacks delta column or is empty.")
        return
    mean_delta = df["delta_meta_minus_eq"].mean()
    share_better = (df["delta_meta_minus_eq"] < 0).mean()

    lines = []
    lines.append("\n## Ensemble vs Equal-Weight (FFORMA Phase)\n")
    lines.append(f"- Mean Δ (meta − equal-weight, composite loss): **{mean_delta:.6f}** (negative is better)")
    lines.append(f"- Share of (indicator,origin,horizon) where meta < equal-weight: **{share_better:.1%}**")
    lines.append(f"- Rows compared: **{len(df)}**\n")

    with open(RPT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[ok] appended summary to REPORT.md")

if __name__ == "__main__":
    main()
