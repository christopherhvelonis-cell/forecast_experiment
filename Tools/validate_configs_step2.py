#!/usr/bin/env python
import argparse
from pathlib import Path
import yaml

REQUIRED_BASELINES = [
    "persistence", "linear_trend", "random_walk_drift",
    "ets_local_level", "equal_weight_combination"
]

def load_yaml(p):
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def normalize_indicators(obj):
    """
    Accept either:
      - {"indicators": [ ... ]}
      - [ ... ]   # top-level list
    Return list of indicator dicts.
    """
    if isinstance(obj, dict) and "indicators" in obj:
        lst = obj.get("indicators", [])
        return lst if isinstance(lst, list) else []
    if isinstance(obj, list):
        return obj
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", required=True)
    ap.add_argument("--baselines", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ind_cfg_raw = load_yaml(args.indicators)
    base_cfg = load_yaml(args.baselines)

    indicators = normalize_indicators(ind_cfg_raw)
    problems = []

    names = []
    for i, item in enumerate(indicators):
        if not isinstance(item, dict):
            problems.append(f"[indicators.yml] entry {i} is not a dict")
            continue
        name = item.get("name") or item.get("indicator") or f"<missing_name_{i}>"
        names.append(name)
        for k in ("transform","data_vintage_available","mode_changes","break_flags"):
            if k not in item:
                problems.append(f"[indicators.yml] {name}: missing \"{k}\"")

    present = list(base_cfg.keys()) if isinstance(base_cfg, dict) else []
    missing_baselines = [b for b in REQUIRED_BASELINES if b not in present]

    must_have = ["ba_plus_25plus_share", "trust_media_pct"]
    missing_used = [m for m in must_have if m not in names]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Step 2 Audit - Configs")
    lines.append("")
    lines.append(f"**Indicators file:** {args.indicators}")
    lines.append(f"**Baselines file:**  {args.baselines}")
    lines.append("")
    lines.append("## Indicators present")
    if names:
        for n in names:
            lines.append(f"- {n}")
    else:
        lines.append("(none found)")
    lines.append("")
    if missing_used:
        lines.append("## MISSING required indicators (used earlier)")
        for m in missing_used:
            lines.append(f"- {m}")
    else:
        lines.append("All required indicators used earlier are present (ba_plus_25plus_share, trust_media_pct).")
    lines.append("")
    if problems:
        lines.append("## Indicator field warnings")
        for p in problems:
            lines.append(f"- {p}")
    else:
        lines.append("No indicator field warnings detected (transform, data_vintage_available, mode_changes, break_flags present for each).")
    lines.append("")
    lines.append("## Baselines")
    lines.append(f"Present: {', '.join(present) if present else '(none)'}")
    if missing_baselines:
        lines.append("**Missing recommended baselines:** " + ", ".join(missing_baselines))
    else:
        lines.append("All recommended baselines found.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[validate_configs_step2] wrote {out_path}")

if __name__ == "__main__":
    main()
