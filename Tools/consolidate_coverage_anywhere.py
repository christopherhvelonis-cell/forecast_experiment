import os, glob, re
import pandas as pd

DIAG_ROOT = os.path.join("eval","results","diagnostics")
YEARS = [1985,1990,2005,2010,2015,2020]

# Any file that plausibly contains pointwise coverage
CANDIDATE_PATTERNS = [
    "coverage_points_calibrated.csv",
    "coverage_points_calibrated.parquet",
    "coverage_points.csv",
    "coverage_points_calibrated_long.csv",
    "coverage_calibrated_points.csv",
    "coverage_long.csv",
    "coverage_calibrated.csv",
    "coverage.csv",
]

# helper: read csv/parquet
def read_any(path):
    try:
        if path.lower().endswith(".parquet"):
            return pd.read_parquet(path)
        return pd.read_csv(path)
    except Exception as e:
        return None

# normalize to evaluator schema
def to_long(df):
    if df is None or len(df)==0: return None
    # lower-map
    lower = {c.lower(): c for c in df.columns}

    # if year column exists, we drop it later
    # ID cols
    ind_col = lower.get("indicator", None)
    hz_col  = lower.get("horizon", lower.get("h", lower.get("horiz", lower.get("hzn", None))))
    lvl_col = lower.get("level", None)
    cov_col = lower.get("covered", None)

    def norm_level_series(s):
        s = s.astype(str).str.strip().str.lower()
        # map common variants
        repl = {
            "50":"0.5","p50":"0.5","q50":"0.5","q_50":"0.5",".5":"0.5","50%":"0.5",
            "90":"0.9","p90":"0.9","q90":"0.9","q_90":"0.9",".9":"0.9","90%":"0.9",
        }
        return s.map(lambda x: repl.get(x, x)).str.replace("0.50","0.5").str.replace("0.90","0.9")

    # Case A: already long (indicator/horizon/level/covered present)
    if ind_col and hz_col and lvl_col and cov_col:
        out = df.rename(columns={ind_col:"indicator", hz_col:"horizon", lvl_col:"level", cov_col:"covered"}).copy()
        # drop nuisance columns
        for extra in ["year","origin","cutoff","vintage"]:
            if extra in out.columns: out = out.drop(columns=[extra], errors="ignore")
        # normalize types
        out["level"] = norm_level_series(out["level"])
        out["horizon"] = pd.to_numeric(out["horizon"], errors="coerce").astype("Int64")
        out["covered"] = pd.to_numeric(out["covered"], errors="coerce")
        # bools → int
        if out["covered"].dtype == bool:
            out["covered"] = out["covered"].astype(int)
        out["covered"] = out["covered"].fillna(0).astype(int)
        # keep only 0.5/0.9 if present
        lv = set(out["level"].unique().tolist())
        if {"0.5","0.9"} & lv:
            out = out[out["level"].isin(["0.5","0.9"])]
        out = out.dropna(subset=["indicator","horizon","level","covered"])
        if len(out)==0: return None
        return out[["indicator","horizon","level","covered"]]

    # Case B: wide → melt
    if ind_col and hz_col:
        # find any columns that look like level variants
        candidates = []
        for c in df.columns:
            cl = c.lower()
            if cl in {"covered_0.5","covered_50","cov50","cov_50","0.5","p50","q50","q_50"}:
                candidates.append((c,"0.5"))
            if cl in {"covered_0.9","covered_90","cov90","cov_90","0.9","p90","q90","q_90"}:
                candidates.append((c,"0.9"))
        if candidates:
            keep = [ind_col, hz_col] + [c for c,_ in candidates]
            tmp = df[keep].copy()
            long = tmp.melt(id_vars=[ind_col, hz_col], var_name="_k", value_name="covered")
            # map keys to levels
            key_to_level = {}
            for c,l in candidates: key_to_level[c] = l
            long["level"] = long["_k"].map(key_to_level).fillna(long["_k"])
            long = long.drop(columns=["_k"])
            long = long.rename(columns={ind_col:"indicator", hz_col:"horizon"})
            long["horizon"] = pd.to_numeric(long["horizon"], errors="coerce").astype("Int64")
            long["covered"] = pd.to_numeric(long["covered"], errors="coerce").fillna(0).astype(int)
            long = long[long["level"].isin(["0.5","0.9"])]
            long = long.dropna(subset=["indicator","horizon","level","covered"])
            if len(long)==0: return None
            return long[["indicator","horizon","level","covered"]]

    return None

def gather_for_year(year):
    # collect coverage-like files anywhere that *mentions this year* in the path
    # also include FINAL_YYYY (in case populated) and *_cal* dirs
    year_pat = re.compile(rf"(?:^|[^\d]){year}(?:[^\d]|$)")
    files = []
    for pat in CANDIDATE_PATTERNS:
        for p in glob.glob(os.path.join(DIAG_ROOT, "**", pat), recursive=True):
            # only consider files that belong to this year somewhere in their path
            if year_pat.search(p.replace("\\","/")):
                files.append(p)
    return sorted(set(files))

def main():
    any_writes = False
    for year in YEARS:
        dst_dir = os.path.join(DIAG_ROOT, f"FINAL_{year}")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "coverage_points_calibrated.csv")

        candidates = gather_for_year(year)
        parts = []
        for fp in candidates:
            df = read_any(fp)
            out = to_long(df)
            if out is not None and len(out):
                parts.append(out)
        if not parts:
            print(f"[consolidate] {year}: no usable coverage rows found in {len(candidates)} candidate file(s).")
            continue

        cat = pd.concat(parts, ignore_index=True)
        # de-dup in case repeats; prefer uniqueness by indicator,horizon,level
        cat = (cat
               .dropna(subset=["indicator","horizon","level","covered"])
               .astype({"indicator":"string","level":"string"})
               .sort_values(["indicator","horizon","level"])
               .drop_duplicates(["indicator","horizon","level"], keep="first"))

        # keep only rows where level is exactly '0.5' or '0.9'
        if {"0.5","0.9"} & set(cat["level"].unique()):
            cat = cat[cat["level"].isin(["0.5","0.9"])]

        if len(cat)==0:
            print(f"[consolidate] {year}: after normalization, 0 rows remain.")
            continue

        cat.to_csv(dst, index=False)
        lv = sorted(cat["level"].unique().tolist())
        print(f"[consolidate] {year}: wrote {dst} | rows={len(cat)} | levels={lv} | from {len(candidates)} source file(s).")
        any_writes = True

    if not any_writes:
        print("[consolidate] Nothing written. If your only artifacts are quantiles, we need to rebuild coverage from quantiles + actuals.")
if __name__ == "__main__":
    main()
