import csv, sys, pathlib

EXPECTED = ["indicator","horizon","covered_50_rate","covered_90_rate","loss50_abs_error","loss90_abs_error"]

# Resolve repo root as the parent of this script's directory (Tools/)
REPO = pathlib.Path(__file__).resolve().parents[1]

def fix_one(path: pathlib.Path):
    if not path.exists():
        return False, f"missing: {path}"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # map source headers -> expected (case/variant tolerant)
    def keymap(keys):
        km = {}
        for k in keys:
            lk = k.lower().strip()
            if lk == "indicator": km[k] = "indicator"
            elif lk == "horizon": km[k] = "horizon"
            elif "cover" in lk and "50" in lk: km[k] = "covered_50_rate"
            elif "cover" in lk and "90" in lk: km[k] = "covered_90_rate"
            elif ("loss" in lk or "abs" in lk) and "50" in lk: km[k] = "loss50_abs_error"
            elif ("loss" in lk or "abs" in lk) and "90" in lk: km[k] = "loss90_abs_error"
            else: km[k] = None
        return km

    src_keys = rows[0].keys() if rows else EXPECTED
    km = keymap(src_keys)

    fixed = []
    for r in rows:
        out = {c: "" for c in EXPECTED}
        for k, v in r.items():
            t = km.get(k)
            if t in out:
                out[t] = v
        fixed.append(out)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPECTED)
        w.writeheader()
        w.writerows(fixed)

    return True, f"fixed: {path}"

if __name__ == "__main__":
    years = sys.argv[1:] or ["1995"]
    for y in years:
        p = REPO / f"eval/results/v2/FINAL_{y}/loss_differences.csv"
        ok, msg = fix_one(p)
        print(("[ok]" if ok else "[skip]"), y, "-", msg)
