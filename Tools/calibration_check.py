import sys, json, csv, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_COVS = [0.50, 0.90]

def read_coverage_points(p):
    if not p.exists():
        return []
    rows = []
    with p.open(encoding="utf-8") as f:
        R = csv.DictReader(f)
        for r in R:
            try:
                rows.append({
                    "origin": int(r.get("origin", 0)),
                    "level": float(r.get("level")),
                    "covered": float(r.get("covered")),
                })
            except Exception:
                pass
    return rows

def summarize_for_year(year):
    diag = ROOT / f"eval/results/diagnostics/FINAL_{year}/coverage_points_calibrated.csv"
    rows = read_coverage_points(diag)

    out = {
        "year": year,
        "has_points": bool(rows),
        "targets": TARGET_COVS,
        "empirical": {},
        "abs_error_pp": {},
        "needs_conformal": False,
        "notes": "",
    }
    if not rows:
        out["notes"] = "no diagnostics coverage file"
        return out

    by_level = defaultdict(list)
    for r in rows:
        by_level[r["level"]].append(r["covered"])
    for lvl in TARGET_COVS:
        vals = by_level.get(lvl, [])
        emp = sum(vals)/len(vals) if vals else None
        out["empirical"][lvl] = emp
        if emp is None:
            out["abs_error_pp"][lvl] = None
        else:
            out["abs_error_pp"][lvl] = abs(emp - lvl) * 100.0

    miss = [v for v in out["abs_error_pp"].values() if v is not None and v > 5.0]
    out["needs_conformal"] = len(miss) > 0
    return out

def main():
    years = [int(x) for x in (sys.argv[1:] or ["1995","2000","2005","2010"])]
    rep_dir = ROOT / "eval" / "results" / "v2"
    rep_dir.mkdir(parents=True, exist_ok=True)
    table_rows = []
    jblob = []
    for y in years:
        s = summarize_for_year(y)
        jblob.append(s)
        row = {
            "year": y,
            "50_empirical": "{:.3f}".format(s["empirical"].get(0.50, float("nan"))) if s["empirical"].get(0.50) is not None else "",
            "90_empirical": "{:.3f}".format(s["empirical"].get(0.90, float("nan"))) if s["empirical"].get(0.90) is not None else "",
            "50_abs_err_pp": "{:.2f}".format(s["abs_error_pp"].get(0.50, float("nan"))) if s["abs_error_pp"].get(0.50) is not None else "",
            "90_abs_err_pp": "{:.2f}".format(s["abs_error_pp"].get(0.90, float("nan"))) if s["abs_error_pp"].get(0.90) is not None else "",
            "needs_conformal": "yes" if s["needs_conformal"] else "no",
            "has_points": "yes" if s["has_points"] else "no",
        }
        table_rows.append(row)

    csv_path = rep_dir / "calibration_targets_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
        w.writeheader()
        w.writerows(table_rows)

    (rep_dir / "calibration_targets_summary.json").write_text(json.dumps(jblob, indent=2), encoding="utf-8")

    print("[calibration] wrote", csv_path)
    for r in table_rows:
        print(r)

if __name__ == "__main__":
    main()
