# Tools/canonicalize_coverage.py
# Purpose: rewrite coverage_overall.csv files into canonical header: level,empirical

import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

YEARS = [1995,2000,2005,2010]

def normalize(path: pathlib.Path):
    if not path.exists():
        return False
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return False

    out = []
    for r in rows:
        # try several possible keys
        lvl = r.get("level") or r.get("coverage") or r.get("indicator") or ""
        emp = r.get("empirical") or r.get("value") or r.get("cov50_overall") or r.get("0.5") or ""
        lvl = (lvl or "").strip()
        emp = (emp or "").strip().replace(",", ".")
        if lvl and emp:
            try:
                out.append({"level": lvl, "empirical": float(emp)})
            except:
                continue

    if not out:
        return False

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["level","empirical"])
        w.writeheader()
        w.writerows(out)
    return True

def main():
    changed = 0
    for y in YEARS:
        p = V2 / f"FINAL_{y}" / "coverage_overall.csv"
        if normalize(p):
            print(f"[canon] {p}")
            changed += 1
    print(f"[summary] canonicalized={changed}")

if __name__ == "__main__":
    main()
