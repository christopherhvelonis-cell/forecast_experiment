from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
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
    if ren:
        df = df.rename(columns=ren)
    return df

def main():
    ap = argparse.ArgumentParser(description='Shift quantiles by mean residual (truth - q50) over scored horizons.')
    ap.add_argument('--calibrated_csv', required=True)
    ap.add_argument('--truth_csv', required=True)
    ap.add_argument('--indicator', required=True)
    ap.add_argument('--origin', type=int, required=True)
    ap.add_argument('--h', type=int, required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    qdf = _norm_cols(pd.read_csv(args.calibrated_csv))
    tdf = _norm_cols(pd.read_csv(args.truth_csv))

    if 'year' not in tdf.columns:
        if 'date' in tdf.columns:
            tdf['year'] = pd.to_datetime(tdf['date'], errors='coerce').dt.year
        else:
            raise SystemExit('truth_csv must have a year or date column')

    qsub = qdf[qdf['indicator'] == args.indicator].copy()
    if qsub.empty:
        raise SystemExit(f'No rows for indicator {args.indicator!r} in calibrated_csv')

    rows = []
    for k in range(1, args.h + 1):
        y = args.origin + k
        r = qsub[qsub['horizon'] == k]
        t = tdf[tdf['year'].astype('Int64') == y]
        if r.empty or t.empty:
            continue
        rows.append(dict(year=y, q50=float(r['q50'].values[0]), truth=float(t['value'].values[0])))

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit('No overlap between forecast horizons and truth years.')

    delta = float((df['truth'] - df['q50']).mean())  # mean residual
    for col in ('q5','q50','q95'):
        qsub[col] = qsub[col] + delta

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    outdf = pd.concat([qdf[qdf['indicator'] != args.indicator], qsub], ignore_index=True)
    outdf.to_csv(out_path, index=False)
    print(f'[bias] indicator={args.indicator} delta={delta:.6f}')
    print(f'[bias] wrote: {out_path}')

if __name__ == '__main__':
    main()
