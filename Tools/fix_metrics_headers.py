# Tools\fix_metrics_headers.py
# Normalizes headers (horizon/metric/value) and fills missing horizon for composite rows with "1".
import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def norm_key(k): 
    return (k or "").strip().lstrip("\ufeff").lower()

def fix_file(p):
    if not p.exists(): 
        return False
    with p.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        rr = { norm_key(k): v for k,v in r.items() }
        h = (rr.get("horizon") or "").strip()
        m = (rr.get("metric")  or "").strip()
        v = (rr.get("value")   or "").strip()
        if m == "composite_mean" and (h == "" or h is None):
            h = "1"
        out.append({"horizon": h, "metric": m, "value": v})
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["horizon","metric","value"])
        w.writeheader(); w.writerows(out)
    return True

def main():
    changed = 0
    for y in [1995,2000,2005,2010]:
        p = V2 / f"FINAL_{y}" / "metrics_by_horizon.csv"
        if fix_file(p): 
            print(f"[fixed] {p}"); changed += 1
    print(f"[summary] files_fixed={changed}")
if __name__ == "__main__":
    main()
