# data/processing_pipeline.py
import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("data/raw")
PRO_DIR = Path("data/processed")
ANNOT_MD = PRO_DIR / "annotations.md"
CORR_CSV = PRO_DIR / "corr_matrix.csv"

PRO_DIR.mkdir(parents=True, exist_ok=True)

def _annualize_to_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: df with columns ['date','value'] (date-like, possibly multiple per year)
    Output: tidy annual rows with columns ['date','value'] where date = Jan 1 of year.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    # Resample to Year-End, then normalize to Jan 1
    s = df.set_index("date")["value"].resample("YE").mean()
    out = (
        s.reset_index()
         .assign(date=lambda x: pd.to_datetime(x["date"].dt.year.astype(int).astype(str) + "-01-01"))
         .rename(columns={"value": "value"})[["date", "value"]]
         .sort_values("date", kind="stable")
         .reset_index(drop=True)
    )
    # Ensure unique years (group by just in case and take mean)
    out["year"] = out["date"].dt.year.astype(int)
    out = (
        out.groupby("year", as_index=False)["value"].mean()
           .assign(date=lambda x: pd.to_datetime(x["year"].astype(str) + "-01-01"))
           .drop(columns=["year"])
           .sort_values("date", kind="stable")
           .reset_index(drop=True)
    )
    return out

def _detect_breaks_simple(values: np.ndarray) -> list[int]:
    """
    Lightweight break heuristic: |Δ| > 3 * median(|Δ|).
    Returns list of break YEARS offsets (we’ll translate to calendar year upstream).
    """
    x = pd.Series(values).dropna().values
    n = len(x)
    if n <= 2:
        return []
    diffs = np.diff(x)
    mad = np.median(np.abs(diffs)) if len(diffs) else 0.0
    thr = 3.0 * (mad if mad > 0 else (np.std(diffs) if len(diffs) else 0.0))
    if thr <= 0:
        return []
    idx = np.where(np.abs(diffs) > thr)[0] + 1  # jump locations (row indices)
    return [int(i) for i in idx]

def process_one_raw(path: Path) -> str | None:
    """
    Process a single raw CSV (requires columns ['date','value']).
    Writes processed CSV as tidy `date,value` rows (one per year).
    Returns annotation message.
    """
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        return f"[ERROR] {path.name}: {e}"

    if not {"date", "value"}.issubset(df.columns):
        return f"[SKIP] {path.name}: missing 'date' and 'value' columns"

    try:
        annual = _annualize_to_rows(df)
        # Break heuristic (convert row indices to years)
        if len(annual) > 0:
            br_idx = _detect_breaks_simple(annual["value"].to_numpy())
            years = annual["date"].dt.year.to_numpy()
            break_years = [int(years[i]) for i in br_idx if 0 <= i < len(years)]
        else:
            break_years = []

        out_path = PRO_DIR / path.name
        annual.to_csv(out_path, index=False)  # always 'date,value' tidy format
        return f"[OK] Processed {path.name} -> {out_path.name} | breaks: {break_years}"
    except Exception as e:
        return f"[ERROR] {path.name}: {e}"

def _load_processed_flex(path: Path) -> pd.Series:
    """
    Robust reader for processed files. Handles both tidy ('date,value') and legacy index CSVs.
    Returns a Series indexed by YEAR (int) with unique index (mean if duplicates).
    """
    df = pd.read_csv(path, low_memory=False)
    if {"date", "value"}.issubset(df.columns):
        # tidy path
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "value"]).copy()
        df["year"] = df["date"].dt.year.astype(int)
        s = df.groupby("year", as_index=True)["value"].mean()
        s.name = path.stem
        return s
    else:
        # legacy path: assume first column is date index, second is 'value'
        try:
            df = pd.read_csv(path, index_col=0)
            # Try parse index to datetime; if fails, coerce to year
            try:
                idx_dt = pd.to_datetime(df.index, errors="coerce")
                years = idx_dt.year
            except Exception:
                # If index already looks like years
                years = pd.to_numeric(df.index, errors="coerce").astype("Int64")
            s = pd.Series(df.iloc[:, 0].values, index=years, name=path.stem)
            s = s.dropna()
            # Group by year to ensure unique index
            s = s.groupby(s.index.astype(int)).mean()
            s.index = s.index.astype(int)
            return s
        except Exception as e:
            raise ValueError(f"Cannot parse processed file {path.name}: {e}")

def build_corr_matrix():
    """
    Assemble all processed series into a single DataFrame indexed by YEAR (int),
    then compute the Pearson correlation on overlapping years.
    """
    series_dict = {}
    for f in PRO_DIR.glob("*.csv"):
        try:
            s = _load_processed_flex(f)
            if s is not None and len(s) > 0:
                series_dict[f.stem] = s
        except Exception as e:
            print(f"[WARN] Skipping {f.name} for corr: {e}")

    if not series_dict:
        return False

    # Outer join on year index; ensure unique and sorted
    df = pd.DataFrame(series_dict)
    # df index is already year (int) from loader; drop duplicate years defensively
    df = df.groupby(df.index).mean()
    df = df.sort_index()

    corr = df.corr()
    corr.to_csv(CORR_CSV, index=True)
    print(f"[OK] Wrote correlation matrix: {CORR_CSV}")
    return True

def main():
    annotations: list[str] = []

    for raw_path in RAW_DIR.glob("*.csv"):
        msg = process_one_raw(raw_path)
        if msg:
            print(msg)
            annotations.append(msg)

    _ = build_corr_matrix()

    ANNOT_MD.write_text(
        "# Data Annotations\n\n" + "\n".join(f"- {line}" for line in annotations) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Wrote annotations: {ANNOT_MD}")

if __name__ == "__main__":
    main()
