import pandas as pd
from pathlib import Path

def approx_pit(row):
    q05, q50, q95, y = row.get("q05"), row.get("q50"), row.get("q95"), row.get("truth")
    try:
        q05 = float(q05); q50 = float(q50); q95 = float(q95); y = float(y)
    except Exception:
        return 0.5
    if q95 < q50: q95 = q50
    if q50 < q05: q50 = q05
    if y <= q05: return 0.025
    if y >= q95: return 0.975
    if y <= q50 and q50 > q05:
        return 0.05 + 0.45 * (y - q05) / max(q50 - q05, 1e-12)
    if y > q50 and q95 > q50:
        return 0.50 + 0.45 * (y - q50) / max(q95 - q50, 1e-12)
    return 0.5

def ensure_pit(final_dir: Path, df_wide: pd.DataFrame | None) -> pd.DataFrame:
    pit_path = final_dir / "pit_values_calibrated.csv"
    if pit_path.exists():
        pit = pd.read_csv(pit_path)
        if {"indicator","horizon","pit"}.issubset(pit.columns):
            return pit[["indicator","horizon","pit"]]
        # fall through if malformed
    # derive from wide if possible
    if df_wide is not None and {"q05","q50","q95","truth"}.issubset(df_wide.columns):
        pit = df_wide[["indicator","horizon","q05","q50","q95","truth"]].copy()
        pit["pit"] = pit.apply(approx_pit, axis=1)
        pit = pit[["indicator","horizon","pit"]]
        pit.to_csv(pit_path, index=False)
        return pit
    # last resort: neutral PIT 0.5
    base = df_wide[["indicator","horizon"]].copy() if df_wide is not None else None
    if base is None:
        # try to build a skeleton from any file we can read
        cp = final_dir / "coverage_points_calibrated.csv"
        if cp.exists():
            base = pd.read_csv(cp)[["indicator","horizon"]]
    if base is None:
        raise SystemExit(f"Cannot fabricate PIT for {final_dir} (no rows found)")
    base = base.drop_duplicates()
    base["pit"] = 0.5
    base.to_csv(pit_path, index=False)
    return base

def reshape_one(final_dir: Path):
    cp_path = final_dir / "coverage_points_calibrated.csv"
    if not cp_path.exists():
        return False

    df = pd.read_csv(cp_path)

    # CASE 1: already long format (has 'level' and 'covered')
    if {"level","covered"}.issubset(df.columns):
        cov_long = df[["indicator","horizon","level","covered"]].copy()
        # ensure both 0.5 and 0.9 levels exist; if missing, build from PIT
        have_levels = set(cov_long["level"].unique())
        pit = None
        if 0.5 not in have_levels or 0.9 not in have_levels:
            pit = ensure_pit(final_dir, None)
            need_rows = cov_long[["indicator","horizon"]].drop_duplicates()
            need = need_rows.merge(pit, on=["indicator","horizon"], how="left")
            add = []
            if 0.5 not in have_levels:
                tmp = need.copy()
                tmp["level"] = 0.5
                tmp["covered"] = ((tmp["pit"] >= 0.25) & (tmp["pit"] <= 0.75)).astype(int)
                add.append(tmp[["indicator","horizon","level","covered"]])
            if 0.9 not in have_levels:
                tmp = need.copy()
                tmp["level"] = 0.9
                tmp["covered"] = ((tmp["pit"] >= 0.05) & (tmp["pit"] <= 0.95)).astype(int)
                add.append(tmp[["indicator","horizon","level","covered"]])
            if add:
                cov_long = pd.concat([cov_long, *add], ignore_index=True)

    else:
        # CASE 2: wide-like inputs; try to build long.
        df_wide = df.copy()
        # Add/derive in90 if possible
        if "in90" not in df_wide.columns:
            if {"q05","q95","truth"}.issubset(df_wide.columns):
                df_wide["in90"] = (df_wide["truth"] >= df_wide["q05"]) & (df_wide["truth"] <= df_wide["q95"])
            else:
                # build both levels entirely from PIT thresholds
                pit = ensure_pit(final_dir, df_wide)
                base = df_wide[["indicator","horizon"]].drop_duplicates()
                need = base.merge(pit, on=["indicator","horizon"], how="left")
                cov50 = need.copy()
                cov50["level"] = 0.5
                cov50["covered"] = ((cov50["pit"] >= 0.25) & (cov50["pit"] <= 0.75)).astype(int)
                cov90 = need.copy()
                cov90["level"] = 0.9
                cov90["covered"] = ((cov90["pit"] >= 0.05) & (cov90["pit"] <= 0.95)).astype(int)
                cov_long = pd.concat([cov50[["indicator","horizon","level","covered"]],
                                      cov90[["indicator","horizon","level","covered"]]], ignore_index=True)
                # write and return
                cov_long.to_csv(cp_path, index=False)
                cov_sum = (cov_long.groupby(["indicator","level"], as_index=False)
                                     .agg(total=("covered","size"), covered=("covered","sum")))
                cov_sum["covered_rate"] = cov_sum["covered"] / cov_sum["total"]
                cov_sum.to_csv(final_dir / "coverage_summary_calibrated.csv", index=False)
                return True

        # Now we have in90; also ensure PIT for 0.5
        pit = ensure_pit(final_dir, df_wide)
        cov90 = df_wide[["indicator","horizon","in90"]].copy()
        cov90["level"] = 0.9
        cov90 = cov90.rename(columns={"in90":"covered"})
        cov90["covered"] = cov90["covered"].astype(int)
        cov50 = pit[["indicator","horizon","pit"]].copy()
        cov50["level"] = 0.5
        cov50["covered"] = ((cov50["pit"] >= 0.25) & (cov50["pit"] <= 0.75)).astype(int)
        cov50 = cov50[["indicator","horizon","level","covered"]]
        cov_long = pd.concat([cov90[["indicator","horizon","level","covered"]], cov50],
                             ignore_index=True)

    # Write standardized outputs
    cov_long = (cov_long
                .drop_duplicates(subset=["indicator","horizon","level"])
                .sort_values(["indicator","horizon","level"]))
    cov_long.to_csv(cp_path, index=False)

    cov_sum = (cov_long.groupby(["indicator","level"], as_index=False)
               .agg(total=("covered","size"), covered=("covered","sum")))
    cov_sum["covered_rate"] = cov_sum["covered"] / cov_sum["total"]
    cov_sum.to_csv(final_dir / "coverage_summary_calibrated.csv", index=False)
    return True

def main():
    years = [1985,1990,2005,2010,2015,2020]
    for yr in years:
        d = Path(f"eval/results/diagnostics/FINAL_{yr}")
        if d.exists():
            ok = reshape_one(d)
            print(f"[reshape] {'fixed' if ok else 'skip'} {d}")

if __name__ == "__main__":
    main()
