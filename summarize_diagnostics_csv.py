# summarize_diagnostics_csv.py
"""
Scan eval/results/diagnostics/**/coverage_*_calibrated.csv and build rollups:
- overall_coverage_points.csv
- overall_coverage_summary.csv
Adds an 'origin' column parsed from directory name like hsm_chatgpt_2000_cal.
"""

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

ROOT = Path("eval/results/diagnostics")
POINTS_NAME = "coverage_points_calibrated.csv"
SUMMARY_NAME = "coverage_summary_calibrated.csv"

def _parse_origin(dirname: str) -> str:
    # e.g., hsm_chatgpt_2000_cal -> 2000
    m = re.search(r"_(\d{4})_cal$", dirname)
    return m.group(1) if m else ""

def main():
    if not ROOT.exists():
        print(f"[skip] {ROOT}: not found.")
        return

    points_rows = []
    summary_rows = []

    for sub in sorted([p for p in ROOT.iterdir() if p.is_dir()]):
        origin = _parse_origin(sub.name)
        # coverage points
        p_file = sub / POINTS_NAME
        if p_file.exists():
            try:
                pdf = pd.read_csv(p_file)
                if not pdf.empty and set(["indicator","year","horizon","level","covered"]).issubset(pdf.columns):
                    pdf["origin"] = origin
                    points_rows.append(pdf)
                else:
                    print(f"[skip] {sub}: points missing columns or empty.")
            except Exception as e:
                print(f"[skip] {sub}: failed to read points ({e}).")
        else:
            print(f"[skip] {sub}: no points file.")

        # coverage summary
        s_file = sub / SUMMARY_NAME
        if s_file.exists():
            try:
                sdf = pd.read_csv(s_file)
                if not sdf.empty and set(["indicator","level","covered","total","coverage_rate"]).issubset(sdf.columns):
                    sdf["origin"] = origin
                    summary_rows.append(sdf)
                else:
                    print(f"[skip] {sub}: summary missing columns or empty.")
            except Exception as e:
                print(f"[skip] {sub}: failed to read summary ({e}).")
        else:
            print(f"[skip] {sub}: no summary file.")

    out_dir = ROOT
    out_dir.mkdir(parents=True, exist_ok=True)

    if points_rows:
        all_points = pd.concat(points_rows, ignore_index=True)
        all_points = all_points[["origin","indicator","year","horizon","level","covered"]]
        all_points.to_csv(out_dir / "overall_coverage_points.csv", index=False)
        print(f"[write] {out_dir / 'overall_coverage_points.csv'} ({len(all_points)} rows)")
    else:
        print("No usable coverage points found.")

    if summary_rows:
        all_summary = pd.concat(summary_rows, ignore_index=True)
        # reorder & sort for readability
        all_summary = all_summary[["origin","indicator","level","covered","total","coverage_rate"]]
        all_summary.sort_values(["origin","indicator","level"], inplace=True)
        all_summary.to_csv(out_dir / "overall_coverage_summary.csv", index=False)
        print(f"[write] {out_dir / 'overall_coverage_summary.csv'} ({len(all_summary)} rows)")
    else:
        print("No usable coverage summaries found.")

if __name__ == "__main__":
    main()
