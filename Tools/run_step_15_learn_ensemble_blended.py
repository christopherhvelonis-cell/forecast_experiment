#!/usr/bin/env python3
import os, argparse, numpy as np, pandas as pd
from sklearn.linear_model import Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

def softmax(x, T=1.0):
    x = np.asarray(x, float)
    z = (x - np.max(x)) / max(1e-8, float(T))
    e = np.exp(z); s = e.sum()
    return e/s if s>0 else np.ones_like(e)/len(e)

def _select_numeric_features(df):
    keep=[c for c in df.columns
          if c not in {"indicator","horizon","origin_year","model"}
          and pd.api.types.is_numeric_dtype(df[c])]
    return df[keep].copy()

def equal_weights(models):
    m = sorted(models)
    if not m: return pd.DataFrame(columns=["model","w_eq"])
    return pd.DataFrame({"model": m, "w_eq": [1.0/len(m)]*len(m)})

def learn_group_weights(feat_g, perf_mean_by_model, model_kind="ridge", T=1.0):
    """
    feat_g: features for ONE (indicator,horizon,origin_year), rows per model
    perf_mean_by_model: DataFrame[model, composite] averaged over train years
    returns DataFrame(model, w_meta)
    """
    models = sorted(set(feat_g["model"].astype(str)) & set(perf_mean_by_model["model"].astype(str)))
    if not models: return None

    # targets (lower is better)
    pm = perf_mean_by_model.set_index("model").loc[models]
    if "composite" not in pm.columns:
        return None
    y = pm["composite"].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    models_y = y.index.tolist()
    if not models_y:  # no valid targets
        return None

    X = feat_g.set_index("model").loc[models_y]
    Xn = _select_numeric_features(X)

    # If no numeric features, score all equally (softmax -> equal)
    if Xn.empty:
        scores = np.ones(len(models_y))
    else:
        # Impute missing features with median within this group, then scale
        imp = SimpleImputer(strategy="median")
        X_imp = imp.fit_transform(Xn.to_numpy())
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X_imp)

        target = -y.to_numpy()  # larger is better
        if model_kind == "lasso":
            reg = Lasso(alpha=0.1, max_iter=10000)
        else:
            reg = Ridge(alpha=1.0, random_state=42)
        reg.fit(Xs, target)
        scores = reg.predict(Xs)

    w_meta = softmax(scores, T=T)
    return pd.DataFrame({"model": models_y, "w_meta": w_meta})

def cv_score_for(feats, perf, T, alpha, model_kind):
    """
    Leave-one-origin-year-out within each (indicator,horizon)
    """
    scores=[]
    for (ind,h), gperf in perf.groupby(["indicator","horizon"]):
        years = sorted(gperf["origin_year"].unique())
        for oy in years:
            train=gperf[gperf["origin_year"]!=oy]; test=gperf[gperf["origin_year"]==oy]
            if train.empty or test.empty: continue
            f_test = feats[(feats["indicator"]==ind)&(feats["horizon"]==h)&(feats["origin_year"]==oy)]
            if f_test.empty: continue
            p_tr_mean = train.groupby("model", as_index=False)["composite"].mean()
            wm = learn_group_weights(f_test, p_tr_mean, model_kind=model_kind, T=T)
            if wm is None or wm.empty: continue
            weq = equal_weights(wm["model"])
            w = wm.merge(weq, on="model", how="inner")
            w["weight"] = (1.0 - alpha)*w["w_eq"] + alpha*w["w_meta"]
            test_m = test.merge(w[["model","weight"]], on="model", how="inner")
            if test_m.empty: continue
            scores.append(float((test_m["composite"]*test_m["weight"]).sum()))
    return np.mean(scores) if scores else np.inf

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--model", choices=["ridge","lasso"], default="ridge")
    ap.add_argument("--temps", nargs="+", type=float, default=[0.5,1,2,5,10])
    ap.add_argument("--alphas", nargs="+", type=float, default=[0.2,0.4,0.6])
    ap.add_argument("--out", required=True)
    args=ap.parse_args()

    feats=pd.read_csv(args.features)
    perf=pd.read_csv(args.metrics)

    # Normalize & keep only needed columns; drop any rows with NaN composite
    needf={"indicator","horizon","origin_year","model"}
    needp={"indicator","horizon","origin_year","model","composite"}
    if not needf.issubset(feats.columns):
        raise SystemExit(f"[error] features missing {needf}")
    if not needp.issubset(perf.columns):
        raise SystemExit(f"[error] metrics missing {needp}")

    for c, typ in [("indicator",str), ("horizon",int), ("origin_year",int), ("model",str)]:
        feats[c] = feats[c].astype(typ)
        perf[c]  = perf[c].astype(typ)

    perf = perf.copy()
    perf["composite"] = pd.to_numeric(perf["composite"], errors="coerce")
    perf = perf.dropna(subset=["composite"])

    # Grid search T x alpha
    best=(None,None,np.inf)
    for T in args.temps:
        for a in args.alphas:
            s=cv_score_for(feats, perf, T, a, args.model)
            if s<best[2]:
                best=(T,a,s)

    Tstar, astar, sstar = best
    if not np.isfinite(sstar):
        # Fail-safe to equal-weight
        Tstar, astar = 1.0, 0.0
        print("[cv] no valid folds; falling back to equal-weight (T=1.0, alpha=0.0)")
    else:
        print(f"[cv] best T={Tstar} alpha={astar} mean_loss={sstar:.6f}")

    rows=[]
    for (ind,h,oy), g in feats.groupby(["indicator","horizon","origin_year"]):
        p_g = perf[(perf["indicator"]==ind)&(perf["horizon"]==h)]
        if p_g.empty: continue
        p_mean = p_g.groupby("model", as_index=False)["composite"].mean()
        wm = learn_group_weights(g, p_mean, model_kind=args.model, T=Tstar)
        if wm is None or wm.empty:
            # equal-weight fallback for this group
            mods = sorted(p_mean["model"].astype(str).unique().tolist())
            weq = equal_weights(mods)
            wdf = weq.rename(columns={"w_eq":"weight"})
        else:
            weq = equal_weights(wm["model"])
            wdf = wm.merge(weq, on="model", how="inner")
            wdf["weight"] = (1.0 - astar)*wdf["w_eq"] + astar*wdf["w_meta"]

        for _, r in wdf.iterrows():
            rows.append(dict(indicator=str(ind), horizon=int(h), origin_year=int(oy),
                             model=str(r["model"]), weight=float(r["weight"])))

    out=pd.DataFrame(rows)
    if out.empty:
        # global fallback: equal-weight everywhere from perf
        base=perf.groupby(["indicator","horizon","origin_year"])["model"].unique().reset_index()
        rr=[]
        for _, r in base.iterrows():
            mods=sorted(map(str, r["model"])); w=1.0/len(mods) if mods else 0.0
            for m in mods:
                rr.append(dict(indicator=str(r["indicator"]), horizon=int(r["horizon"]),
                               origin_year=int(r["origin_year"]), model=m, weight=w))
        out=pd.DataFrame(rr)
        print("[warn] produced no learned weights; wrote equal-weight fallback.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[ok] wrote {args.out} rows={len(out)}")

if __name__=="__main__": main()
