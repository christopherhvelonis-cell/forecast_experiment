# tools/make_structural_indicators.py
"""
Batch-clean structural indicators from data/processed/archive into tidy date,value
series under data/raw/, ready for the processing pipeline.

Heuristics:
- Accepts many legacy shapes (year column, date index, wide one-column with year index).
- Coerces to annual rows (one per year) and writes YYYY-01-01 as 'date'.
- Drops NA/inf and collapses duplicate years by mean.

Targets (if present in archive):
  - union_membership_rate_pct.csv
  - public-trust-in-government.csv
  - gini_household.csv
  - urban_population_share_pct_annual.csv
  - vep_turnout_pct.csv
  - foreign_born_population_millions.csv
  - homicide_rate_per100k.csv
  - military_spend_gdp_share_pct.csv
  - trust_media_pct.csv
  - house_polarization_dw.csv
  - cultural_liberalism_index.csv
  - median_household_income_real.csv
  - justice_mq_score.csv
  - ba_plus_25plus_pct.csv
  - president_party_code.csv (numeric; may be scenario-only later)

Result filenames (in data/raw/):
  union_membership_rate, public_trust_gov, gini_household, urban_pop_share,
  vep_turnout_pct, foreign_born_pop_m, homicide_rate_per100k, mil_spend_gdp_share_pct,
  trust_media_pct, house_polarization_dw, cultural_liberalism_index,
  median_hh_income_real, justice_mq_score, ba_plus_25plus_share, president_party_code
"""
from pathlib import Path
import pandas as pd

ARCH = Path("data/processed/archive")
RAW  = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)

MAP = {
    "union_membership_rate_pct.csv":        "union_membership_rate",
    "public-trust-in-government.csv":       "public_trust_gov",
    "gini_household.csv":                   "gini_household",
    "urban_population_share_pct_annual.csv":"urban_pop_share",
    "vep_turnout_pct.csv":                  "vep_turnout_pct",
    "foreign_born_population_millions.csv": "foreign_born_pop_m",
    "homicide_rate_per100k.csv":            "homicide_rate_per100k",
    "military_spend_gdp_share_pct.csv":     "mil_spend_gdp_share_pct",
    "trust_media_pct.csv":                  "trust_media_pct",
    "house_polarization_dw.csv":            "house_polarization_dw",
    "cultural_liberalism_index.csv":        "cultural_liberalism_index",
    "median_household_income_real.csv":     "median_hh_income_real",
    "justice_mq_score.csv":                 "justice_mq_score",
    "ba_plus_25plus_pct.csv":               "ba_plus_25plus_share",
    "president_party_code.csv":             "president_party_code",
}

VALUE_LIKE = {"value","val","y","series","measure","pct","index","rate","score"}

def _tidy(df: pd.DataFrame, name: str) -> pd.DataFrame:
    cols_lower = {c.lower(): c for c in df.columns}

    # Case A: already tidy
    if "date" in cols_lower and "value" in cols_lower:
        out = df[[cols_lower["date"], cols_lower["value"]]].copy()
        out.columns = ["date","value"]
    # Case B: year + value-like column
    elif "year" in cols_lower:
        vcols = [c for c in df.columns if c.lower() in VALUE_LIKE]
        if not vcols:
            # fallback: pick the second column if exists
            vcols = df.columns[1:2].tolist()
        ycol = cols_lower["year"]
        vcol = vcols[0]
        out = df[[ycol, vcol]].copy()
        out.columns = ["year","value"]
        out = out.dropna(subset=["year","value"])
        out["year"] = pd.to_numeric(out["year"], errors="coerce")
        out = out.dropna(subset=["year"])
        out["date"] = pd.to_datetime(out["year"].astype(int).astype(str) + "-01-01")
        out = out[["date","value"]]
    # Case C: first column parseable as date, second numeric
    elif df.shape[1] >= 2:
        dt = pd.to_datetime(df.iloc[:,0], errors="coerce")
        out = pd.DataFrame({"date": dt, "value": pd.to_numeric(df.iloc[:,1], errors="coerce")})
        out = out.dropna(subset=["date","value"])
    else:
        raise ValueError("Unrecognized shape—please add date,value manually.")

    # Normalize to yearly rows & clean
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date","value"]).copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["value"])

    # Annualize to year-end then map to Jan 1, and collapse duplicate years
    s = out.set_index("date")["value"].resample("YE").mean().reset_index()
    s["date"] = pd.to_datetime(s["date"].dt.year.astype(int).astype(str) + "-01-01")
    s["year"] = s["date"].dt.year.astype(int)
    s = s.groupby("year", as_index=False)["value"].mean()
    s["date"] = pd.to_datetime(s["year"].astype(str) + "-01-01")
    s = s[["date","value"]].sort_values("date").reset_index(drop=True)
    return s

def main():
    created = []
    skipped  = []
    for src_name, out_stem in MAP.items():
        src = ARCH / src_name
        if not src.exists():
            skipped.append(f"[MISS] {src_name} (not found)")
            continue
        try:
            df = pd.read_csv(src, low_memory=False)
            tidy = _tidy(df, src_name)
            out = RAW / f"{out_stem}.csv"
            tidy.to_csv(out, index=False)
            created.append(f"[OK] {src_name} -> data/raw/{out.name} ({len(tidy)} rows)")
        except Exception as e:
            skipped.append(f"[FAIL] {src_name}: {e}")

    print("\n".join(created) if created else "[Info] No files created.")
    if skipped:
        print("\n--- Skipped ---")
        print("\n".join(skipped))

if __name__ == "__main__":
    main()
