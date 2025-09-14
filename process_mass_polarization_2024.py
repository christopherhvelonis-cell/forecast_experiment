# -*- coding: utf-8 -*-
"""
Process ANES 2024 wave -> mass_public_polarization.csv (single-year row)
- Ideology dispersion: std dev of 7-pt ideology self-placement.
- Affective polarization:
    If PID7 present -> mean in-party vs out-party thermometer gap
    Else            -> population-level |DemParty thermometer - RepParty thermometer|
"""

import os
import sys
import numpy as np
import pandas as pd

# ---------------- CONFIG: 2024 ANES variable IDs ----------------
# This file is a single-year (2024) wave; we set the year constant.
YEAR_CONST = 2024

# Confirmed by codebook (labels summarized in prior message):
IDEO       = "V241177"   # 7-pt liberal–conservative self-placement (1..7)
PID7       = "V241226"   # 7-pt party ID (Strong Dem … Strong Rep). If not in file, set to None.
THERM_DEM  = "V241166"   # Democratic Party thermometer (0..100), pre-wave
THERM_REP  = "V241167"   # Republican Party thermometer (0..100), pre-wave
# ----------------------------------------------------------------

# Project paths (point to your Downloads project)
PROJECT = r"C:\Users\Owner\Downloads\forecast_experiment"
RAW     = os.path.join(PROJECT, "data", "raw")
OUTDIR  = os.path.join(PROJECT, "data", "processed")
os.makedirs(OUTDIR, exist_ok=True)

# Locate ANES CSV (allow flexible suffix)
import glob
candidates = glob.glob(os.path.join(RAW, "anes_timeseries_2024_csv*.csv"))
if not candidates:
    print("ERROR: No ANES CSV found in:", RAW)
    print("RAW contents:", os.listdir(RAW) if os.path.exists(RAW) else "RAW missing")
    sys.exit(1)

anes_csv = candidates[0]
print("Using ANES file:", anes_csv)

# Read file (disable low_memory to avoid dtype issues in wide survey files)
try:
    df = pd.read_csv(anes_csv, encoding="utf-8", low_memory=False)
except Exception as e_utf8:
    # Fallback to latin-1 if needed
    try:
        df = pd.read_csv(anes_csv, encoding="latin-1", low_memory=False)
        print("NOTE: Read with latin-1 encoding fallback.")
    except Exception as e_lat:
        print("Failed to read CSV with utf-8 and latin-1.")
        print("utf-8 error:", e_utf8)
        print("latin-1 error:", e_lat)
        sys.exit(1)

# Utility
def to_num(s):
    return pd.to_numeric(s, errors="coerce")

def exists(col):
    return (col is not None) and (col in df.columns)

print("\nDetected presence:")
print(f"  IDEO ({IDEO}):", exists(IDEO))
print(f"  PID7 ({PID7}):", exists(PID7))
print(f"  THERM_DEM ({THERM_DEM}):", exists(THERM_DEM))
print(f"  THERM_REP ({THERM_REP}):", exists(THERM_REP))

# ---------- 1) Ideology dispersion (std of 1..7) ----------
ideo_result = pd.DataFrame(columns=["year","ideology_dispersion","ideology_n"])
if exists(IDEO):
    x = to_num(df[IDEO])
    mask = x.between(1,7)
    if mask.any():
        ideo_sd = float(x[mask].std(ddof=0))  # population SD; use ddof=1 if you prefer sample SD
        ideo_n  = int(mask.sum())
    else:
        ideo_sd, ideo_n = (np.nan, 0)
    ideo_result = pd.DataFrame({
        "year": [YEAR_CONST],
        "ideology_dispersion": [ideo_sd],
        "ideology_n": [ideo_n]
    })
else:
    print("NOTE: IDEO column not found; ideology dispersion will be missing.")

# ---------- 2) Affective polarization ----------
# Two modes:
#   (a) If PID7 and both thermometers available -> in-party vs out-party gap per respondent
#   (b) Else if both thermometers available -> population-level |DemParty - RepParty|
aff_result = pd.DataFrame(columns=["year","affective_polarization","affective_n"])

have_therm = exists(THERM_DEM) and exists(THERM_REP)
if have_therm:
    d = to_num(df[THERM_DEM])
    r = to_num(df[THERM_REP])
    valid = d.between(0,100) & r.between(0,100)

    if exists(PID7):
        pid = to_num(df[PID7])

        # Compute per-respondent in-party vs out-party gap
        # Typical 7-pt PID coding: 1..3 Dem side, 4 Ind, 5..7 Rep side (we treat 4 as independent)
        def gap_row(i):
            if not valid.iat[i] or pd.isna(pid.iat[i]):
                return np.nan
            if pid.iat[i] <= 3:
                return abs(d.iat[i] - r.iat[i])   # Dem/lean Dem
            elif pid.iat[i] >= 5:
                return abs(r.iat[i] - d.iat[i])   # Rep/lean Rep
            else:
                return abs(d.iat[i] - r.iat[i])   # Independents: absolute difference

        # Vectorized-ish apply for safety with mixed dtypes
        gaps = pd.Series([gap_row(i) for i in range(len(df))], dtype="float64")
        m = gaps.notna()
        if m.any():
            aff_mean = float(gaps[m].mean())
            aff_n    = int(m.sum())
        else:
            aff_mean, aff_n = (np.nan, 0)

        aff_result = pd.DataFrame({
            "year": [YEAR_CONST],
            "affective_polarization": [aff_mean],
            "affective_n": [aff_n]
        })
    else:
        # Fallback: population-level thermometer gap (no PID7)
        gaps = (d[valid] - r[valid]).abs()
        aff_result = pd.DataFrame({
            "year": [YEAR_CONST],
            "affective_polarization": [float(gaps.mean()) if len(gaps) else np.nan],
            "affective_n": [int(len(gaps))]
        })
else:
    print("NOTE: Missing one or both thermometer columns; affective polarization will be missing.")

# ---------- Merge & Save ----------
final = pd.merge(ideo_result, aff_result, on="year", how="outer")
out_csv = os.path.join(OUTDIR, "mass_public_polarization.csv")
final.to_csv(out_csv, index=False)
print("\nWrote:", out_csv)
print(final.to_string(index=False))
