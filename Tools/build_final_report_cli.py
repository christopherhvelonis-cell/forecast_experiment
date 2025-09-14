#!/usr/bin/env python
import argparse, os, pandas as pd

def read_csv_safe(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return None

def section_header(title, level=2):
    return f"{'#'*level} {title}\n\n"

def df_to_md(df, max_rows=None):
    if df is None or df.empty: return "_(no data)_\n\n"
    d = df if max_rows is None else df.head(max_rows)
    return d.to_markdown(index=False) + "\n\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_md", required=True)
    args = ap.parse_args()

    # Known file locations
    paths = {
        "single_model_cov": r"eval\results\diagnostics\FINAL_1995_a085\coverage_summary_calibrated.csv",
        "ensemble_cov":     r"eval\results\diagnostics\FINAL_ensemble_1995_equal\coverage_summary_calibrated.csv",
        "nonus_japan":      r"validation_nonUS\out\Japan_ba_plus_25plus_share\coverage_summary_nonUS.csv",
        "nonus_brazil":     r"validation_nonUS\out\Brazil_trust_media_pct\coverage_summary_nonUS.csv",
        "overlap":          r"reports\scenarios\overlap_matrix.csv",
    }

    sm = read_csv_safe(paths["single_model_cov"])
    en = read_csv_safe(paths["ensemble_cov"])
    jp = read_csv_safe(paths["nonus_japan"])
    br = read_csv_safe(paths["nonus_brazil"])
    ov = read_csv_safe(paths["overlap"])

    out = []
    out.append("# Final Report (Origin 1995)\n\n")
    out.append("Artifacts: `release/FINAL_hsm_chatgpt_1995.csv`, `release/FINAL_ensemble_1995_equal.csv`.\n\n")

    out.append(section_header("Coverage — Single Model (BA a221 + TM α=0.85)"))
    out.append(df_to_md(sm))

    out.append(section_header("Coverage — Ensemble (Equal Weight)"))
    out.append(df_to_md(en))

    out.append(section_header("Non-US Validation (Proxies)"))
    out.append("**Japan (BA proxy):**\n\n")
    out.append(df_to_md(jp))
    out.append("**Brazil (Trust Media proxy):**\n\n")
    out.append(df_to_md(br))

    out.append(section_header("Cross-Indicator Overlap (Ensemble)"))
    out.append(df_to_md(ov))

    out.append(section_header("Notes"))
    out.append(
        "- With n=15 horizons, sampling error at 50%/90% is substantial; "
        "interpret small deviations cautiously.\n"
        "- Ensemble currently includes 1 model; more models can be added by appending paths to "
        "`configs/ensemble_models_1995.txt` and re-running Step 14.\n\n"
    )

    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("".join(out))
    print(f"[final_report] wrote {args.out_md}")

if __name__ == "__main__":
    main()
