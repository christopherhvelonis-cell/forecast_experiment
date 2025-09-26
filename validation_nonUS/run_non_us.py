#!/usr/bin/env python
# validation_nonUS/run_non_us.py — scaffold (handles UTF-8 BOM)
import json, sys
from pathlib import Path
import pandas as pd

def main():
    specs_path = Path("validation_nonUS/specs.json")
    # NOTE: read with utf-8-sig to tolerate BOM written by Windows PowerShell
    specs = json.loads(specs_path.read_text(encoding="utf-8-sig"))
    outdir = Path("validation_nonUS/results"); outdir.mkdir(parents=True, exist_ok=True)

    rows=[]
    for r in specs["regions"]:
        rid = r["id"]; y0,y1 = r["years"]
        rows.append({"region":rid,"years_start":y0,"years_end":y1,"status":"PENDING_DATA","reuse_calibration":specs["reuse_calibration"]})

    pd.DataFrame(rows).to_csv(outdir/"summary_placeholder.csv", index=False)
    print("[ok] wrote validation_nonUS/results/summary_placeholder.csv")

if __name__ == "__main__":
    raise SystemExit(main())
