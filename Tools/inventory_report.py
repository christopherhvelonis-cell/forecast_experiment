#!/usr/bin/env python3
"""
Tools/inventory_report.py

Scan the forecast_experiment repo and produce:
  - reports/INVENTORY.md       (human-readable)
  - reports/inventory_summary.json (machine-readable)

It verifies expected folders, lists key files, summarizes eval/results artifacts
(models, indicators, horizons, origin_years), and flags missing-but-expected items.

Run:
  python Tools/inventory_report.py
"""

from __future__ import annotations
import os, sys, glob, json, re, datetime
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES  = os.path.join(ROOT, "eval", "results")
REPORTS = os.path.join(ROOT, "reports")

EXPECTED_DIRS = [
    "data/raw", "data/processed", "data/docsheets",
    "models/HSM_chatgpt", "models/FSM_chatgpt",
    "models/HSM_grok", "models/FSM_grok",
    "eval/metrics", "eval/results", "eval/holdouts",
    "validation_nonUS", "bias_logs", "ensemble", "reports", "configs", "Tools"
]

EXPECTED_FILES_OPTIONAL = [
    "configs/experiment.yml",
    "configs/scoring.yml",
    "configs/indicators.yml",
    "configs/baselines.yml",
    "data/vintages.md",
    "data/revisions.md",
    "Tools/run_step_15_learn_ensemble.py",
    "Tools/run_step_15_apply_weights.py",
    "Tools/make_stacking_features_from_perf.py",
    "Tools/discover_make_perf.py",
    "Tools/make_perf_from_struct_quantiles.py",
    "eval/evaluator_code.py",
    "Tools/acceptance_gate.ps1",
    "Tools/make_mini_report.py",
    "Tools/make_release_bundle.py",
    "Tools/clean_metrics_files.py",
    "Tools/compute_composite_from_summaries.py",
    "Tools/make_composite_plot.py",
    "Tools/canonicalize_coverage.py",
    "Tools/validate_schema.py",
]

RESULT_FILE_HINTS = {
    "perf_by_model": os.path.join(RES, "perf_by_model.csv"),
    "stacking_features": os.path.join(RES, "stacking_features.csv"),
    "quantiles_by_model": os.path.join(RES, "quantiles_by_model.csv"),
    "event_probs_by_model": os.path.join(RES, "event_probs_by_model.csv"),
    "realized_by_origin": os.path.join(RES, "realized_by_origin.csv"),
}

def exists(relpath: str) -> bool:
    return os.path.exists(os.path.join(ROOT, relpath))

def list_struct_files():
    return sorted(glob.glob(os.path.join(RES, "*_struct_*.csv")))

def parse_model_year(path):
    base = os.path.basename(path).lower()
    m = re.match(r"(.+?)_struct_(\d{4})\.csv$", base)
    if m:
        return m.group(1), int(m.group(2))
    return None, None

def safe_read_csv(path, nrows=None):
    try:
        return pd.read_csv(path, nrows=nrows)
    except Exception:
        return None

def summarize_eval_results():
    summary = {
        "struct_files": [],
        "models": set(),
        "origin_years": set(),
        "indicators": set(),
        "horizons": set(),
        "files_present": {},
        "files_missing": [],
    }

    # Presence of standard result files
    for key, path in RESULT_FILE_HINTS.items():
        summary["files_present"][key] = os.path.exists(path)

    # Scan *_struct_*.csv
    for f in list_struct_files():
        model, oy = parse_model_year(f)
        if model is None: 
            continue
        df = safe_read_csv(f)
        if df is None or df.empty:
            continue

        need = {"indicator", "horizon"}
        if not need.issubset(df.columns):
            continue

        inds = set(map(str, df["indicator"].dropna().unique()))
        hzs = set(int(h) for h in df["horizon"].dropna().astype(int).unique())

        summary["struct_files"].append({
            "path": os.path.relpath(f, ROOT),
            "model": model,
            "origin_year": oy,
            "indicators_count": len(inds),
            "horizons_count": len(hzs)
        })
        summary["models"].add(model)
        if oy is not None:
            summary["origin_years"].add(int(oy))
        summary["indicators"].update(inds)
        summary["horizons"].update(hzs)

    # Convert sets to sorted lists
    summary["models"] = sorted(summary["models"])
    summary["origin_years"] = sorted(summary["origin_years"])
    summary["indicators"] = sorted(summary["indicators"])
    summary["horizons"] = sorted(summary["horizons"])
    return summary

def check_expected_tree():
    present_dirs, missing_dirs = [], []
    for d in EXPECTED_DIRS:
        (present_dirs if exists(d) else missing_dirs).append(d)

    present_files, missing_files = [], []
    for f in EXPECTED_FILES_OPTIONAL:
        (present_files if exists(f) else missing_files).append(f)

    return {
        "present_dirs": present_dirs, "missing_dirs": missing_dirs,
        "present_files": present_files, "missing_files": missing_files
    }

