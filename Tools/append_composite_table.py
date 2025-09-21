# Tools/append_composite_table.py
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"
OUT  = ROOT / "REPORT.md"

def get_composite(y):
    p = V2 / f"FINAL_{y}" / "metrics_by_horizon.csv"
    if not p.exists(): return None
    with p.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            h = (r.get("horizon","") or "").strip()
            m = (r.get("metric","")  or "").strip()
            v = (r.get("value","")   or "").strip().replace(",",".")
            if h == "1" and m == "composite_mean":
                try: return float(v)
                except: return None
    return None

rows = []
for y in [1995,2000,2005,2010]:
    c = get_composite(y)
    rows.append((y, "" if c is None else f"{c:.6f}"))

# Append section (idempotent: removes any previous section with same header)
text = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
marker = "## Composite Mean by Year"
parts = text.split(marker, 1)
if len(parts) > 1:
    # keep everything before header; drop old section
    text = parts[0].rstrip() + "\n"

table = ["", marker, "", "| year | composite_mean |",
         "| --- | --- |"] + [f"| {y} | {v} |" for y,v in rows] + [""]

OUT.write_text(text + "\n".join(table) + "\n", encoding="utf-8")
print(f"[report] appended composite table -> {OUT}")
