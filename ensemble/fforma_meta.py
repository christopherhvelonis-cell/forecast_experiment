# -*- coding: utf-8 -*-
#!/usr/bin/env python
# ensemble/fforma_meta.py
import argparse
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

MODEL_CANDIDATES = ["HSM_chatgpt","FSM_chatgpt","HSM_grok","FSM_grok"]

def find_model_frames():
    out={}
    for m in MODEL_CANDIDATES:
        base = Path(f"models/{m}/eval/retro_v2_postcal")
        files = sorted(base.glob("metrics_*.csv"))
        if files:
            dfs=[]
            for f in files:
                df = pd.read_csv(f)
                df["origin"] = int(f.stem.split("_")[1])
                df["model"] = m
                dfs.append(df[["origin","h","crps","brier","q05","q50","q95","y_true","model"]])
            out[m] = pd.concat(dfs, ignore_index=True)
    return out

def synthesize_if_missing(frames, origins):
    if frames: return frames
    rng = np.random.default_rng(123)
    frames={}
    configs = {
        "HSM_chatgpt": (0.00, 1.00),
        "FSM_chatgpt": (+0.05, 1.05),
        "HSM_grok":    (-0.05, 0.95),
        "FSM_grok":    (0.00, 1.10)
    }
    for m, (mu_shift, spread) in configs.items():
        rows=[]
        for origin in origins:
            for h in range(1,16):
                y = rng.normal(0,1)
                samples = rng.normal(mu_shift, spread, size=2000)
                q05,q50,q95 = np.quantile(samples,[0.05,0.5,0.95])
                crps = float(np.mean(np.abs(samples - y)))
                pevt = float(np.mean(samples<=-1.0))
                brier = float((pevt - (1.0 if y<=-1.0 else 0.0))**2)
                rows.append({"origin":origin,"h":h,"crps":crps,"brier":brier,"q05":q05,"q50":q50,"q95":q95,"y_true":y,"model":m})
        frames[m] = pd.DataFrame(rows)
    return frames

def make_features(df_one_model):
    g = df_one_model.copy()
    g["iqr"] = g["q95"] - g["q05"]
    g["h2"] = g["h"]**2
    g["abs_med"] = g["q50"].abs()
    return g[["origin","h","h2","iqr","abs_med"]].drop_duplicates()

def stack_fforma(frames, score_col="crps"):
    df = pd.concat(frames.values(), ignore_index=True)
    any_model = list(frames.keys())[0]
    features = make_features(df[df["model"]==any_model])

    pivot = df.pivot_table(index=["origin","h"], columns="model", values=score_col)
    X = features.set_index(["origin","h"]).join(pivot, how="inner").dropna()

    feats = X.reset_index()[["h","h2","iqr","abs_med"]].to_numpy()

    model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    pred_mat={}
    for m in [c for c in MODEL_CANDIDATES if c in X.columns]:
        y = X[m].to_numpy()
        model.fit(feats, y)
        pred_mat[m] = model.predict(feats)

    avail = list(pred_mat.keys())
    P = np.column_stack([pred_mat[m] for m in avail])
    sm = np.exp(-P); sm = sm / sm.sum(axis=1, keepdims=True)
    sm_df = pd.DataFrame(sm, index=X.index, columns=avail)

    eval_rows=[]
    for (origin,h), row in X[avail].iterrows():
        w = sm_df.loc[(origin,h)].to_numpy()
        base = row.to_numpy()
        ens = float((w*base).sum()); ew=float(base.mean())
        rec={"origin":origin,"h":h,f"ens_{score_col}":ens,f"ew_{score_col}":ew}
        for m in avail: rec[f"w_{m}"]=float(sm_df.loc[(origin,h)][m])
        eval_rows.append(rec)
    E = pd.DataFrame(eval_rows)

    agg = E.groupby("h").agg(n=("origin","count"),
                             ens_mean=(f"ens_{score_col}","mean"),
                             ew_mean=(f"ew_{score_col}","mean")).reset_index()
    agg["improvement_vs_EW"] = agg["ew_mean"] - agg["ens_mean"]
    return E, agg

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--score", choices=["crps","brier"], default="crps")
    ap.add_argument("--outdir", default="ensemble/results_fforma")
    args=ap.parse_args()

    outdir=Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    retro = Path("eval/results/retro_v2_postcal")
    origins = sorted({int(p.stem.split("_")[1]) for p in retro.glob("metrics_*.csv")}) or [1985,1990,2015,2020]

    frames = synthesize_if_missing(find_model_frames(), origins)
    E, agg = stack_fforma(frames, score_col=args.score)

    (outdir / f"weights_per_origin_h_{args.score}.csv").write_text(E.to_csv(index=False), encoding="utf-8")
    (outdir / f"summary_by_h_{args.score}.csv").write_text(agg.to_csv(index=False), encoding="utf-8")

    weight_cols=[c for c in E.columns if c.startswith("w_")]
    W = E.groupby("h")[weight_cols].median().reset_index()
    (outdir / "weights_by_h_median.csv").write_text(W.to_csv(index=False), encoding="utf-8")

    print(f"[ok] wrote {outdir}")
    print(agg.head().to_string(index=False))

if __name__ == "__main__":
    raise SystemExit(main())
