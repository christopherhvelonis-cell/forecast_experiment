# Tools/compute_composite_from_summaries.py
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def read_stats(final_dir):
    p = final_dir / "crps_brier_summary.csv"
    out = {}
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = (r.get("stat","") or "").strip().lower()
                v = (r.get("value","") or "").replace(",",".")
                try: out[k] = float(v)
                except: pass
    return out

def write_metric(final_dir, metric, value):
    p = final_dir / "metrics_by_horizon.csv"
    rows = []
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    # normalize + drop existing metric@h1
    norm = []
    for r in rows:
        h = (r.get("horizon","") or "").strip()
        m = (r.get("metric","")  or "").strip()
        v = (r.get("value","")   or "").strip()
        if not (h=="1" and m==metric):
            norm.append({"horizon": h, "metric": m, "value": v})
    norm.append({"horizon":"1","metric":metric,"value":f"{float(value):.6f}"})
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["horizon","metric","value"]); w.writeheader(); w.writerows(norm)

def main():
    for y in [1995,2000,2005,2010]:
        d = V2 / f"FINAL_{y}"
        if not d.exists():
            print(f"[skip] {y} no dir"); continue
        s = read_stats(d)
        crps  = s.get("crps_mean")
        brier = s.get("brier_mean")
        if crps is not None and brier is not None:
            comp = 0.5*crps + 0.5*brier
            src = "crps+brier"
        elif crps is not None:
            comp = crps; src = "crps"
        elif brier is not None:
            comp = brier; src = "brier"
        else:
            print(f"[warn] {y} no crps/brier stats, leaving existing composite_mean"); continue
        write_metric(d, "composite_mean", comp)
        print(f"[composite] {y}: {comp:.6f} ({src})")

if __name__ == "__main__":
    main()
