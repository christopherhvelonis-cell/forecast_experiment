# Tools/make_release_bundle.py
import pathlib, zipfile, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTD = ROOT / "release"
OUTD.mkdir(exist_ok=True)
stamp = time.strftime("%Y%m%d-%H%M%S")
zip_path = OUTD / f"forecast_experiment_preview_{stamp}.zip"

keep_rel = [
    "REPORT.md",
    "fig_composite_by_year.png",
    "eval/results/v2/acceptance_gate_summary.csv",
    "eval/results/v2/acceptance_gate_threshold_summary.csv",
    "eval/results/v2/calibration_targets_summary.csv",
]
# Include per-year FINAL_* dirs
for y in (1995,2000,2005,2010):
    for fn in ["metrics_by_horizon.csv","crps_brier_summary.csv","coverage_overall.csv"]:
        keep_rel.append(f"eval/results/v2/FINAL_{y}/{fn}")

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for rel in keep_rel:
        p = ROOT / rel
        if p.exists():
            z.write(p, arcname=rel)
print(f"[bundle] wrote {zip_path}")
