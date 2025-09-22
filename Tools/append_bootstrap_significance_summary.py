#!/usr/bin/env python3
"""
Append a short 'Significance (Block-Bootstrap)' section to REPORT.md
from eval/results/significance_dm_bootstrap.csv.
"""
import os, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
SIG  = os.path.join(RES, "significance_dm_bootstrap.csv")
RPT  = os.path.join(ROOT, "REPORT.md")

def main():
    if not os.path.exists(SIG):
        print("[warn] run Tools/run_significance_tests_bootstrap.py first.")
        return
    df = pd.read_csv(SIG)
    if df.empty:
        print("[warn] bootstrap significance file is empty.")
        return

    # Use horizon_bucket if present; else horizon
    bucket_col = "horizon_bucket" if "horizon_bucket" in df.columns else "horizon"
    mean_delta = df["mean_delta"].mean()
    win_share  = (df["mean_delta"] < 0).mean()
    sig_share  = (df["significant"] == True).mean()

    lines = []
    lines.append("\n## Significance (Block-Bootstrap)\n")
    lines.append(f"- Grouping: **{bucket_col}**")
    lines.append(f"- Mean Δ(meta − eq): **{mean_delta:.6f}** (negative = meta better)")
    lines.append(f"- Share(meta better): **{win_share:.1%}**")
    lines.append(f"- Share(significant at 10%): **{sig_share:.1%}**")
    lines.append(f"- Rows (groups tested): **{len(df)}**\n")

    with open(RPT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[ok] appended bootstrap significance summary to REPORT.md")

if __name__ == "__main__":
    main()
