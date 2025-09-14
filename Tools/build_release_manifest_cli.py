#!/usr/bin/env python
import argparse, hashlib, os, platform, subprocess, sys, time
from pathlib import Path

def sha256(fp):
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def get_py_version():
    return sys.version.replace("\n"," ")

def get_pip_freeze():
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return "(pip freeze unavailable)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="Git tag to record (e.g., v1995-a085)")
    ap.add_argument("--out_md", required=True, help="Output manifest path")
    args = ap.parse_args()

    root = Path(".").resolve()
    release = root / "release"
    release.mkdir(parents=True, exist_ok=True)

    files = []
    for p in sorted(release.glob("*")):
        if p.is_file():
            files.append((p.name, sha256(p)))

    pyver = get_py_version()
    pipf  = get_pip_freeze()

    # Repro commands (minimal core)
    repro = [
        r'python tools\ensemble_equal_cli.py --list_file configs\ensemble_models_1995.txt --out_csv eval\results\calibrated\FINAL_ensemble_1995_equal.csv',
        r'python verify_calibrated_cli.py --calibrated_csv eval\results\calibrated\FINAL_ensemble_1995_equal.csv --indicators ba_plus_25plus_share trust_media_pct --origin 1995 --h 15 --out_dir eval\results\diagnostics\FINAL_ensemble_1995_equal',
        r'python validation_nonUS\nonus_check_cli.py --final_calibrated_csv eval\results\calibrated\FINAL_hsm_chatgpt_1995.csv --proxy_csv validation_nonUS\proxies_japan_ba.csv --origin 1995 --out_dir validation_nonUS\out\Japan_ba_plus_25plus_share',
        r'python validation_nonUS\nonus_check_cli.py --final_calibrated_csv eval\results\calibrated\FINAL_hsm_chatgpt_1995.csv --proxy_csv validation_nonUS\proxies_brazil_tm.csv --origin 1995 --out_dir validation_nonUS\out\Brazil_trust_media_pct',
    ]

    lines = []
    lines.append(f"# Release Manifest — {args.tag}\n\n")
    lines.append(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
    lines.append(f"Platform: {platform.platform()}  \n")
    lines.append(f"Python: {pyver}\n\n")

    lines.append("## Files in `release/` (SHA256)\n\n")
    if files:
        lines.append("| file | sha256 |\n|:-----|:-------|\n")
        for name, h in files:
            lines.append(f"| {name} | `{h}` |\n")
        lines.append("\n")
    else:
        lines.append("_(no files found)_\n\n")

    lines.append("## Reproduction (core commands)\n\n")
    for cmd in repro:
        lines.append(f"- `{cmd}`\n")
    lines.append("\n")

    lines.append("## Seeds / Config Notes\n\n")
    lines.append("- Seeds: (record here if applicable)\n")
    lines.append("- Configs: `configs/ensemble_models_1995.txt` lists included models for the ensemble.\n\n")

    lines.append("## Library Versions (`pip freeze`)\n\n")
    lines.append("```\n" + pipf + "\n```\n")

    Path(args.out_md).write_text("".join(lines), encoding="utf-8")
    print(f"[release_manifest] wrote {args.out_md}")

if __name__ == "__main__":
    main()
