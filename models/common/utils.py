# models/common/utils.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

PRO_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")


def _coerce_year_index(idx: pd.Index) -> pd.Index:
    """Convert various date-ish indices to Int64 year index."""
    try:
        years = pd.to_datetime(idx, errors="coerce").year
        years = pd.Index(years, dtype="Int64")
        if years.notna().any():
            return years
    except Exception:
        pass
    try:
        years = pd.to_numeric(idx, errors="coerce").astype("Int64")
        return pd.Index(years)
    except Exception:
        pass

    def _extract_year(x):
        s = str(x)
        for i in range(len(s) - 3):
            sub = s[i : i + 4]
            if sub.isdigit():
                val = int(sub)
                if 1700 <= val <= 2100:
                    return val
        return pd.NA

    return pd.Index([_extract_year(x) for x in idx], dtype="Int64")


def _repair_from_raw(indicator: str, pro_path: Path) -> pd.Series:
    """
    Rebuild processed series from data/raw/{indicator}.csv (date,value).
    Writes a clean processed CSV with a 'value' column.
    """
    raw_path = RAW_DIR / f"{indicator}.csv"
    if not raw_path.exists():
        raise KeyError(f"{pro_path} has no 'value'/'imputed' and no raw fallback at {raw_path}")
    df = pd.read_csv(raw_path)
    if "date" not in df.columns or "value" not in df.columns:
        raise KeyError(f"{raw_path} must have columns 'date' and 'value'")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    s = df.set_index("date")["value"].astype(float).resample("YE").mean().dropna()
    s.index = pd.Index(s.index.year, dtype="Int64")
    s = s.sort_index()

    out = pd.DataFrame({"value": s.values}, index=pd.to_datetime(s.index.astype(int), format="%Y"))
    pro_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(pro_path)
    print(f"[repair] Rebuilt processed {pro_path.name} from raw/{indicator}.csv ({len(s)} rows).")
    return s.rename(indicator)


def _read_processed_any_shape(pro_path: Path) -> pd.DataFrame:
    """
    Read a processed CSV regardless of shape and try to produce a frame
    with a 'value' column (or at least some numeric column).
    """
    df = pd.read_csv(pro_path, index_col=0)
    if df.shape[1] == 1 and df.columns.tolist() == ["date"]:
        df2 = pd.read_csv(pro_path)
        if "date" in df2.columns and df2.shape[1] >= 2:
            cand_cols = [c for c in df2.columns if c.lower() != "date"]
            val_col = cand_cols[-1]
            df = df2.set_index("date")[[val_col]].rename(columns={val_col: "value"})
        else:
            return df

    if "value" not in df.columns and "imputed" not in df.columns:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            df = df[[num_cols[-1]]].rename(columns={num_cols[-1]: "value"})
    return df


def load_indicator(indicator: str, pro_dir: Path | None = None) -> pd.Series:
    """
    Load processed indicator as a Series (Int64 year index).
    Accepts 'value' (preferred) or 'imputed' column; if malformed, rebuilds
    from data/raw/{indicator}.csv.
    """
    if pro_dir is None:
        pro_dir = PRO_DIR
    pro_path = pro_dir / f"{indicator}.csv"
    if not pro_path.exists():
        return _repair_from_raw(indicator, pro_path)

    df = _read_processed_any_shape(pro_path)
    col = "value" if "value" in df.columns else ("imputed" if "imputed" in df.columns else None)
    if col is None:
        return _repair_from_raw(indicator, pro_path)

    years = _coerce_year_index(df.index)
    s = pd.Series(df[col].astype(float).values, index=years, name=indicator)
    s = s[s.index.notna()]
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s


def make_origin_panel(
    indicators: Iterable[str],
    origin_year: int,
    pro_dir: Path | None = None,
    min_len: int = 3,
) -> pd.DataFrame:
    """Build a panel up to/including origin_year; keep series with >=min_len obs."""
    if pro_dir is None:
        pro_dir = PRO_DIR

    print(f"[make_origin_panel] Origin={origin_year}, min_len={min_len}")
    kept: List[pd.Series] = []
    names: List[str] = []

    for ind in indicators:
        s = load_indicator(ind, pro_dir)
        yrs_total = int(s.index.notna().sum())
        yrs_pre = int((s.index.astype("Int64") <= origin_year).sum())
        print(f"  - {ind}: {yrs_total} yrs  -> <= origin: {yrs_pre}")
        if yrs_pre >= min_len:
            kept.append(s.loc[s.index <= origin_year])
            names.append(ind)
        else:
            print(f"    ! Skipping {ind}: only {yrs_pre} obs before origin (need >= {min_len})")

    if not kept:
        raise ValueError("No indicators with sufficient history for the given origin.")
    df = pd.concat(kept, axis=1)
    df.columns = names
    return df


def _parse_horizon(h) -> int:
    """Accept 5, '5', 'h5', 'H5' etc."""
    s = str(h).strip()
    if s.isdigit():
        return int(s)
    if (s.lower().startswith("h")) and s[1:].isdigit():
        return int(s[1:])
    raise ValueError(f"Unrecognized horizon key: {h!r}")


def save_quantiles_csv(
    quantiles: Dict[str, Dict],  # flexible shapes supported
    out_path: str | Path,
) -> None:
    """
    Write a tidy CSV with rows: indicator,horizon,q05,q50,q95 from either:
      A) {indicator: {horizon: {'q05','q50','q95'}}}
      B) {indicator: {'q05': {h: v}, 'q50': {h: v}, 'q95': {h: v}}}
      (also tolerates 'q5' for 5%)
    """
    rows: List[Tuple[str, int, float, float, float]] = []
    for ind, sub in quantiles.items():
        if not isinstance(sub, dict):
            continue

        # Detect shape B (top-level keys look like quantiles)
        top_keys = {str(k).lower() for k in sub.keys()}
        looks_like_q_top = top_keys.issubset({"q5", "q05", "q50", "q95"})

        if looks_like_q_top:
            q05_map = sub.get("q05", sub.get("q5", {})) or {}
            q50_map = sub.get("q50", {}) or {}
            q95_map = sub.get("q95", {}) or {}
            # Iterate horizons from union of keys
            all_h = set(q05_map.keys()) | set(q50_map.keys()) | set(q95_map.keys())
            for h in sorted(all_h, key=lambda x: _parse_horizon(x)):
                hh = _parse_horizon(h)
                q05 = float(q05_map.get(h, np.nan))
                q50 = float(q50_map.get(h, np.nan))
                q95 = float(q95_map.get(h, np.nan))
                rows.append((ind, hh, q05, q50, q95))
        else:
            # Shape A: horizon -> quantiles dict
            for h, q in sub.items():
                try:
                    hh = _parse_horizon(h)
                except ValueError:
                    # If this "h" is actually 'q5' etc because of mixed shapes, skip here.
                    continue
                if isinstance(q, dict):
                    q05 = float(q.get("q05", q.get("q5", np.nan)))
                    q50 = float(q.get("q50", np.nan))
                    q95 = float(q.get("q95", np.nan))
                else:
                    # If a scalar slipped through, put it as median
                    q05 = np.nan
                    q50 = float(q)
                    q95 = np.nan
                rows.append((ind, hh, q05, q50, q95))

    df = pd.DataFrame(rows, columns=["indicator", "horizon", "q05", "q50", "q95"])
    df = df.sort_values(["indicator", "horizon"]).reset_index(drop=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def save_json(obj, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)