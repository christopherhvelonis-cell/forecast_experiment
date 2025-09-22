#!/usr/bin/env python3
"""
Apply learned weights to per-model forecasts.

Inputs:
  --weights   ensemble/weights_learned.csv
  --quantiles eval/results/quantiles_by_model.csv
              (indicator,horizon,origin_year,model,quantile,value)
  --events    eval/results/event_probs_by_model.csv  [optional]
              (indicator,horizon,origin_year,model,event,prob)

Outputs:
  ensemble/quantiles_ensemble.csv
  ensemble/event_probs_ensemble.csv  [if events provided]
"""

import argparse, os
import pandas as pd

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="ensemble/weights_learned.csv")
    p.add_argument("--quantiles", default="eval/results/quantiles_by_model.csv")
    p.add_argument("--events", default="eval/results/event_probs_by_model.csv")
    p.add_argument("--out_quantiles", default="ensemble/quantiles_ensemble.csv")
    p.add_argument("--out_events", default="ensemble/event_probs_ensemble.csv")
    p.add_argument("--method_tag", default="meta_stack_linear_pool")
    return p.parse_args()

def coerce_q(q):
    try: return float(q)
    except: 
        s = str(q).lower().lstrip('q')
        return float(s)

def main():
    a = parse_args()
    w = pd.read_csv(a.weights)
    for c in ["indicator","horizon","origin_year","model","weight"]:
        if c not in w.columns:
            raise SystemExit(f"[error] weights missing {c}")

    q = pd.read_csv(a.quantiles)
    need_q = {"indicator","horizon","origin_year","model","quantile","value"}
    if not need_q.issubset(q.columns):
        miss = need_q - set(q.columns)
        raise SystemExit(f"[error] quantiles missing {miss}")
    q = q.copy()
    q["quantile"] = q["quantile"].apply(coerce_q)

    # join and normalize weights over available models per group+quantile
    key = ["indicator","horizon","origin_year","model"]
    mq = q.merge(w[key+["weight"]], on=key, how="inner")
    if mq.empty:
        raise SystemExit("[error] No overlap between weights and model quantiles.")
    mq["weight"] = mq.groupby(["indicator","horizon","origin_year","quantile"])["weight"] \
                     .transform(lambda s: s / max(1e-12, s.sum()))
    ens_q = (mq.assign(wv=lambda df: df["weight"]*df["value"])
                .groupby(["indicator","horizon","origin_year","quantile"], as_index=False)["wv"]
                .sum()
                .rename(columns={"wv":"value"})
                .sort_values(["indicator","horizon","origin_year","quantile"]))
    ens_q["method"] = a.method_tag
    ens_q["created_utc"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(a.out_quantiles), exist_ok=True)
    ens_q.to_csv(a.out_quantiles, index=False)
    print(f"[ok] wrote {a.out_quantiles} rows={len(ens_q)}")

    # optional events
    try:
        ev = pd.read_csv(a.events)
        need_e = {"indicator","horizon","origin_year","model","event","prob"}
        if need_e.issubset(ev.columns) and not ev.empty:
            me = ev.merge(w[key+["weight"]], on=key, how="inner")
            if not me.empty:
                me["weight"] = me.groupby(["indicator","horizon","origin_year","event"])["weight"] \
                                 .transform(lambda s: s / max(1e-12, s.sum()))
                ens_e = (me.assign(wp=lambda df: df["weight"]*df["prob"])
                           .groupby(["indicator","horizon","origin_year","event"], as_index=False)["wp"]
                           .sum()
                           .rename(columns={"wp":"prob"})
                           .sort_values(["indicator","horizon","origin_year","event"]))
                ens_e["method"] = a.method_tag
                ens_e["created_utc"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
                ens_e.to_csv(a.out_events, index=False)
                print(f"[ok] wrote {a.out_events} rows={len(ens_e)}")
            else:
                print("[info] no overlap between weights and event probs; skipped events.")
        else:
            print("[info] event file missing or lacks required columns; skipped events.")
    except FileNotFoundError:
        print("[info] event file not found; skipped events.")

if __name__ == "__main__":
    main()