def main():
    os.makedirs(REPORTS, exist_ok=True)

    tree = check_expected_tree()
    eval_summ = summarize_eval_results()

    # If perf_by_model is present, get quick shape + head columns
    perf_info = {}
    ppath = RESULT_FILE_HINTS["perf_by_model"]
    if os.path.exists(ppath):
        df = safe_read_csv(ppath, nrows=5)
        perf_info = {
            "path": os.path.relpath(ppath, ROOT),
            "head_columns": list(df.columns) if df is not None else None
        }

    # If stacking_features present, capture feature columns
    feats_info = {}
    fpath = RESULT_FILE_HINTS["stacking_features"]
    if os.path.exists(fpath):
        df = safe_read_csv(fpath, nrows=5)
        feats_info = {
            "path": os.path.relpath(fpath, ROOT),
            "head_columns": list(df.columns) if df is not None else None
        }

    # Prepare JSON summary
    summary = {
        "generated_at_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "root": ROOT,
        "tree": tree,
        "eval_results": eval_summ,
        "perf_by_model": perf_info,
        "stacking_features": feats_info,
        "standard_files_present": RESULT_FILE_HINTS,
    }

    json_out = os.path.join(REPORTS, "inventory_summary.json")
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Build Markdown
    md_lines = []
    md_lines.append("# Inventory Report")
    md_lines.append(f"_Generated (UTC)_: {summary['generated_at_utc']}")
    md_lines.append("")
    md_lines.append("## Folder Tree Check")
    md_lines.append("**Present dirs:**")
    for d in tree["present_dirs"]:
        md_lines.append(f"- [x] `{d}`")
    if tree["missing_dirs"]:
        md_lines.append("")
        md_lines.append("**Missing dirs:**")
        for d in tree["missing_dirs"]:
            md_lines.append(f"- [ ] `{d}`")

    md_lines.append("")
    md_lines.append("## Key Files")
    md_lines.append("**Present files:**")
    for f in tree["present_files"]:
        md_lines.append(f"- [x] `{f}`")
    if tree["missing_files"]:
        md_lines.append("")
        md_lines.append("**Missing files (optional/expected):**")
        for f in tree["missing_files"]:
            md_lines.append(f"- [ ] `{f}`")

    md_lines.append("")
    md_lines.append("## eval/results Summary")
    md_lines.append(f"- Models discovered: `{', '.join(eval_summ['models']) or '—'}`")
    md_lines.append(f"- Origin years: `{', '.join(map(str, eval_summ['origin_years'])) or '—'}`")
    md_lines.append(f"- Indicators (unique): `{len(eval_summ['indicators'])}`")
    md_lines.append(f"- Horizons (unique): `{len(eval_summ['horizons'])}`")
    md_lines.append("")
    md_lines.append("### Struct files")
    if eval_summ["struct_files"]:
        for s in eval_summ["struct_files"]:
            md_lines.append(f"- `{s['path']}`  (model=`{s['model']}`, origin_year=`{s['origin_year']}`, "
                            f"indicators={s['indicators_count']}, horizons={s['horizons_count']})")
    else:
        md_lines.append("- _None found_")

    md_lines.append("")
    md_lines.append("### Standard Result Files")
    for key, path in RESULT_FILE_HINTS.items():
        status = "present" if os.path.exists(path) else "missing"
        md_lines.append(f"- `{os.path.relpath(path, ROOT)}` → **{status}**")

    if perf_info:
        md_lines.append("")
        md_lines.append("### perf_by_model.csv (peek)")
        md_lines.append(f"- Path: `{perf_info['path']}`")
        md_lines.append(f"- Columns: `{', '.join(perf_info.get('head_columns') or [])}`")

    if feats_info:
        md_lines.append("")
        md_lines.append("### stacking_features.csv (peek)")
        md_lines.append(f"- Path: `{feats_info['path']}`")
        md_lines.append(f"- Columns: `{', '.join(feats_info.get('head_columns') or [])}`")

    md_lines.append("")
    md_lines.append("## Next Minimal Actions (if continuing Step 15)")
    if not os.path.exists(RESULT_FILE_HINTS["perf_by_model"]):
        md_lines.append("- Build `eval/results/perf_by_model.csv` (from evaluator or from struct+truth helper).")
    if not os.path.exists(RESULT_FILE_HINTS["stacking_features"]):
        md_lines.append("- Generate `eval/results/stacking_features.csv` from `perf_by_model.csv`.")
    md_lines.append("- If weights not present: run `Tools/run_step_15_learn_ensemble.py` once perf/features exist.")
    md_lines.append("- Then apply weights via `Tools/run_step_15_apply_weights.py` and re-score.")

    md = "\n".join(md_lines)
    os.makedirs(REPORTS, exist_ok=True)
    md_path = os.path.join(REPORTS, "INVENTORY.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[ok] Wrote {os.path.relpath(md_path, ROOT)}")
    print(f"[ok] Wrote {os.path.relpath(json_out, ROOT)}")

if __name__ == "__main__":
    sys.exit(main())
