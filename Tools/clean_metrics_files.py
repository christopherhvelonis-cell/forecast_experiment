# Tools/clean_metrics_files.py
import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def normalize(path: pathlib.Path):
    if not path.exists(): 
        return False
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        # normalize keys and trim
        h = (r.get("horizon") or r.get("HORIZON") or "").strip()
        m = (r.get("metric")  or r.get("METRIC")  or "").strip()
        v = (r.get("value")   or r.get("VALUE")   or "").strip()
        # keep only non-empty, well-formed rows
        if h or m or v:
            out.append({"horizon": h, "metric": m, "value": v})
    # write back with clean header
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["horizon","metric","value"])
        w.writeheader(); w.writerows(out)
    return True

def main():
    changed = 0
    for y in [1995,2000,2005,2010]:
        p = V2 / f"FINAL_{y}" / "metrics_by_horizon.csv"
        if normalize(p): 
            print(f"[clean] {p}"); changed += 1
    print(f"[summary] cleaned={changed}")

if __name__ == "__main__":
    main()
