import csv, pathlib
p = pathlib.Path(r"eval/results/v2/FINAL_1995/loss_differences.csv")
if not p.exists():
    raise SystemExit("missing file: {}".format(p))
EXPECTED = ["indicator","horizon","covered_50_rate","covered_90_rate","loss50_abs_error","loss90_abs_error"]
with p.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
out = []
for r in rows:
    out.append({k: r.get(k,"") for k in EXPECTED})
with p.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=EXPECTED)
    w.writeheader()
    w.writerows(out)
print("[rewrite] wrote", p)
