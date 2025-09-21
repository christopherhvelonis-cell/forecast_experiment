# Tools/make_mini_report.py
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"
OUT  = ROOT / "REPORT.md"

def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rdr = csv.reader(f)
        rows = list(rdr)
        if not rows:
            return []
        # normalize headers: strip + remove BOM + lowercase
        headers = [ (h or "").strip().lstrip("\ufeff").lower() for h in rows[0] ]
        out = []
        for r in rows[1:]:
            d = {}
            for i, v in enumerate(r):
                key = headers[i] if i < len(headers) else f"col{i}"
                d[key] = v
            out.append(d)
        return out

def table(rows, cols):
    if not rows:
        return "_(none)_\n"
    # map with header fallback (handles slightly different fieldnames)
    def get(r, k):
        lk = k.lower()
        for kk,v in r.items():
            if kk.strip().lower() == lk:
                return str(v)
        return ""
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"]*len(cols)) + " |")
    for r in rows:
        lines.append("| " + " | ".join(get(r,c) for c in cols) + " |")
    return "\n".join(lines) + "\n"

ag  = read_csv(V2 / "acceptance_gate_summary.csv")
agt = read_csv(V2 / "acceptance_gate_threshold_summary.csv")
cal = read_csv(V2 / "calibration_targets_summary.csv")

with OUT.open("w", encoding="utf-8") as f:
    f.write("# Forecast Experiment - Mini Report\n\n")
    f.write("## Acceptance Gate (real composite)\n\n")
    f.write(table(ag,  ["id","group","description","ok","detail"]))
    f.write("\n## Acceptance Gate (thresholded composite)\n\n")
    # use ASCII "<=" in description to avoid console glyph issues
    for r in agt:
        if "description" in r and "≤" in r["description"]:
            r["description"] = r["description"].replace("≤", "<=")
    f.write(table(agt, ["id","group","description","ok","detail"]))
    f.write("\n## Calibration Targets Summary\n\n")
    f.write(table(cal, ["year","50_empirical","90_empirical","50_abs_err_pp","90_abs_err_pp","needs_conformal","has_points"]))

print(f"[report] wrote {OUT}")
