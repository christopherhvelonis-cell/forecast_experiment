# Processing Plan — mass_public_polarization (ANES CDF)

## Inputs
- `data/raw/anes_timeseries_cdf_csv_20220916.csv` (ANES CDF)
- Optional single-wave reference: `data/raw/anes_timeseries_2024_csv_20250808.csv`

## Steps
1. Load CDF; detect columns for year (VCF0004), ideology (VCF0803), PID7 (VCF0301), weight (VCF0009z preferred).
2. For each year:
   - Normalize weights within year (if present).
   - **Ideology dispersion**: weighted SD over valid ideology (1..7).
   - **Affective polarization**: select the Dem/Rep thermometer pair with the most valid 0–100 responses for that year.  
     - If PID7 present in that year: mean in-party vs out-party gap per respondent.  
     - Else: population mean absolute gap |FT_Dem − FT_Rep|.
3. Save to `data/processed/mass_public_polarization.csv`.  
4. Write `data/processed/mass_public_polarization_pairs_by_year.txt` (pair used per year) and append build notes to `data/processed/annotations.md`.

## Vintage Control
- Record SHA256 of each raw CSV in `data/vintages.md` with date/time and short notes.

## Revisions
- Treat ANES re-releases as new vintages. No in-place edits.

## Scoring
- Indicator flagged **scored: true** once multi-year output is produced. No imputation of missing years.
