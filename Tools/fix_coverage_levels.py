import pandas as pd
from pathlib import Path

YEARS = [1985,1990,2005,2010,2015,2020]

def fix_one(y):
    p = Path(f"eval/results/diagnostics/FINAL_{y}/coverage_points_calibrated.csv")
    if not p.exists():
        print(f"[fix] skip {y} (missing {p})")
        return
    df = pd.read_csv(p)

    # Ensure required columns
    need = {"indicator","horizon","level","covered"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"{p} missing {missing}; columns are {list(df.columns)}")

    # Coerce types
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df["covered"] = pd.to_numeric(df["covered"], errors="coerce").round().astype("Int64")
    df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce").astype("Int64")

    # Keep only valid rows
    df = df.dropna(subset=["indicator","horizon","level","covered"]).copy()
    # Normalize levels very strictly to {0.5, 0.9}
    df.loc[(df["level"] > 0) & (df["level"] < 1), "level"] = df["level"].round(2)
    # Rare case: levels like 50/90 -> convert to 0.5/0.9
    df.loc[df["level"] > 1, "level"] = (df.loc[df["level"] > 1, "level"] / 100).round(2)

    # Ensure integers for covered (0/1)
    df["covered"] = df["covered"].clip(lower=0, upper=1).astype(int)

    # Keep only 0.5 / 0.9 rows
    df = df[df["level"].isin([0.5, 0.9])].copy()

    # Sanity: if one level is missing, try to derive:
    have = set(df["level"].unique().tolist())
    if 0.9 not in have:
        print(f"[fix] WARNING {y}: no 0.9 level rows found")
    if 0.5 not in have:
        print(f"[fix] WARNING {y}: no 0.5 level rows found")

    df = df.sort_values(["indicator","horizon","level"])
    df.to_csv(p, index=False)

    # Print a tiny preview so we can see what the evaluator will read
    head = df.head(6).to_string(index=False)
    uniq = df["level"].drop_duplicates().tolist()
    print(f"[fix] {y}: levels={uniq}\n{head}\n")

def main():
    for y in YEARS:
        fix_one(y)

if __name__ == "__main__":
    main()
