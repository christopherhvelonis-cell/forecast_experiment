# verify_calibrated_cli.py
from __future__ import annotations
import argparse, math
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd

DATA_DIR = Path(r'C:\Users\Owner\Downloads\forecast_experiment\data\processed')
Z90 = 1.6448536269514722  # Phi^{-1}(0.95)
Z50 = 0.6744897501960817  # Phi^{-1}(0.75)

def _normalize_qdf(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    ren = {}
    if 'h' in df.columns and 'horizon' not in df.columns: ren['h'] = 'horizon'
    if 'q05' in df.columns and 'q5' not in df.columns: ren['q05'] = 'q5'
    if 'p5' in df.columns and 'q5' not in df.columns: ren['p5'] = 'q5'
    if 'p95' in df.columns and 'q95' not in df.columns: ren['p95'] = 'q95'
    if 'q0.5' in df.columns and 'q50' not in df.columns: ren['q0.5'] = 'q50'
    if 'median' in df.columns and 'q50' not in df.columns: ren['median'] = 'q50'
    if 'variable' in df.columns and 'indicator' not in df.columns: ren['variable'] = 'indicator'
    if 'series' in df.columns and 'indicator' not in df.columns: ren['series'] = 'indicator'
    if ren: df = df.rename(columns=ren)
    expected = {'indicator','horizon','q5','q50','q95'}
    miss = [c for c in expected if c not in df.columns]
    if miss:
        raise ValueError(f'Calibrated CSV must have {sorted(expected)}; missing {miss}. Got {df.columns.tolist()}')
    df['horizon'] = pd.to_numeric(df['horizon'], errors='coerce').astype(int)
    for c in ['q5','q50','q95']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def _extract_year_series(df: pd.DataFrame) -> pd.Series:
    if 'year' in df.columns:
        y = pd.to_numeric(df['year'], errors='coerce')
        if y.notna().sum() > 1 and y.nunique() > 1:
            return y
    for c in df.columns:
        if c == 'year': continue
        if df[c].dtype == 'O':
            s = df[c].astype(str)
            m = s.str.extract(r'^(?P<y>\d{4})(?:[-/]\d{1,2})?(?:[-/]\d{1,2})?$', expand=True)
            y = pd.to_numeric(m['y'], errors='coerce')
            if y.notna().sum() > 1 and y.nunique() > 1:
                return y
    for cand in ['date','period','time','year_month','year_quarter']:
        if cand in df.columns:
            y = pd.to_datetime(df[cand], errors='coerce').dt.year
            if y.notna().sum() > 1 and y.nunique() > 1:
                return y
    for c in df.columns:
        y = pd.to_datetime(df[c], errors='coerce').dt.year
        if y.notna().sum() > 1 and y.nunique() > 1:
            return y
    return pd.to_datetime(df.index, errors='coerce').year

def _load_truth(indicator: str) -> pd.DataFrame:
    path = DATA_DIR / f'{indicator}.csv'
    if not path.exists():
        raise FileNotFoundError(f"Truth series not found for '{indicator}': {path}")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    y = _extract_year_series(df)
    y = pd.to_numeric(y, errors='coerce')
    value_col = 'value'
    if value_col not in df.columns:
        if indicator.lower() in df.columns:
            value_col = indicator.lower()
        else:
            numc = [c for c in df.columns if c != 'year' and pd.api.types.is_numeric_dtype(df[c])]
            value_col = numc[0] if numc else df.columns[-1]
    out = pd.DataFrame({'year': y, 'value': pd.to_numeric(df[value_col], errors='coerce')})
    out = out.dropna(subset=['year','value']).astype({'year': int}).sort_values('year').reset_index(drop=True)
    return out

def _phi(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(lambda t: math.erf(t / math.sqrt(2.0)))(x))

def main():
    ap = argparse.ArgumentParser(description='Verify PIT & coverage for calibrated quantiles.')
    ap.add_argument('--calibrated_csv', required=True, help='Calibrated quantiles CSV (indicator,horizon,q5,q50,q95).')
    ap.add_argument('--indicators', nargs='+', required=True, help='Indicators list.')
    ap.add_argument('--origin', type=int, required=True, help='Origin year for scored horizons.')
    ap.add_argument('--h', type=int, default=15, help='Max scored horizon.')
    ap.add_argument('--out_dir', required=True, help='Directory to write outputs.')
    args = ap.parse_args()

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    qdf = _normalize_qdf(pd.read_csv(args.calibrated_csv))

    pit_rows: List[dict] = []
    cov_rows: List[dict] = []

    for ind in args.indicators:
        sub = qdf[qdf['indicator'] == ind]
        if sub.empty:
            continue
        truth = _load_truth(ind)
        for k in range(1, args.h + 1):
            y_year = args.origin + k
            row = sub[sub['horizon'] == k]
            if row.empty:
                continue
            trow = truth[truth['year'] == y_year]
            if trow.empty:
                continue
            y_true = float(trow['value'].values[0])
            q50 = float(row['q50'].values[0]); q95 = float(row['q95'].values[0])

            sigma = max(1e-8, (q95 - q50) / Z90)
            z = (y_true - q50) / sigma
            pit = float(_phi(np.array([z]))[0])
            pit_rows.append(dict(indicator=ind, year=y_year, horizon=k, pit=pit))

            lo50 = q50 - Z50 * sigma; hi50 = q50 + Z50 * sigma
            covered50 = int(min(lo50, hi50) <= y_true <= max(lo50, hi50))
            cov_rows.append(dict(indicator=ind, year=y_year, horizon=k, level=0.50, covered=covered50))

            lo90 = q50 - Z90 * sigma; hi90 = q50 + Z90 * sigma
            covered90 = int(min(lo90, hi90) <= y_true <= max(lo90, hi90))
            cov_rows.append(dict(indicator=ind, year=y_year, horizon=k, level=0.90, covered=covered90))

    pd.DataFrame(pit_rows, columns=['indicator','year','horizon','pit']).to_csv(out_dir / 'pit_values_calibrated.csv', index=False)
    cov_df = pd.DataFrame(cov_rows, columns=['indicator','year','horizon','level','covered'])
    cov_df.to_csv(out_dir / 'coverage_points_calibrated.csv', index=False)

    if not cov_df.empty:
        summary = (cov_df.groupby(['indicator','level'], as_index=False)['covered']
                   .agg(total='count', covered='sum'))
        summary['coverage_rate'] = summary['covered'] / summary['total'].replace({0: np.nan})
        summary = summary[['indicator','level','covered','total','coverage_rate']]
    else:
        summary = pd.DataFrame(columns=['indicator','level','covered','total','coverage_rate'])

    summary.to_csv(out_dir / 'coverage_summary_calibrated.csv', index=False)
    print(f"[verify] wrote:\n  - {out_dir / 'pit_values_calibrated.csv'}\n  - {out_dir / 'coverage_points_calibrated.csv'}\n  - {out_dir / 'coverage_summary_calibrated.csv'}")

if __name__ == '__main__':
    main()
