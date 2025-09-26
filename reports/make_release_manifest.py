#!/usr/bin/env python
# reports/make_release_manifest.py
from pathlib import Path, PurePosixPath
import hashlib, json
from datetime import datetime, timezone

ARTIFACTS = [
    "eval/results/retro_v2_postcal/metrics_1985.csv",
    "eval/results/retro_v2_postcal/metrics_1990.csv",
    "eval/results/retro_v2_postcal/metrics_2015.csv",
    "eval/results/retro_v2_postcal/metrics_2020.csv",
    "eval/results/significance_dm_prepost.csv",
    "eval/results/ensemble_retro_v2_postcal/metrics_ENSEMBLE.csv",
    "ensemble/results_fforma/summary_by_h_crps.csv",
    "ensemble/results_fforma/weights_by_h_median.csv",
    "reports/final_report.md",
    "README.md",
]

def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    repo = Path(".")
    artifacts = []
    for rel in ARTIFACTS:
        p = repo / rel
        if p.exists():
            artifacts.append({
                "file": str(PurePosixPath(rel)),
                "bytes": p.stat().st_size,
                "sha256": sha256_of(p),
            })
    manifest = {
        "tag": "v1.6-final",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git_commit": "",  # fill if desired
        "artifacts": artifacts,
    }
    out = repo / "reports" / "release_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("[ok] wrote reports/release_manifest.json")

if __name__ == "__main__":
    main()
