# -*- coding: utf-8 -*-
"""
Mass Public Polarization from ANES CDF (per-year best thermometer pair, weighted).

Outputs data/processed/mass_public_polarization.csv with:
  year, ideology_dispersion, ideology_n, affective_polarization, affective_n

Ideology dispersion: weighted SD of 7-point ideology (valid 1..7; unweighted fallback)
Affective polarization:
  If PID7 present in that year: mean |in-party – out-party| thermometer gap (0..100)
  Else: population mean |Dem thermometer – Rep thermometer|
Weights:
  Prefer VCF0009z, else VCF9999, else VCF0009x/VCF0009y. Normalize within year.
"""

import os, sys, glob
import numpy as np
import pandas as pd

PROJECT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(PROJECT, "data", "raw")
OUT = os.path.join(PROJECT, "data", "processed")
os.makedirs(OUT, exist_ok=True)

# ---- find CDF ----
cdf_candidates = glob.glob(os.path.join(RAW, "anes_timeseries_cdf*.csv")) + \
                 glob.glob(os.path.join(RAW, "anes_timeseries_cdf_csv_*.csv"))
if not cdf_candidates:
    print("ERROR: no ANES CDF CSV in", RAW); sys.exit(1)
cdf_csv = sorted(cdf_candidates)[-1]
print("Using ANES CDF:", cdf_csv)

def read_csv_robust(path):
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False)
    except Exception:
        print("NOTE: utf-8 failed; trying latin-1…")
        return pd.read_csv(path, encoding="latin-1", low_memory=False)

df = read_csv_robust(cdf_csv)
print("Loaded shape:", df.shape)

# ---- candidates ----
YEAR_CANDS  = ["VCF0004", "YEAR", "year", "vyear", "VCF0004a", "VCF0004x"]
IDEO_CANDS  = ["VCF0803", "VCF080305", "IDEO7", "ideo7", "V241177"]
PID7_CANDS  = ["VCF0301", "PID7", "pid7", "V241226"]

# Thermometer pairs (Dem, Rep) to try; include classic group & party variants
THERM_PAIRS = [
    ("VCF0218","VCF0224"),  # Democratic Party / Republican Party
    ("VCF0218","VCF0222"),  # alt mapping in some releases
    ("VCF0201","VCF0202"),  # Democrats / Republicans (group thermometers)
    ("V201156","V201157"),  # 2020 pre
    ("V241166","V241167"),  # 2024 pre
    ("FTDems","FTReps"),
    ("therm_dem","therm_rep"),
]

WEIGHT_CANDS = ["VCF0009z", "VCF9999", "VCF0009x", "VCF0009y"]

def first_existing(cands, cols):
    for c in cands:
        if c in cols:
            return c
    return None

def to_num(s): return pd.to_numeric(s, errors="coerce")

def detect_year_col(frame):
    col = first_existing(YEAR_CANDS, frame.columns)
    if col: return col
    best, best_score = None, -1
    for c in frame.columns:
        s = to_num(frame[c]); ok = s.between(1948, 2025)
        score = ok.mean() * (1.0 - min(s.nunique(), 500)/500.0)
        if ok.mean() > 0.5 and s.nunique() < 200 and score > best_score:
            best, best_score = c, score
    return best

YEAR = detect_year_col(df)
IDEO = first_existing(IDEO_CANDS, df.columns)
PID7 = first_existing(PID7_CANDS, df.columns)
WCOL = first_existing(WEIGHT_CANDS, df.columns)

print("\nDetected core columns:")
print("  YEAR:", YEAR)
print("  IDEO:", IDEO)
print("  PID7:", PID7)
print("  WEIGHT:", WCOL)

if YEAR is None: print("ERROR: no YEAR"); sys.exit(1)
df["_YEAR"] = to_num(df[YEAR])
if IDEO: df["_IDEO"] = to_num(df[IDEO])
if PID7: df["_PID7"] = to_num(df[PID7])
if WCOL: df["_W"]    = to_num(df[WCOL]).clip(lower=0)

# Precompute numeric versions of all thermometer candidates (only those present)
therm_present = []
for dcol, rcol in THERM_PAIRS:
    if (dcol in df.columns) and (rcol in df.columns):
        dname = f"_T_{dcol}"; rname = f"_T_{rcol}"
        df[dname] = to_num(df[dcol]); df[rname] = to_num(df[rcol])
        therm_present.append((dcol, rcol, dname, rname))

