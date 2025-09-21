import csv, pathlib, math

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"
ENS  = ROOT / "ensemble"
ENS.mkdir(exist_ok=True, parents=True)

YEARS = [1995,2000,2005,2010]

def read_cov_overall(final_dir):
    p = final_dir / "coverage_overall.csv"
    out = {}
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lvl = (r.get("level","") or r.get("coverage","") or "").strip()
                emp = r.get("empirical","") or r.get("value","")
                try:
                    out[lvl] = float(emp)
                except:
                    pass
    return out

def read_metrics(final_dir):
    p = final_dir / "metrics_by_horizon.csv"
    rows = []
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(r)
    return rows

def main():
    outp = ENS / "stacking_features.csv"
    with outp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "year","horizons_count","cov50_err_pp","cov90_err_pp",
            "has_composite","composite_mean"
        ])
        for y in YEARS:
            d = V2 / f"FINAL_{y}"
            cov = read_cov_overall(d)
            cov50 = cov.get("0.5", cov.get("50%", float("nan")))
            cov90 = cov.get("0.9", cov.get("90%", float("nan")))
            cov50_err = abs((cov50 if cov50==cov50 else 0.5) - 0.5)*100.0
            cov90_err = abs((cov90 if cov90==cov90 else 0.9) - 0.9)*100.0

            met = read_metrics(d)
            comp = None
            for r in met:
                if (r.get("metric") == "composite_mean" and str(r.get("horizon")) == "1"):
                    try:
                        comp = float((r.get("value") or "").replace(",",".")) 
                    except:
                        pass
                    break
            w.writerow([y, len(met), f"{cov50_err:.2f}", f"{cov90_err:.2f}", "yes" if comp is not None else "no", "" if comp is None else f"{comp:.6f}"])
    print(f"[features] wrote {outp}")
if __name__ == "__main__":
    main()

