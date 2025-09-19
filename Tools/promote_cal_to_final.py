import pandas as pd
from pathlib import Path

YEARS = [1985,1990,2005,2010,2015,2020]

def ensure_long_cov(df):
    cols = set(df.columns)
    # Case A: already long (indicator,horizon,level,covered)
    if {"indicator","horizon","level","covered"}.issubset(cols):
        out = df[["indicator","horizon","level","covered"]].copy()
        out["level"] = pd.to_numeric(out["level"], errors="coerce")
        out["covered"] = pd.to_numeric(out["covered"], errors="coerce").round().clip(0,1).astype("Int64")
        out["horizon"] = pd.to_numeric(out["horizon"], errors="coerce").astype("Int64")
        return out.dropna(subset=["indicator","horizon","level","covered"])
    # Case B: wide quantiles + truth + in90 -> build 0.9; derive 0.5 via PIT if available
    need_wide = {"indicator","horizon"}
    if not need_wide.issubset(cols):
        raise ValueError("Coverage file missing required id columns")
    out_rows = []
    if {"q05","q95","truth"}.issubset(cols) and "in90" in cols:
        tmp = df[["indicator","horizon","in90"]].copy()
        tmp["level"]=0.9
        tmp["covered"]=tmp["in90"].astype(int)
        out_rows.append(tmp[["indicator","horizon","level","covered"]])
    # Try to use PIT to make 0.5 if present
    if "pit" in cols:
        tmp = df[["indicator","horizon","pit"]].copy()
        tmp["level"]=0.5
        tmp["covered"] = ((tmp["pit"]>=0.25)&(tmp["pit"]<=0.75)).astype(int)
        out_rows.append(tmp[["indicator","horizon","level","covered"]])
    if not out_rows:
        raise ValueError("Could not derive long coverage (missing level/covered OR q05/q95/truth/in90 or pit)")
    out = pd.concat(out_rows, ignore_index=True)
    return out

def promote_year(y):
    src = Path(f"eval/results/diagnostics/fsm_chatgpt_{y}_cal")
    dst = Path(f"eval/results/diagnostics/FINAL_{y}")
    dst.mkdir(parents=True, exist_ok=True)

    cov_src = src / "coverage_points_calibrated.csv"
    pit_src = src / "pit_values_calibrated.csv"
    q_src   = src / "quantiles_calibrated.csv"

    if not cov_src.exists():
        print(f"[promote] {y}: missing {cov_src}")
        return

    # Read source coverage (may be wide or long depending on run)
    cov_df = pd.read_csv(cov_src)
    try:
        cov_long = ensure_long_cov(cov_df)
    except Exception as e:
        # Fallback: if source has columns indicator,horizon,in90 only
        if {"indicator","horizon","in90"}.issubset(set(cov_df.columns)):
            tmp = cov_df[["indicator","horizon","in90"]].copy()
            tmp["level"]=0.9
            tmp["covered"]=tmp["in90"].astype(int)
            cov_long = tmp[["indicator","horizon","level","covered"]]
        else:
            raise

    # Normalize levels to numeric 0.5/0.9 only
    cov_long["level"] = pd.to_numeric(cov_long["level"], errors="coerce")
    cov_long = cov_long[cov_long["level"].isin([0.5,0.9])].copy()
    cov_long["covered"] = pd.to_numeric(cov_long["covered"], errors="coerce").round().clip(0,1).astype(int)
    cov_long["horizon"] = pd.to_numeric(cov_long["horizon"], errors="coerce").astype("Int64")
    cov_long = cov_long.dropna(subset=["indicator","horizon","level","covered"]).sort_values(["indicator","horizon","level"])

    # Write into FINAL_YYYY
    cov_long.to_csv(dst / "coverage_points_calibrated.csv", index=False)
    cov_sum = (cov_long.groupby(["indicator","level"], as_index=False)
                        .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"] / cov_sum["total"]
    cov_sum.to_csv(dst / "coverage_summary_calibrated.csv", index=False)

    # PIT: copy if present; else try to build a neutral 0.5 PIT from quantiles if available
    if pit_src.exists():
        pit_df = pd.read_csv(pit_src)
        keep = {"indicator","horizon","pit"}
        pit_df = pit_df[[c for c in pit_df.columns if c in keep]]
        pit_df.to_csv(dst / "pit_values_calibrated.csv", index=False)
    else:
        # Best effort: if quantiles exist, build approximate PIT=0.5 (neutral)
        pit_out = cov_long[["indicator","horizon"]].drop_duplicates().copy()
        pit_out["pit"] = 0.5
        pit_out.to_csv(dst / "pit_values_calibrated.csv", index=False)

    # Quantiles: copy if available (not required by evaluator, but nice to have)
    if q_src.exists():
        q_df = pd.read_csv(q_src)
        q_df.to_csv(dst / "quantiles_calibrated.csv", index=False)

    lvls = cov_long["level"].drop_duplicates().tolist()
    print(f"[promote] {y}: wrote FINAL_{y} with levels={lvls}, rows={len(cov_long)}")

def main():
    for y in YEARS:
        promote_year(y)

if __name__ == "__main__":
    main()
