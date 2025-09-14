#!/usr/bin/env python
import argparse, os, pandas as pd, numpy as np

def detect_cols(df):
    have = set(df.columns)
    q50 = "q50" if "q50" in have else None
    q05 = "q05" if "q05" in have else ("q5" if "q5" in have else None)
    q95 = "q95" if "q95" in have else None
    lo50 = "lo_50" if "lo_50" in have else ("q25" if "q25" in have else None)
    hi50 = "hi_50" if "hi_50" in have else ("q75" if "q75" in have else None)
    return q50, q05, q95, lo50, hi50

def overlap(loA, hiA, loB, hiB):
    if any(pd.isna([loA,hiA,loB,hiB])): return np.nan
    return 1.0 if (max(loA,loB) <= min(hiA,hiB)) else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.ensemble_csv)
    needed = {"indicator","horizon"}
    if not needed.issubset(df.columns):
        raise ValueError("Need columns indicator,horizon in ensemble CSV")

    q50,q05,q95,lo50,hi50 = detect_cols(df)
    if q50 is None: raise ValueError("Need q50 in ensemble CSV")
    if q05 is None or q95 is None:
        print("[overlap] q05/q95 not found; 90% metrics will be NaN.")
    if lo50 is None or hi50 is None:
        print("[overlap] 50% band edges not found; 50% metrics will be NaN.")

    inds = sorted(df["indicator"].unique().tolist())
    if len(inds) < 2:
        raise ValueError(f"Need at least 2 indicators; found {inds}")

    rows=[]
    for i in range(len(inds)):
        for j in range(i+1,len(inds)):
            A,B = inds[i],inds[j]
            da = df[df.indicator==A].set_index("horizon").sort_index()
            db = df[df.indicator==B].set_index("horizon").sort_index()
            common = da.index.intersection(db.index)
            if len(common)==0: continue
            da = da.loc[common]; db = db.loc[common]

            # median direction agree from first to last common horizon
            h1, hL = common.min(), common.max()
            dirA = np.sign(da.loc[hL,q50] - da.loc[h1,q50])
            dirB = np.sign(db.loc[hL,q50] - db.loc[h1,q50])
            dir_agree = 1.0 if (dirA==dirB) else 0.0

            # 50% band overlap share
            if lo50 and hi50:
                ov50 = []
                for h in common:
                    ov50.append(overlap(da.loc[h,lo50], da.loc[h,hi50],
                                        db.loc[h,lo50], db.loc[h,hi50]))
                ov50 = [x for x in ov50 if not np.isnan(x)]
                ov50_share = float(np.mean(ov50)) if len(ov50)>0 else np.nan
            else:
                ov50_share = np.nan

            # 90% band overlap share (via q05/q95)
            if q05 and q95:
                ov90 = []
                for h in common:
                    ov90.append(overlap(da.loc[h,q05], da.loc[h,q95],
                                        db.loc[h,q05], db.loc[h,q95]))
                ov90 = [x for x in ov90 if not np.isnan(x)]
                ov90_share = float(np.mean(ov90)) if len(ov90)>0 else np.nan
            else:
                ov90_share = np.nan

            rows.append({
                "indicator_A": A,
                "indicator_B": B,
                "median_dir_agree": dir_agree,
                "band_overlap_50": ov50_share,
                "band_overlap_90": ov90_share,
                "h_first": int(h1),
                "h_last": int(hL)
            })

    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print(f"[overlap] wrote {args.out_csv} rows={len(out)}")

if __name__ == "__main__":
    main()
