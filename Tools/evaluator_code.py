import csv, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def read_summary(final_dir):
    p = final_dir / "crps_brier_summary.csv"
    stats = {}
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = (r.get("stat") or "").strip()
                v = (r.get("value") or "").strip()
                if k:
                    try: stats[k] = float(v)
                    except: pass
    return stats

def write_metrics_by_horizon(final_dir, composite):
    out = final_dir / "metrics_by_horizon.csv"
    rows = []
    if out.exists():
        with out.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    # keep any existing rows, but ensure one composite_mean at horizon=1
    keep = [r for r in rows if not (r.get("horizon")=="1" and r.get("metric")=="composite_mean")]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["horizon","metric","value"])
        w.writeheader()
        w.writerows(keep)
        w.writerow({"horizon":"1","metric":"composite_mean","value":f"{composite:.6f}"})
    return out

def main(years):
    for y in years:
        d = V2 / f"FINAL_{y}"
        if not d.exists():
            print(f"[skip] {y} -> dir missing: {d}")
            continue
        s = read_summary(d)
        crps  = s.get("crps_mean", float("nan"))
        brier = s.get("brier_mean", float("nan"))
        if crps == crps and brier == brier:
            composite = 0.5*crps + 0.5*brier
        elif crps == crps:
            composite = crps
        elif brier == brier:
            composite = brier
        else:
            print(f"[warn] {y} -> no stats in crps_brier_summary.csv")
            continue
        p = write_metrics_by_horizon(d, composite)
        print(f"[evaluator] {y} -> {p}")

if __name__ == "__main__":
    years = [int(x) for x in sys.argv[1:]] or [1995,2000,2005,2010]
    main(years)
