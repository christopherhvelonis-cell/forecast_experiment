#!/usr/bin/env python3
"""
Tools/run_step_15_learn_ensemble.py  (small-data safe)

FFORMA-style learner with robust fallbacks:
- If a fold has too few rows -> equal-weights for that fold.
- If ALL folds are too small (no validation rows) -> global equal-weights
  for every (indicator,horizon,origin_year) group found in the merged data.

Inputs:
  --features eval/results/stacking_features.csv
    (indicator,horizon,origin_year,...features)
  --metrics  eval/results/perf_by_model.csv
    (indicator,horizon,origin_year,model,metric,loss)

Output:
  ensemble/weights_learned.csv
"""

import argparse, os, sys, json, random
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def parse_args():
    p = argparse.ArgumentParser(description="Learn feature-based ensemble weights (FFORMA-style).")
    p.add_argument("--features", default="eval/results/stacking_features.csv")
    p.add_argument("--metrics",  default="eval/results/perf_by_model.csv")
    p.add_argument("--metric",   default="composite", choices=["composite","crps","brier"])
    p.add_argument("--model",    default="ridge", choices=["ridge","gbrt"])
    p.add_argument("--alphas", nargs="*", type=float, default=[0.01,0.1,1.0,10.0,100.0])
    p.add_argument("--gbrt_params", type=str,
                   default='{"n_estimators":400,"max_depth":3,"learning_rate":0.05,"min_samples_leaf":5}')
    p.add_argument("--temperature_grid", nargs="*", type=float, default=[1.0])
    p.add_argument("--min_train_rows", type=int, default=20,  # lower for small datasets
                   help="Minimum training rows per fold; else equal-weight fallback.")
    p.add_argument("--out", default="ensemble/weights_learned.csv")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()

def softmax_neg_loss(losses, T=1.0):
    z = -np.array(losses, dtype=float) / max(1e-8, T)
    z -= np.max(z)
    e = np.exp(z)
    return e / e.sum()

def build_model(kind, alphas, gbrt_params, seed):
    if kind == "ridge":
        return Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("ridge", RidgeCV(alphas=alphas, store_cv_values=False))
        ])
    else:
        params = json.loads(gbrt_params)
        return Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("gbrt", GradientBoostingRegressor(random_state=seed, **params))
        ])

def choose_temperature(val_df, temps):
    if val_df.empty or len(temps) == 1:
        return temps[0] if temps else 1.0
    best_T, best_score = temps[0], float("inf")
    for T in temps:
        scores = []
        for _, g in val_df.groupby(["indicator","horizon","origin_year"]):
            true = g["true_loss"].to_numpy()
            pred = g["pred_loss"].to_numpy()
            w = softmax_neg_loss(pred, T)
            scores.append(float(np.sum(w * true)))
        if scores:
            s = float(np.mean(scores))
            if s < best_score:
                best_score, best_T = s, T
    return best_T

def main():
    args = parse_args()
    random.seed(args.seed); np.random.seed(args.seed)

    feats = pd.read_csv(args.features)
    perf  = pd.read_csv(args.metrics)

    perf = perf[perf["metric"].str.lower() == args.metric.lower()].copy()
    merged = perf.merge(feats, on=["indicator","horizon","origin_year"], how="inner", validate="many_to_one")
    if merged.empty:
        raise SystemExit("[error] Join produced no rows; check indicator/horizon/origin_year alignment.")

    key_cols = {"indicator","horizon","origin_year","model","metric","loss"}
    feature_cols = [c for c in merged.columns if c not in key_cols]

    years = sorted(merged["origin_year"].unique())
    model_names = sorted(merged["model"].unique())

    val_rows, out_records = [], []

    # Rolling folds
    for oy in years:
        train_df = merged[merged["origin_year"] < oy]
        test_df  = merged[merged["origin_year"] == oy]

        if len(train_df) < args.min_train_rows or train_df["indicator"].nunique() < 1:
            # equal-weights for this origin_year
            for (ind,h), g in test_df.groupby(["indicator","horizon"]):
                mlist = g["model"].tolist()
                if not mlist: continue
                w = np.ones(len(mlist))/len(mlist)
                for m, ww in zip(mlist, w):
                    out_records.append(dict(indicator=ind,horizon=int(h),origin_year=int(oy),
                                            model=m,weight=float(ww),metric=args.metric,
                                            method="equal_weight_fallback",temperature=1.0,seed=args.seed))
            continue

        # fit per-model predictors
        predictors = {}
        for m in model_names:
            tr = train_df[train_df["model"]==m]
            if tr.empty: continue
            X, y = tr[feature_cols].to_numpy(), tr["loss"].to_numpy()
            mdl = build_model(args.model, args.alphas, args.gbrt_params, args.seed)
            mdl.fit(X, y)
            predictors[m] = mdl

        # validation predictions for this fold
        for (ind,h), g in test_df.groupby(["indicator","horizon"]):
            Xg = g[feature_cols].to_numpy()
            true_losses, pred_losses = g["loss"].to_numpy(), []
            models = g["model"].tolist()
            grp_mean = float(true_losses.mean()) if len(true_losses) else 0.0
            for row, m in zip(Xg, models):
                pred = predictors[m].predict([row])[0] if m in predictors else grp_mean
                pred_losses.append(pred)
            for m, tl, pl in zip(models, true_losses, pred_losses):
                val_rows.append(dict(indicator=ind,horizon=int(h),origin_year=int(oy),
                                     model=m,true_loss=float(tl),pred_loss=float(pl)))

    val_df = pd.DataFrame(val_rows)

    # If no validation rows at all -> global equal-weights for all groups
    if val_df.empty:
        eq_records = []
        for (ind,h,oy), g in merged.groupby(["indicator","horizon","origin_year"]):
            models = sorted(g["model"].unique().tolist())
            w = np.ones(len(models))/len(models)
            for m, ww in zip(models, w):
                eq_records.append(dict(indicator=ind,horizon=int(h),origin_year=int(oy),
                                       model=m,weight=float(ww),metric=args.metric,
                                       method="equal_weight_global_fallback",temperature=1.0,seed=args.seed))
        out = pd.DataFrame(eq_records)
        out["weight"] = out.groupby(["indicator","horizon","origin_year"])["weight"].transform(lambda x: x/x.sum())
        out["created_utc"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        out.to_csv(args.out, index=False)
        print(f"[ok] Wrote learned weights to {args.out} (global equal-weight fallback), rows={len(out)}")
        return 0

    T_opt = choose_temperature(val_df, args.temperature_grid)

    # Create weights from predictions
    final_records = out_records[:]  # include any fold-level equal-weight fallbacks already produced
    for (ind,h,oy), g in val_df.groupby(["indicator","horizon","origin_year"]):
        w = softmax_neg_loss(g["pred_loss"].to_numpy(), T_opt)
        for m, ww in zip(g["model"], w):
            final_records.append(dict(indicator=ind,horizon=int(h),origin_year=int(oy),
                                      model=m,weight=float(ww),metric=args.metric,
                                      method=f"{args.model}_fforma",temperature=float(T_opt),seed=args.seed))

    out = pd.DataFrame(final_records)
    out = out.groupby(["indicator","horizon","origin_year","model","metric","method","temperature","seed"], as_index=False)["weight"].sum()
    out["weight"] = out.groupby(["indicator","horizon","origin_year"])["weight"].transform(lambda x: x/x.sum())
    out["created_utc"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[ok] Wrote learned weights to {args.out}, rows={len(out)}")
    print(f"[info] Chosen temperature = {T_opt}")
    return 0

if __name__ == "__main__":
    import numpy as np
    sys.exit(main())