def wmean(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    m = (~np.isnan(x)) & (~np.isnan(w)) & (w > 0)
    if not m.any(): return np.nan
    return float(np.average(x[m], weights=w[m]))

def wstd(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    m = (~np.isnan(x)) & (~np.isnan(w)) & (w > 0)
    if not m.any(): return np.nan
    wm = np.average(x[m], weights=w[m])
    var = np.average((x[m]-wm)**2, weights=w[m])
    return float(np.sqrt(var))

years = sorted(int(y) for y in df["_YEAR"].dropna().unique() if 1900 <= y <= 2100)
rows = []
per_year_choice = {}  # record which pair used by year

for y in years:
    sub = df[df["_YEAR"] == y].copy()

    # normalize weights within year
    if "_W" in sub.columns:
        wsum = sub["_W"].sum(skipna=True)
        sub["_WN"] = sub["_W"]/wsum if wsum and not np.isnan(wsum) else np.nan
    else:
        sub["_WN"] = np.nan

    # ideology dispersion
    ideology_dispersion = np.nan; ideology_n = 0
    if "_IDEO" in sub.columns:
        m = sub["_IDEO"].between(1,7)
        ideology_n = int(m.sum())
        if ideology_n > 0:
            ideology_dispersion = wstd(sub.loc[m,"_IDEO"].values, sub.loc[m,"_WN"].values) \
                                  if sub["_WN"].notna().any() else \
                                  float(sub.loc[m,"_IDEO"].std(ddof=0))

    # choose best thermometer pair *for this year*
    best_count = -1
    best_pair = None
    best_gap_mean = np.nan
    best_n = 0

    for dcol, rcol, dname, rname in therm_present:
        d = sub[dname] if dname in sub.columns else None
        r = sub[rname] if rname in sub.columns else None
        if d is None or r is None: continue
        valid = d.between(0,100) & r.between(0,100)
        count_valid = int(valid.sum())
        if count_valid <= 0: continue

        # compute gap with PID if available, else population gap
        if "_PID7" in sub.columns and sub["_PID7"].notna().any():
            pid = sub["_PID7"]
            gaps = np.full(len(sub), np.nan, dtype=float)
            idx = np.where(valid.values)[0]
            for i in idx:
                p = pid.iat[i]
                if np.isnan(p): 
                    continue
                dd = d.iat[i]; rr = r.iat[i]
                if p <= 3:   gaps[i] = abs(dd - rr)   # Dem side
                elif p >= 5: gaps[i] = abs(rr - dd)   # Rep side
                else:        gaps[i] = abs(dd - rr)   # Ind
            m = ~np.isnan(gaps)
            n = int(m.sum())
            if n > 0:
                gap_mean = wmean(gaps[m], sub.loc[m, "_WN"].values) \
                           if sub["_WN"].notna().any() else float(np.nanmean(gaps))
            else:
                gap_mean = np.nan
        else:
            pg = (d[valid] - r[valid]).abs().values
            n = int(len(pg))
            gap_mean = wmean(pg, sub.loc[valid, "_WN"].values) \
                       if sub["_WN"].notna().any() else float(np.mean(pg))

        # choose pair by *valid count*, break ties by larger n then by not-NaN gap
        if (count_valid > best_count) or (count_valid == best_count and n > best_n) \
           or (count_valid == best_count and n == best_n and not np.isnan(gap_mean)):
            best_count = count_valid
            best_pair = (dcol, rcol)
            best_gap_mean = gap_mean
            best_n = n

    affective_polarization = best_gap_mean
    affective_n = best_n
    per_year_choice[y] = best_pair

    rows.append({
        "year": y,
        "ideology_dispersion": ideology_dispersion,
        "ideology_n": ideology_n,
        "affective_polarization": affective_polarization,
        "affective_n": affective_n
    })

result = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
mask_any = result[["ideology_dispersion","affective_polarization"]].notna().any(axis=1)
result = result[mask_any].reset_index(drop=True)

out_csv = os.path.join(OUT, "mass_public_polarization.csv")
result.to_csv(out_csv, index=False)
print("\nWrote:", out_csv)
print(result.tail(15).to_string(index=False))

# write which pair used by year
pairs_report = os.path.join(OUT, "mass_public_polarization_pairs_by_year.txt")
with open(pairs_report, "w", encoding="utf-8") as f:
    f.write("Thermometer pair chosen per year (Dem/Rep):\n")
    for y in sorted(per_year_choice.keys()):
        f.write(f"{y}: {per_year_choice[y]}\n")
print("Wrote pair-usage report:", pairs_report)

# annotate
ann_path = os.path.join(OUT, "annotations.md")
with open(ann_path, "a", encoding="utf-8") as f:
    f.write("\n\n## mass_public_polarization build (CDF, per-year pairs, weighted)\n")
    f.write(f"- Source: {os.path.basename(cdf_csv)}\n")
    f.write(f"- YEAR: {YEAR} | IDEO: {IDEO} | PID7: {PID7} | weights: {WCOL if WCOL else 'None'} (per-year normalized)\n")
    f.write(f"- Output rows: {len(result)} | Years: {result['year'].min()}–{result['year'].max()}\n")
print("Updated annotations:", ann_path)
