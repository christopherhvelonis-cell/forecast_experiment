#!/usr/bin/env python3
"""
Build equal-weight weights from quantiles_by_model.csv.

Outputs:
  ensemble/weights_equal.csv with columns:
  indicator,horizon,origin_year,model,weight
"""
import os, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "eval", "results")
QBM = os.path.join(RES, "quantiles_by_model.csv")
OUT = os.path.join(ROOT, "ensemble", "weights_equal.csv")

def main():
    if not os.path.exists(QBM):
        raise SystemExit(f"[error] missing {os.path.relpath(QBM, ROOT)}")
    q = pd.read_csv(QBM)
    need = {"indicator","horizon","origin_year","model"}
    if not need.issubset(q.columns):
        raise SystemExit(f"[error] quantiles_by_model missing {need}")
    # keep unique model list per (ind,h,oy)
    g = (q.drop_duplicates(subset=["indicator","horizon","origin_year","model"])
           .groupby(["indicator","horizon","origin_year"]))
    rows = []
    for (ind,h,oy), df in g:
        mlist = sorted(df["model"].astype(str).unique())
        if not mlist: 
            continue
        w = 1.0/len(mlist)
        for m in mlist:
            rows.append(dict(indicator=str(ind), horizon=int(h), origin_year=int(oy),
                             model=str(m), weight=float(w)))
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[ok] wrote {OUT}  rows={len(out)}")

if __name__ == "__main__":
    main()
