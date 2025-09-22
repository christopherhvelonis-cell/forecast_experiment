#!/usr/bin/env python3
import os, sys, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W_LEARNED = os.path.join(ROOT, "ensemble", "weights_learned.csv")
W_EQ      = os.path.join(ROOT, "ensemble", "weights_equal.csv")
OUT       = W_LEARNED  # overwrite if empty

def main():
    if not os.path.exists(W_LEARNED):
        print("[info] no learned weights found; using equal-weight.")
        if not os.path.exists(W_EQ):
            raise SystemExit("[error] weights_equal.csv missing; run Tools/make_equal_weight_weights.py")
        pd.read_csv(W_EQ).to_csv(OUT, index=False)
        print(f"[ok] wrote fallback -> {OUT}")
        return
    df = pd.read_csv(W_LEARNED)
    if df.empty or not {"indicator","horizon","origin_year","model","weight"}.issubset(df.columns):
        print("[info] learned weights empty/invalid; using equal-weight.")
        if not os.path.exists(W_EQ):
            raise SystemExit("[error] weights_equal.csv missing; run Tools/make_equal_weight_weights.py")
        pd.read_csv(W_EQ).to_csv(OUT, index=False)
        print(f"[ok] wrote fallback -> {OUT}")
        return
    print("[ok] learned weights are present and valid; no action.")

if __name__ == "__main__":
    main()
