import os, glob
import pandas as pd

ROOT = os.path.join("eval","results","diagnostics")
TARGET_YEARS = {1985,1990,2005,2010,2015,2020}

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

def read_any(p):
    try:
        if p.lower().endswith(".parquet"):
            return pd.read_parquet(p)
        return pd.read_csv(p)
    except Exception:
        return None

def to_long(df):
    if df is None or len(df)==0: return None
    cmap = {c.lower(): c for c in df.columns}
    def col(*names):
        for n in names:
            if n in cmap: return cmap[n]
        return None
    ind = col("indicator"); hz = col("horizon","h","horiz","hzn"); lvl = col("level"); cov = col("covered")

    # already long?
    if ind and hz and lvl and cov:
        out = df.rename(columns={ind:"indicator",hz:"horizon",lvl:"level",cov:"covered"}).copy()
        ycol = col("year")
        if ycol and ycol!="year": out = out.rename(columns={ycol:"year"})
        out["level"] = (out["level"].astype(str).str.strip().str.lower()
                        .replace({"50":"0.5","p50":"0.5","q50":"0.5","q_50":"0.5",".5":"0.5","50%":"0.5",
                                  "90":"0.9","p90":"0.9","q90":"0.9","q_90":"0.9",".9":"0.9","90%":"0.9",
                                  "0.50":"0.5","0.90":"0.9"}))
        out["horizon"] = pd.to_numeric(out["horizon"], errors="coerce").astype("Int64")
        out["covered"] = pd.to_numeric(out["covered"], errors="coerce").fillna(0).astype(int)
        lvls = set(out["level"].unique().tolist())
        if {"0.5","0.9"} & lvls: out = out[out["level"].isin(["0.5","0.9"])]
        return out

    # wide → melt
    if ind and hz:
        cand = []
        for c in df.columns:
            cl = str(c).lower()
            if cl in {"covered_0.5","covered_50","cov50","cov_50","0.5","p50","q50","q_50"}: cand.append((c,"0.5"))
            if cl in {"covered_0.9","covered_90","cov90","cov_90","0.9","p90","q90","q_90"}: cand.append((c,"0.9"))
        if cand:
            keep = [cmap[ind], cmap[hz]] + [c for c,_ in cand]
            out = df[keep].copy().melt(id_vars=[cmap[ind], cmap[hz]], var_name="_k", value_name="covered")
            out["level"] = out["_k"].map({c:l for c,l in cand}).fillna(out["_k"])
            out = out.drop(columns=["_k"]).rename(columns={cmap[ind]:"indicator", cmap[hz]:"horizon"})
            out["horizon"] = pd.to_numeric(out["horizon"], errors="coerce").astype("Int64")
            out["covered"] = pd.to_numeric(out["covered"], errors="coerce").fillna(0).astype(int)
            out = out[out["level"].isin(["0.5","0.9"])]
            return out

    return None

def main():
    files = []
    for pat in CANDIDATE_PATTERNS:
        files.extend(glob.glob(os.path.join(ROOT,"**",pat), recursive=True))
    files = sorted(set(files))

    bins = {y: [] for y in TARGET_YEARS}
    for fp in files:
        df = read_any(fp); out = to_long(df)
        if out is None or len(out)==0: continue

        ycol = None
        for c in out.columns:
            if str(c).lower()=="year": ycol = c; break
        if ycol is None: continue  # need year to route

        out["__year"] = pd.to_numeric(out[ycol], errors="coerce").astype("Int64")
        for y, sub in out.groupby("__year", dropna=True):
            if int(y) in TARGET_YEARS and len(sub):
                bins[int(y)].append(sub.drop(columns=[c for c in [ycol,"__year"] if c in sub.columns]))

    wrote_any = False
    for y in TARGET_YEARS:
        if not bins[y]:
            print(f"[route] {y}: no rows found with year={y}.")
            continue
        cat = (pd.concat(bins[y], ignore_index=True)
                 .dropna(subset=["indicator","horizon","level","covered"])
                 .astype({"indicator":"string","level":"string"}))
        if {"0.5","0.9"} & set(cat["level"].unique()): cat = cat[cat["level"].isin(["0.5","0.9"])]
        cat = cat.sort_values(["indicator","horizon","level"]).drop_duplicates(["indicator","horizon","level"], keep="first")

        dst_dir = os.path.join(ROOT, f"FINAL_{y}"); os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "coverage_points_calibrated.csv")
        cat.to_csv(dst, index=False)
        print(f"[route] {y}: wrote {dst} | rows={len(cat)} | levels={sorted(cat['level'].unique().tolist())}")
        wrote_any = True

    if not wrote_any:
        print("[route] No FINAL_* written. Sources may be header-only.")
if __name__ == "__main__":
    main()
