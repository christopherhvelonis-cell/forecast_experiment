# Tools/validate_schema.py
import csv, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

def _norm(h: str) -> str:
    return (h or "").strip().lstrip("\ufeff").strip('"').strip("'").lower()

def must_exist(p: pathlib.Path):
    if not p.exists():
        print(f"[ERR] missing: {p}")
        return False
    return True

def check_headers(path: pathlib.Path, expected, order_matters=False):
    """
    expected: list of expected header names (normalized)
    order_matters=False -> treat as a superset check (all expected must be present, any order)
    """
    if not must_exist(path): return False
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        try:
            hdr = next(r)
        except StopIteration:
            print(f"[ERR] empty file: {path}"); return False
    norm = [_norm(h) for h in hdr]
    exp  = [_norm(c) for c in expected]
    ok = (norm == exp) if order_matters else set(exp).issubset(set(norm))
    if not ok:
        print(f"[ERR] bad header in {path.name}: {norm} vs expected(s) {exp}")
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

def coverage_header_ok(path: pathlib.Path) -> bool:
    if not must_exist(path): return False
    with path.open(encoding="utf-8", newline="") as f:
        try:
            hdr = [ _norm(h) for h in next(csv.reader(f)) ]
        except StopIteration:
            print(f"[ERR] empty file: {path}"); return False
    # allow several known shapes
    allowed = [
        ["indicator","cov50_overall","cov90_overall"],
        ["indicator","0.5","0.9"],
        ["level","empirical"],
        ["coverage","value"],
    ]
    for alt in allowed:
        if set(alt).issubset(set(hdr)):  # superset check
            print(f"[ok] {path.name} header ({alt} accepted)")
            return True
    print(f"[ERR] {path.name} header {hdr} not in expected options")
    return False

def main():
    good = True
    # global summaries (order doesn’t matter)
    good &= check_headers(V2 / "acceptance_gate_summary.csv",
                          ["id","group","description","ok","detail"], order_matters=False)
    if (V2 / "acceptance_gate_threshold_summary.csv").exists():
        good &= check_headers(V2 / "acceptance_gate_threshold_summary.csv",
                              ["id","group","description","ok","detail"], order_matters=False)
    good &= check_headers(V2 / "calibration_targets_summary.csv",
                          ["year","50_empirical","90_empirical","50_abs_err_pp","90_abs_err_pp","needs_conformal","has_points"],
                          order_matters=False)

    # per-year core files
    for y in (1995,2000,2005,2010):
        d = V2 / f"FINAL_{y}"
        good &= check_headers(d / "metrics_by_horizon.csv",
                              ["horizon","metric","value"], order_matters=False)
        if (d / "crps_brier_summary.csv").exists():
            good &= check_headers(d / "crps_brier_summary.csv",
                                  ["stat","value"], order_matters=False)
        if (d / "coverage_overall.csv").exists():
            good &= coverage_header_ok(d / "coverage_overall.csv")

        # require composite_mean@h1 present
        comp_ok = False
        with (d / "metrics_by_horizon.csv").open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if (_norm(r.get("horizon",""))=="1" and
                    _norm(r.get("metric",""))=="composite_mean" and
                    (r.get("value","") or "").strip()):
                    comp_ok = True; break
        if not comp_ok:
            print(f"[ERR] FINAL_{y} missing composite_mean@h1"); good = False

    # ensure gate is all green
    good &= read_gate(V2 / "acceptance_gate_summary.csv")
    sys.exit(0 if good else 2)

if __name__ == "__main__":
    main()
