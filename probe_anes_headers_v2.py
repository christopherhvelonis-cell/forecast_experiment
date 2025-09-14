import os, sys, pandas as pd, numpy as np, codecs

PROJECT = r"C:\Users\Owner\Downloads\forecast_experiment"
RAW = os.path.join(PROJECT, "data", "raw")
csv_path = os.path.join(RAW, "anes_timeseries_2024_csv_20250808.csv")

print("File exists? ", os.path.exists(csv_path))
print("Path:", csv_path)

# 1) Show first 5 raw lines (helps identify delimiter)
try:
    with open(csv_path, "rb") as f:
        head = f.read(2048)
    # try to decode as utf-8 else latin-1
    try:
        txt = head.decode("utf-8", errors="replace")
    except:
        txt = head.decode("latin-1", errors="replace")
    print("\n--- FIRST BYTES (decoded) ---")
    print(txt)
except Exception as e:
    print("Failed to open raw file:", e)
    sys.exit(1)

# 2) Try robust read attempts WITHOUT low_memory
attempts = [
    dict(sep=None, engine="python", encoding="utf-8"),
    dict(sep=None, engine="python", encoding="latin-1"),
    dict(sep=",", engine="c", encoding="utf-8"),
    dict(sep=",", engine="c", encoding="latin-1"),
    dict(sep="\t", engine="python", encoding="utf-8"),
    dict(sep=";", engine="python", encoding="utf-8"),
]
df = None
ok = None
for opts in attempts:
    try:
        print("\nTrying read_csv with:", opts)
        df = pd.read_csv(csv_path, **opts, nrows=2000)  # read a sample
        ok = opts
        print("OK. shape:", df.shape)
        break
    except Exception as e:
        print("Failed:", e)

if df is None:
    print("\nAll attempts failed. The file may not be a text CSV/TSV. Is it XLSX/SAV/DTA/ZIP?")
    sys.exit(1)

print("\n--- COLUMNS (first 20) ---")
print(list(df.columns[:20]))
print("Total columns:", len(df.columns))

print("\n--- SAMPLE ROWS ---")
print(df.head(5).to_string())

# 3) Heuristic detection of key columns by content
def frac_in_set(series, allowed):
    s = pd.to_numeric(series, errors="coerce")
    s = s.dropna()
    if len(s) == 0: return 0
    return np.isin(s.values, allowed).mean()

cols = df.columns.tolist()

# Year candidates: mostly 1948..2025 and not too many unique values
year_candidates = []
for c in cols:
    s = pd.to_numeric(df[c], errors="coerce").dropna()
    if len(s) > 100 and (s.between(1948, 2025).mean() > 0.8) and (s.nunique() < 200):
        year_candidates.append(c)

scale_1to7 = []
for c in cols:
    frac = frac_in_set(df[c], np.arange(1,8))
    if frac > 0.5 and pd.to_numeric(df[c], errors="coerce").notna().sum() > 200:
        scale_1to7.append((c, round(frac,3)))

thermo_candidates = []
for c in cols:
    s = pd.to_numeric(df[c], errors="coerce").dropna()
    if len(s) > 200:
        share = s.between(0,100).mean()
        if share > 0.9:
            thermo_candidates.append((c, round(share,3)))

print("\n--- HEURISTIC CANDIDATES ---")
print("Year-ish:", year_candidates)
print("1..7-scale (IDEO or PID7):", scale_1to7[:20])
print("0..100 thermometer-like:", thermo_candidates[:20])

print("\nUsed read options:", ok)
