# Tools/make_crps_brier_from_losses.py
# Purpose: derive a CRPS-like proxy from loss_differences.csv and emit
#          eval/results/v2/FINAL_YYYY/crps_brier_summary.csv as:
#          stat,value
#          crps_mean,<float>
#          brier_mean,<float or blank>
#
# Notes:
# - Uses mean(loss50_abs_error) as a simple CRPS proxy. If loss90_abs_error exists,
#   we blend: crps_proxy = 0.75*mean(loss50_abs_error) + 0.25*mean(loss90_abs_error)
#   (a coarse trapezoid over a sparse set of quantiles).
# - We leave brier_mean blank unless a usable column is found.

import csv, pathlib, math

ROOT = pathlib.Path(__file__).resolve().parents[1]
V2   = ROOT / "eval" / "results" / "v2"

YEARS = [1995,2000,2005,2010]

def read_losses(final_dir):
    p = final_dir / "loss_differences.csv"
    rows = []
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows

def to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return math.nan

def mean_safe(vals):
    vals = [v for v in vals if isinstance(v, (int, float)) and v == v]
    if not vals: return math.nan
    return sum(vals) / len(vals)

def write_stat_value_file(final_dir, stats):
    p = final_dir / "crps_brier_summary.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stat","value"])
        for k in ["crps_mean","brier_mean"]:
            v = stats.get(k, "")
            if v == v and v is not None and v != "":
                w.writerow([k, f"{float(v):.6f}"])
            else:
                w.writerow([k, ""])
    return p

def main():
    for y in YEARS:
        d = V2 / f"FINAL_{y}"
        if not d.exists():
            print(f"[skip] {y} no dir")
            continue
        rows = read_losses(d)
        if not rows:
            print(f"[warn] {y} loss_differences.csv missing or empty")
            continue

        l50 = []
        l90 = []
        briers = []

        for r in rows:
            # normalize keys
            r_norm = { (k or "").strip().lstrip("\ufeff").lower(): v for k, v in r.items() }
            if "loss50_abs_error" in r_norm:
                l50.append(to_float(r_norm["loss50_abs_error"]))
            if "loss90_abs_error" in r_norm:
                l90.append(to_float(r_norm["loss90_abs_error"]))
            # if any brier-like column exists, collect it (rare in current data)
            for cand in ("brier","brier_mean","brier_score"):
                if cand in r_norm:
                    briers.append(to_float(r_norm[cand]))

        m50 = mean_safe(l50)
        m90 = mean_safe(l90)

        # CRPS proxy (weighted blend if we have l90; else just l50)
        if m50 == m50 and m90 == m90:
            crps_proxy = 0.75*m50 + 0.25*m90
            src = "loss50+loss90"
        elif m50 == m50:
            crps_proxy = m50
            src = "loss50"
        elif m90 == m90:
            crps_proxy = m90
            src = "loss90"
        else:
            print(f"[warn] {y} no usable loss columns for CRPS proxy")
            continue

        # Optional brier if we found any
        brier_mean = mean_safe(briers)
        if not (brier_mean == brier_mean):  # NaN -> leave blank
            brier_mean = ""

        outp = write_stat_value_file(d, {"crps_mean": crps_proxy, "brier_mean": brier_mean})
        print(f"[stats] {y} -> crps_mean={crps_proxy:.6f} ({src}); brier_mean={'(blank)' if brier_mean=='' else f'{brier_mean:.6f}'} | wrote {outp}")

if __name__ == "__main__":
    main()
