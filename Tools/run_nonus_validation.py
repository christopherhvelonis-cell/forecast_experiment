#!/usr/bin/env python3
import os, json, argparse
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPECS = os.path.join(ROOT, "validation_nonUS", "specs.json")
OUTCSV = os.path.join(ROOT, "validation_nonUS", "nonus_validation_results.csv")

def main(spec_path=SPECS, out_csv=OUTCSV):
    # Load specs (handle BOM)
    with open(spec_path, "r", encoding="utf-8-sig") as f:
        specs = json.load(f)

    rows = []
    for s in specs.get("validations", []):
        us_indicator = s.get("us_indicator")
        region = s.get("region")
        period = s.get("period")
        confidence = s.get("confidence", "M")

        proxy_file = os.path.join(ROOT, "validation_nonUS", s.get("proxy_file", ""))
        if not os.path.exists(proxy_file):
            rows.append({
                "us_indicator": us_indicator,
                "region": region,
                "period": period,
                "confidence": confidence,
                "status": "MISSING_PROXY_FILE",
                "empirical_50": None,
                "empirical_90": None,
                "abs_err_50pp": None,
                "abs_err_90pp": None,
                "rows": 0,
                "note": f"Expected {proxy_file}"
            })
            continue

        try:
            df = pd.read_csv(proxy_file)
        except Exception as e:
            rows.append({
                "us_indicator": us_indicator,
                "region": region,
                "period": period,
                "confidence": confidence,
                "status": "FAILED_READ",
                "empirical_50": None,
                "empirical_90": None,
                "abs_err_50pp": None,
                "abs_err_90pp": None,
                "rows": 0,
                "note": str(e)
            })
            continue

        rows.append({
            "us_indicator": us_indicator,
            "region": region,
            "period": period,
            "confidence": confidence,
            "status": "OK",
            "empirical_50": df.mean(numeric_only=True).get("empirical_50", None),
            "empirical_90": df.mean(numeric_only=True).get("empirical_90", None),
            "abs_err_50pp": df.mean(numeric_only=True).get("abs_err_50pp", None),
            "abs_err_90pp": df.mean(numeric_only=True).get("abs_err_90pp", None),
            "rows": len(df),
            "note": ""
        })

    # Always ensure header
    cols = [
        "us_indicator","region","period","confidence","status",
        "empirical_50","empirical_90","abs_err_50pp","abs_err_90pp",
        "rows","note"
    ]
    out = pd.DataFrame(rows, columns=cols)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"[ok] wrote {os.path.relpath(out_csv, ROOT)} rows={len(out)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", default=SPECS)
    ap.add_argument("--out_csv", default=OUTCSV)
    a = ap.parse_args()
    main(a.specs, a.out_csv)
