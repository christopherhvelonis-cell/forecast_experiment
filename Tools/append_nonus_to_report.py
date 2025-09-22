#!/usr/bin/env python3
import os, argparse, pandas as pd
from pandas.errors import EmptyDataError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VALCSV = os.path.join(ROOT, "validation_nonUS", "nonus_validation_results.csv")
REPORT = os.path.join(ROOT, "REPORT.md")

def to_md(df):
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)

def main(csv_path=VALCSV, report_path=REPORT):
    empty_stub = True
    df = None
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            empty_stub = df.empty
        except EmptyDataError:
            empty_stub = True

    blocks = ["\n## Non-US Validation\n"]
    if empty_stub:
        blocks.append("_No validation rows produced (no proxies found in specs or data missing)._ \n")
    else:
        summary = (
            df.assign(is_ok=df["status"].eq("OK"))
              .groupby(["region","confidence"], dropna=False)["is_ok"]
              .mean()
              .reset_index()
              .rename(columns={"is_ok":"share_OK"})
        )
        blocks.append("**Summary (share OK by region/confidence)**\n\n")
        blocks.append(to_md(summary) + "\n\n")

        cols = [c for c in [
            "us_indicator","region","period","confidence","status",
            "empirical_50","empirical_90","abs_err_50pp","abs_err_90pp","rows","note"
        ] if c in df.columns]
        blocks.append("**Details**\n\n")
        blocks.append(to_md(df[cols]) + "\n")

    with open(report_path, "a", encoding="utf-8") as f:
        f.write("".join(blocks))
    print(f"[ok] appended Non-US validation summary to {os.path.relpath(report_path, ROOT)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=VALCSV)
    ap.add_argument("--report", default=REPORT)
    a = ap.parse_args()
    main(a.csv, a.report)
