import pandas as pd
import numpy as np
import os
import glob
import sys

# ---- Paths ----
PROJECT = r"C:\Users\Owner\Downloads\forecast_experiment"
RAW = os.path.join(PROJECT, "data", "raw")
OUT = os.path.join(PROJECT, "data", "processed")
os.makedirs(OUT, exist_ok=True)

# ---- Auto-detect ANES CSV in RAW ----
candidates = glob.glob(os.path.join(RAW, "anes_timeseries_2024_csv*.csv"))
if not candidates:
    print("ERROR: No ANES CSV found matching pattern: anes_timeseries_2024_csv*.csv")
    print("RAW directory contents:")
    try:
        for f in os.listdir(RAW):
            print("  -", f)
    except FileNotFoundError:
        print("RAW directory not found:", RAW)
    sys.exit(1)

anes_csv = candidates[0]
print("Using ANES file:", anes_csv)

# ---- Load ----
df = pd.read_csv(anes_csv, low_memory=False)

def first_existing(cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

# Common columns (auto-detect)
YEAR       = first_existing(["VCF0004","year","YEAR"])
IDEO       = first_existing(["VCF0803","IDEO7","ideo7"])
PID7       = first_existing(["VCF0301","PID7","pid7"])    # 7-point party ID
THERM_DEM  = first_existing(["VCF0218","FTDems","therm_dem"])
THERM_REP  = first_existing(["VCF0222","FTReps","therm_rep"])

print("Detected columns:")
print("  YEAR:", YEAR)
print("  IDEO:", IDEO)
print("  PID7:", PID7)
print("  THERM_DEM:", THERM_DEM)
print("  THERM_REP:", THERM_REP)

# ---- 1) Ideology dispersion (std of 1..7 scale) ----
ideo_result = pd.DataFrame(columns=["year","ideology_dispersion","ideology_n"])
if YEAR and IDEO:
    tmp = df[[YEAR, IDEO]].copy()
    tmp[IDEO] = pd.to_numeric(tmp[IDEO], errors="coerce")
    tmp = tmp[(tmp[IDEO] >= 1) & (tmp[IDEO] <= 7)]
    ideo_result = (
        tmp.groupby(YEAR)[IDEO]
           .agg(ideology_dispersion="std", ideology_n="count")
           .reset_index()
           .rename(columns={YEAR:"year"})
           .sort_values("year")
    )
else:
    print("WARNING: Could not compute ideology dispersion (missing YEAR or IDEO)")

# ---- 2) Affective polarization (mean in-party vs out-party thermometer gap) ----
aff_result = pd.DataFrame(columns=["year","affective_polarization","affective_n"])
if YEAR and PID7 and THERM_DEM and THERM_REP:
    tmp = df[[YEAR, PID7, THERM_DEM, THERM_REP]].copy()
    for col in [PID7, THERM_DEM, THERM_REP]:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
    tmp = tmp[tmp[THERM_DEM].between(0,100, inclusive="both") &
              tmp[THERM_REP].between(0,100, inclusive="both")]

    def gap(row):
        pid = row[PID7]
        d = row[THERM_DEM]
        r = row[THERM_REP]
        if np.isnan(pid) or np.isnan(d) or np.isnan(r):
            return np.nan
        if pid <= 3:      # Democrat/lean Dem
            return abs(d - r)
        elif pid >= 5:    # Republican/lean Rep
            return abs(r - d)
        else:             # Independents: absolute difference
            return abs(d - r)

    tmp["gap"] = tmp.apply(gap, axis=1)
    aff_result = (
        tmp.groupby(YEAR)["gap"]
           .agg(affective_polarization="mean", affective_n="count")
           .reset_index()
           .rename(columns={YEAR:"year"})
           .sort_values("year")
    )
else:
    print("WARNING: Could not compute affective polarization (missing YEAR, PID7, THERM_DEM, or THERM_REP)")

# ---- Merge & save ----
final = pd.merge(ideo_result, aff_result, on="year", how="outer").sort_values("year")
out_csv = os.path.join(OUT, "mass_public_polarization.csv")
final.to_csv(out_csv, index=False)
print(f"Wrote: {out_csv}")
print(final.tail(10))
