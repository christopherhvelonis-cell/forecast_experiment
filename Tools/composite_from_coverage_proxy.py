# Tools\composite_from_coverage_proxy.py
# Writes metric=composite_proxy at horizon=1 using coverage-only error (explicit proxy).
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def _norm_field(d, key):
    # handle BOM/whitespace in CSV headers
    for k in d.keys():
        if k.strip().lstrip("\ufeff").lower() == key:
            return d[k]
    return None

def read_cov(final_dir):
    p = final_dir / "coverage_overall.csv"
    lev = {}
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                k = _norm_field(r, "level") or _norm_field(r, "coverage") or ""
                k = (k or "").strip()
                v = _norm_field(r, "empirical") or _norm_field(r, "value") or ""
                try:
                    lev[k] = float(str(v).replace(",","."))  # tolerate comma decimals
                except:
                    pass
    return lev

def read_metrics(final_dir):
    p = final_dir / "metrics_by_horizon.csv"
    rows = []
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows

def write_metric(final_dir, metric, value):
    p = final_dir / "metrics_by_horizon.csv"
    rows = read_metrics(final_dir)

    # normalize header names per row and drop existing metric@h1
    norm = []
    for r in rows:
        h = (_norm_field(r, "horizon") or "").strip()
        m = (_norm_field(r, "metric")  or "").strip()
        v = (_norm_field(r, "value")   or "").strip()
        if not (h == "1" and m == metric):
            norm.append({"horizon": h, "metric": m, "value": v})

    # append our proxy row (force horizon=1)
    norm.append({"horizon": "1", "metric": metric, "value": f"{float(value):.6f}"})

    # write back cleanly
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["horizon","metric","value"])
        w.writeheader()
        w.writerows(norm)

def main():
    for y in [1995,2000,2005,2010]:
        d = V2 / f"FINAL_{y}"
        if not d.exists():
            print(f"[skip] {y} no dir"); 
            continue
        cov = read_cov(d)
        c50 = cov.get("0.5", 0.5)
        c90 = cov.get("0.9", 0.9)
        proxy = 0.5 * (2.0*abs(c50-0.5)) + 0.5 * (abs(c90-0.9)/0.9)
        write_metric(d, "composite_proxy", proxy)
        print(f"[proxy] {y} composite_proxy={proxy:.6f}")

if __name__ == "__main__":
    main()
