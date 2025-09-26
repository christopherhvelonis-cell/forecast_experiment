#!/usr/bin/env python
# reports/make_final_report.py
from pathlib import Path

parts = []
paths = [
  "eval/results/significance_dm_prepost.csv",
  "ensemble/results_fforma/summary_by_h_crps.csv",
  "ensemble/results_fforma/summary_by_h_brier.csv",
  "eval/results/ensemble_retro_v2_postcal/metrics_ENSEMBLE.csv"
]
for p in paths:
    f = Path(p)
    if f.exists():
        parts.append(f"## {p}\n```\n{f.read_text().splitlines()[0:15]}\n```")

out = "\n\n".join(parts)
Path("reports/final_report.md").write_text(out, encoding="utf-8")
print("[ok] wrote reports/final_report.md")
