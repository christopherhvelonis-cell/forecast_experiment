# Tools/validate_schema.py
import csv, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def must_exist(p: pathlib.Path):
    if not p.exists():
        print(f"[ERR] missing: {p}")
        return False
    return True

def check_headers(path: pathlib.Path, expected):
    if not must_exist(path): return False
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        try:
            hdr = next(r)
        except StopIteration:
            print(f"[ERR] empty file: {path}"); return False
    norm = [ (h or '').strip().lstrip('\ufeff').lower() for h in hdr ]
    ok = [c.lower() for c in expected] == norm
    if not ok:
        print(f"[ERR] bad header in {path.name}: {norm} != {expected}")
    else:
        print(f"[ok] {path.name} header")
    return ok

def read_gate(path: pathlib.Path):
    if not must_exist(path): return False
    ok = True
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rid = (row.get("id","") or "").strip()
            val = (row.get("ok","") or "").strip()
            if val.lower() not in ("true","1","yes"):
                print(f"[ERR] gate failed: {rid}")
                ok = False
    if ok: print("[ok] all acceptance checks passed")
    return ok

def main():
    good = True
    # global summaries
    good &= check_headers(V2 / "acceptance_gate_summary.csv",
                          ["id","group","description","ok","detail"])
    if (V2 / "acceptance_gate_threshold_summary.csv").exists():
        good &= check_headers(V2 / "acceptance_gate_threshold_summary.csv",
                              ["id","group","description","ok","detail"])
    good &= check_headers(V2 / "calibration_targets_summary.csv",
                          ["year","50_empirical","90_empirical","50_abs_err_pp","90_abs_err_pp","needs_conformal","has_points"])

    # per-year core files
    for y in (1995,2000,2005,2010):
        d = V2 / f"FINAL_{y}"
        good &= check_headers(d / "metrics_by_horizon.csv",
                              ["horizon","metric","value"])
        if (d / "crps_brier_summary.csv").exists():
            good &= check_headers(d / "crps_brier_summary.csv",
                                  ["stat","value"])
        if (d / "coverage_overall.csv").exists():
            # allow either "level,empirical" or "coverage,value" (normalize at read time)
            with (d / "coverage_overall.csv").open(encoding="utf-8", newline="") as f:
                hdr = [h.strip().lstrip('\ufeff').lower() for h in next(csv.reader(f))]
                if hdr not in (["level","empirical"], ["coverage","value"]):
                    print(f"[ERR] coverage_overall.csv header {hdr} not in expected options")
                    good = False
                else:
                    print(f"[ok] coverage_overall.csv header")
        # require composite_mean@h1 present
        comp_ok = False
        with (d / "metrics_by_horizon.csv").open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("horizon","").strip()=="1" and
                    r.get("metric","").strip()=="composite_mean" and
                    (r.get("value","") or "").strip()):
                    comp_ok = True; break
        if not comp_ok:
            print(f"[ERR] FINAL_{y} missing composite_mean@h1"); good = False

    # gate must be all green
    good &= read_gate(V2 / "acceptance_gate_summary.csv")
    sys.exit(0 if good else 2)

if __name__ == "__main__":
    main()
