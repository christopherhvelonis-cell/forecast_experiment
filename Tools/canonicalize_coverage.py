# ==== Paths ====
$proj = "C:\Users\Owner\Downloads\forecast_experiment"
$py   = Join-Path $proj ".venv\Scripts\python.exe"

# ==== canonicalize_coverage.py (new) ====
$canon = @'
# Tools/canonicalize_coverage.py
# Standardizes coverage_overall.csv headers to "level,empirical".
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

YEARS = [1995,2000,2005,2010]

def normalize(path: pathlib.Path):
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    # Try to detect header style
    hdr = [h.strip().lstrip("\ufeff").lower() for h in rows[0]]
    outrows = []
    if hdr == ["level","empirical"] or hdr == ["coverage","value"]:
        return False  # already canonical/accepted
    if "indicator" in hdr and "cov50_overall" in hdr and "cov90_overall" in hdr:
        # Convert to rows of level,empirical
        for r in rows[1:]:
            if len(r) >= 3:
                outrows.append(["0.5", r[1]])
                outrows.append(["0.9", r[2]])
    elif "indicator" in hdr and "0.5" in hdr and "0.9" in hdr:
        for r in rows[1:]:
            if len(r) >= 3:
                outrows.append(["0.5", r[1]])
                outrows.append(["0.9", r[2]])
    else:
        print(f"[skip] {path} unrecognized header {hdr}")
        return False
    # Rewrite
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["level","empirical"])
        w.writerows(outrows)
    print(f"[canon] rewrote {path}")
    return True

def main():
    changed = 0
    for y in YEARS:
        p = V2 / f"FINAL_{y}" / "coverage_overall.csv"
        if normalize(p):
            changed += 1
    print(f"[summary] canonicalized={changed}")

if __name__ == "__main__":
    main()
'@
Set-Content -Encoding UTF8 -Path (Join-Path $proj "Tools\canonicalize_coverage.py") -Value $canon
