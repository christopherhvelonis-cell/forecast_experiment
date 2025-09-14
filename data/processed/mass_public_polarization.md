# Mass Public Polarization (ANES, weighted)

**Indicator ID:** mass_public_polarization  
**Version:** 2025-09-02  
**Owner:** Forecast Experiment  
**Source:** ANES Time Series Cumulative Data File (CDF)

## Definition
Two components derived from ANES:
1. **Ideology dispersion** — Weighted standard deviation (per-year normalized weights) of respondents’ self-placement on the 7-point ideology scale. Valid responses 1–7 only.
2. **Affective polarization** — Mean in-party vs out-party gap in party feeling thermometers (0–100). If PID7 is available in that year, compute per-respondent in/out-party gaps; otherwise use the population-level absolute gap |FT_Dem − FT_Rep|.

## Variable Mapping (auto-detected)
- **Year:** `VCF0004` (or detected equivalent)  
- **Ideology 7-pt:** `VCF0803` (or detected)  
- **PID7:** `VCF0301` (or detected)  
- **Weights (preferred):** `VCF0009z` (fallback: `VCF9999`, `VCF0009x`, `VCF0009y`)  
- **Party thermometers (per-year best pair):** tries `[VCF0218/VCF0224]`, `[VCF0218/VCF0222]`, `[VCF0201/VCF0202]`, `[V201156/V201157]`, `[V241166/V241167]`, `[FTDems/FTReps]`, `[therm_dem/therm_rep]` and selects the pair with the most valid 0–100 responses for each year.

## Transform & QC
- Coerce all inputs to numeric; drop out-of-range values (ideology not in 1..7; thermometers not in 0..100).
- **Weights:** per-year normalization; if absent, fall back to unweighted stats.
- **Ideology dispersion:** weighted SD (ddof=0).
- **Affective polarization:** PID7 gap when available per year; otherwise population |FT_Dem − FT_Rep|.
- No imputation; years lacking any valid thermometers remain `NaN` for affective polarization.

## Coverage
- **Years:** auto-detected from the CDF (your current build shows 1984–2020; some years may be missing if no thermometers were fielded).

## Vintage & Revisions
- Logged in `data/vintages.md` with SHA256 for each source file.
- ANES releases are fixed; any re-release treated as a new vintage.

## Output
- `data/processed/mass_public_polarization.csv`  
  Columns: `year, ideology_dispersion, ideology_n, affective_polarization, affective_n`
- `data/processed/mass_public_polarization_pairs_by_year.txt` (which thermometer pair was used each year)
- `data/processed/annotations.md` (build metadata)

## Notes
- Keep NaNs for years with no party thermometers. Do not backfill/impute for scored evaluation.
- This indicator is **scored** once multi-year coverage exists.
