#!/usr/bin/env python
# Minimal Murphy decomposition helper.
# If required inputs are missing, it emits an empty CSV with header and exits 0.

import argparse, csv, os, sys, pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    ap.add_argument("--metricsdir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    metricsdir = pathlib.Path(args.metricsdir)
    outp = pathlib.Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    # Expected inputs (your evaluator may differ; this is tolerant)
    # Seek event probability and outcome files in metricsdir.
    cand_probs = ["event_probs.csv", "events_probs.csv", "event_probabilities.csv"]
    cand_outcomes = ["event_outcomes.csv", "events_outcomes.csv", "event_labels.csv"]

    probs = next((metricsdir / c for c in cand_probs if (metricsdir / c).exists()), None)
    outs  = next((metricsdir / c for c in cand_outcomes if (metricsdir / c).exists()), None)

    header = ["event","n","reliability","resolution","uncertainty","brier_mean"]
    # If missing inputs, write empty file with header
    if probs is None or outs is None:
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header)
        print(f"[murphy] inputs missing (probs={bool(probs)} outs={bool(outs)}). Wrote empty {outp}.")
        return 0

    # Naive join by event + (optional) horizon; expect columns:
    # probs: event, horizon(optional), p
    # outs : event, horizon(optional), y in {0,1}
    import pandas as pd
    try:
        dfp = pd.read_csv(probs)
        dfo = pd.read_csv(outs)
    except Exception as e:
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header)
        print(f"[murphy] read error: {e}. Wrote empty {outp}.")
        return 0

    # Standardize column names
    def std(df):
        cols = {c.lower(): c for c in df.columns}
        rename = {}
        if "event" in cols: rename[cols["event"]] = "event"
        if "horizon" in cols: rename[cols["horizon"]] = "horizon"
        # prob column
        for k in ["p","prob","probability","event_prob","proba"]:
            if k in cols: rename[cols[k]] = "p"
        # outcome column
        for k in ["y","label","outcome","occurrence"]:
            if k in cols: rename[cols[k]] = "y"
        return df.rename(columns=rename)

    dfp = std(dfp); dfo = std(dfo)

    keys = [c for c in ["event","horizon"] if c in dfp.columns and c in dfo.columns]
    if not keys: keys = ["event"]
    try:
        df = pd.merge(dfp, dfo, on=keys, how="inner")
    except Exception as e:
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header)
        print(f"[murphy] merge error: {e}. Wrote empty {outp}.")
        return 0

    if "p" not in df or "y" not in df:
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header)
        print(f"[murphy] missing p/y columns after merge. Wrote empty {outp}.")
        return 0

    # Bin by probability (10 bins) for a simple Murphy decomposition
    import numpy as np
    df["bin"] = np.clip((df["p"] * 10).astype(int), 0, 9)
    rows = []
    for ev, dfe in df.groupby("event"):
        n = len(dfe)
        if n == 0:
            rows.append({"event": ev, "n": 0, "reliability": 0, "resolution": 0, "uncertainty": 0, "brier_mean": 0})
            continue

        o = dfe["y"].mean()  # climatology
        # Reliability: within-bin mean (p - y)^2 weighted
        rel = 0.0
        res = 0.0
        brier = ((dfe["p"] - dfe["y"])**2).mean()
        for _, g in dfe.groupby("bin"):
            w = len(g) / n
            p_bar = g["p"].mean()
            y_bar = g["y"].mean()
            rel += w * (p_bar - y_bar)**2
            res += w * (y_bar - o)**2
        unc = o * (1 - o)
        rows.append({"event": ev, "n": int(n), "reliability": float(rel), "resolution": float(res), "uncertainty": float(unc), "brier_mean": float(brier)})

    out = pd.DataFrame(rows, columns=header)
    out.to_csv(outp, index=False, encoding="utf-8")
    print(f"[murphy] wrote {outp} (events={out.shape[0]})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
