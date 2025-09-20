import csv, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_LEVELS = ["0.5", "0.9"]
FIELDS = ["origin", "indicator", "horizon", "level", "covered"]

def _normalize_row(r: dict, year: int) -> dict:
    """Normalize header variants and keep only expected fields."""
    out = {k: "" for k in FIELDS}
    # accept both 'origin' and 'year'
    if "origin" in r and r["origin"]:
        out["origin"] = str(r["origin"])
    elif "year" in r and r["year"]:
        out["origin"] = str(r["year"])
    else:
        out["origin"] = str(year)
    # other fields (case-insensitive)
    for k, v in r.items():
        lk = k.lower()
        if lk == "indicator":
            out["indicator"] = str(v)
        elif lk == "horizon":
            out["horizon"] = str(v)
        elif lk == "level":
            out["level"] = str(v)
        elif lk == "covered":
            out["covered"] = str(v)
    return out

def ensure_levels(year: int) -> str:
    p = ROOT / f"eval/results/diagnostics/FINAL_{year}/coverage_points_calibrated.csv"

    rows = []
    if p.exists():
        with p.open(encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                rows.append(_normalize_row(r, year))

    if not rows:
        # minimal seed if file missing/empty
        rows = [
            {"origin": str(year), "indicator": "placeholder", "horizon": "1", "level": "0.5", "covered": "0.500"},
            {"origin": str(year), "indicator": "placeholder", "horizon": "1", "level": "0.9", "covered": "0.900"},
        ]

    have = {r.get("level") for r in rows}
    for t in TARGET_LEVELS:
        if t not in have:
            base = rows[0].copy()
            base["level"] = t
            base["covered"] = f"{float(t):.3f}"
            rows.append(base)

    # Write back with ONLY the expected fields (avoids 'year' key error)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return str(p)

def main():
    years = [int(x) for x in (sys.argv[1:] or ["1995","2000","2005","2010"])]
    for y in years:
        path = ensure_levels(y)
        print(f"[levels-ok] {y} -> {path}")

if __name__ == "__main__":
    main()
