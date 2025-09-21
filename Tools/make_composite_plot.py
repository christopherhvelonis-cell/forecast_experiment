# Tools/make_composite_plot.py
import csv, pathlib
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"
OUT  = ROOT / "fig_composite_by_year.png"

def read_comp(y):
    p = V2 / f"FINAL_{y}" / "metrics_by_horizon.csv"
    if not p.exists(): return None
    with p.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if (r.get("horizon","").strip()=="1" and r.get("metric","").strip()=="composite_mean"):
                try: return float(str(r.get("value","")).replace(",",".")) 
                except: return None
    return None

years = [1995,2000,2005,2010]
vals  = [read_comp(y) for y in years]

plt.figure()
plt.bar([str(y) for y in years], vals)
plt.title("Composite Mean by Year")
plt.xlabel("Year"); plt.ylabel("Composite Mean")
plt.tight_layout()
plt.savefig(OUT, dpi=150)
print(f"[plot] wrote {OUT}")
