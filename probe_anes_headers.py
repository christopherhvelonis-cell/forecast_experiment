import pandas as pd, numpy as np, os, sys

PROJECT = r"C:\Users\Owner\Downloads\forecast_experiment"
RAW = os.path.join(PROJECT, "data", "raw")

# Choose your file explicitly (or list RAW to confirm)
csv_path = os.path.join(RAW, "anes_timeseries_2024_csv_20250808.csv")
print("Trying to read:", csv_path)

# Try a few read strategies
df = None
errors = []

for sep, enc in [(None, "utf-8"), (None, "latin-1"), (",", "utf-8"), ("\t", "utf-8"), (";", "utf-8")]:
    try:
        print(f"Attempting read_csv(sep={sep}, encoding={enc}) ...")
        df = pd.read_csv(csv_path, sep=sep, engine="python", encoding=enc, low_memory=False)
        print("Read OK with that combo.")
        break
    except Exception as e:
        errors.append((sep, enc, str(e)))
        print("Failed:", e)

if df is None:
    print("All attempts failed. Errors tried:")
    for e in errors:
        print("  ", e)
    sys.exit(1)

print("\n--- BASIC INFO ---")
print("shape:", df.shape)
print("first 10 columns:", list(df.columns[:10]))
print("last 10 columns:", list(df.columns[-10:]))

print("\n--- SAMPLE ROWS ---")
print(df.head(3).to_string())

cols = df.columns.tolist()
lower = {c: c.lower() for c in cols}

# Heuristic candidate hunts
def find_by_substrings(subs):
    out = []
    for c in cols:
        lc = lower[c]
        if all(s in lc for s in subs):
            out.append(c)
    return out

# Likely year column: numeric, plausible years
year_candidates = []
for c in cols:
    s = pd.to_numeric(df[c], errors="coerce")
    if s.notna().sum() > 1000:
        vals = s.dropna()
        if (vals.between(1948, 2025).mean() > 0.8) and (vals.nunique() < 200):
            year_candidates.append(c)

# Columns with many 1..7 values (ideology or PID)
def frac_in_set(series, allowed):
    s = pd.to_numeric(series, errors="coerce")
    s = s.dropna()
    if len(s) == 0: return 0
    return np.isin(s.values, allowed).mean()

one_to_seven_candidates = []
for c in cols:
    frac = frac_in_set(df[c], np.arange(1,8))
    if frac > 0.5 and pd.to_numeric(df[c], errors="coerce").notna().sum() > 1000:
        one_to_seven_candidates.append((c, round(frac,3)))

# Thermometers: many values in [0..100]
thermo_candidates = []
for c in cols:
    s = pd.to_numeric(df[c], errors="coerce")
    s = s.dropna()
    if len(s) > 1000:
        share_0_100 = (s.between(0,100).mean())
        if share_0_100 > 0.9:  # mostly in thermometer range
            thermo_candidates.append((c, round(share_0_100,3)))

print("\n--- HEURISTIC CANDIDATES ---")
print("Year candidates:", year_candidates)
print("1..7-scale candidates (could be IDEO or PID7):", one_to_seven_candidates[:20])
print("0..100 'thermometer-like' candidates:", thermo_candidates[:20])

# Substring searches to guide us (if named nicely)
print("\n--- SUBSTRING MATCHES ---")
print("Contains 'ideol':", find_by_substrings(["ideol"]))
print("Contains 'pid':", find_by_substrings(["pid"]))
print("Contains 'party' and 'therm' or 'ft':", find_by_substrings(["party","therm"]) + find_by_substrings(["party","ft"]))
print("Contains 'dem' and 'therm' or 'ft':", find_by_substrings(["dem","therm"]) + find_by_substrings(["dem","ft"]))
print("Contains 'rep' and 'therm' or 'ft':", find_by_substrings(["rep","therm"]) + find_by_substrings(["rep","ft"]))
