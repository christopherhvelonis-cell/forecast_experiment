import pandas as pd
from pathlib import Path
import re

want = {
    "union_membership_rate": re.compile(r"union_membership_rate.*\.csv$", re.I),
    "trust_media_pct":       re.compile(r"trust_media_pct.*\.csv$", re.I),
    "vep_turnout_pct":       re.compile(r"vep_turnout_pct.*\.csv$", re.I),
}

roots = [Path("data/processed"), Path("data/processed/archive"), Path("data")]
found = {}
for name, pat in want.items():
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.csv"):
            if pat.search(p.name):
                found[name] = p
                break
        if name in found:
            break

missing = [k for k in want if k not in found]
if missing:
    raise SystemExit(f"Missing files for: {missing}. Found: {found}")

def load_series(colname: str, path: Path) -> pd.DataFrame:
    try:
        d = pd.read_csv(path)
    except Exception:
        d = pd.read_csv(path, engine="python")

    def ensure_year(df: pd.DataFrame) -> pd.DataFrame:
        c = {c.lower(): c for c in df.columns}
        if "year" in c:
            return df.rename(columns={c["year"]: "year"})
        if "date" in c:
            out = df.rename(columns={c["date"]: "date"}).copy()
            out["year"] = pd.to_datetime(out["date"], errors="coerce").dt.year
            return out
        # headerless fallback
        try:
            d2 = pd.read_csv(path, header=None)
            if d2.shape[1] >= 3 and isinstance(d2.iat[0,0], str) and colname.lower() in str(d2.iat[0,0]).lower():
                d2 = d2.rename(columns={0:"indicator", 1:"year", 2:"value"})
                return d2
            if d2.shape[1] >= 2:
                d2 = d2.rename(columns={0:"year", 1:"value"})
                return d2
        except Exception:
            pass
        raise SystemExit(f"{path} must contain a 'year' or 'date' column (or be parseable headerless)")

    d = ensure_year(d)

    cols_lower = {c.lower(): c for c in d.columns}
    value_col = None
    if colname in d.columns:
        value_col = colname
    elif "value" in cols_lower:
        value_col = cols_lower["value"]
    else:
        numeric_candidates = [c for c in d.columns
                              if c.lower() not in ("year","date","indicator","name","series","units","unit")
                              and pd.api.types.is_numeric_dtype(d[c])]
        if len(numeric_candidates) == 1:
            value_col = numeric_candidates[0]
    if value_col is None:
        others = [c for c in d.columns if c != "year"]
        if "year" in d.columns and len(others)==1:
            value_col = others[0]
        else:
            raise SystemExit(f"Could not identify value column in {path}")

    if "indicator" in d.columns:
        mask = d["indicator"].astype(str).str.lower().str.contains(colname.lower())
        if mask.any():
            d = d.loc[mask, ["year", value_col]]
        else:
            d = d[["year", value_col]]

    out = d[["year", value_col]].copy()
    out = out.dropna(subset=["year"])
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"]).astype({"year":"int"})
    out = out.rename(columns={value_col: colname}).drop_duplicates(subset=["year"])
    return out

dfs = [load_series(name, path) for name, path in found.items()]

panel = dfs[0]
for d in dfs[1:]:
    panel = panel.merge(d, on="year", how="outer")
panel = panel.sort_values("year")

out = Path("data/truths/indicator_panel.csv")
out.parent.mkdir(parents=True, exist_ok=True)
panel.to_csv(out, index=False)
print(f"[panel] wrote {len(panel)} rows to {out.resolve()}")
