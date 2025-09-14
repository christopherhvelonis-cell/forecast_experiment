# Mass Public Polarization (ANES 2024)

**Indicator ID:** mass_public_polarization  
**Version:** 2025-09-02  
**Owner:** Forecast Experiment  
**Source:** American National Election Studies (ANES) 2024 Time Series, codebook 2025-08-08

## Definition
Two components derived from the ANES 2024 wave:
1. **Ideology dispersion** — Standard deviation of respondents’ self-placement on the 7-point liberal–conservative scale (valid responses 1–7).
2. **Affective polarization** — Mean in-party vs out-party gap in party feeling thermometers (0–100). If 7-point party ID (PID7) is available, compute per-respondent in-party/out-party gap. If PID7 is missing, fall back to the population-level absolute Democratic vs Republican party thermometer difference.

## Variables
- **Year (constant):** 2024  
- **Ideology 7-pt:** `V241177`  
- **Party ID 7-pt (PID7):** `V241226`  
- **Thermometer — Democratic Party:** `V241166`  
- **Thermometer — Republican Party:** `V241167`

## Transform & QC
- Keep ideology in [1,7]; drop invalid.  
- Keep thermometers in [0,100].  
- Ideology dispersion = SD(ideology, ddof=0).  
- Affective polarization = mean in/out-party thermometer gap (using PID7 if present, fallback to |Dem−Rep|).  

## Coverage
- Year: 2024 only (ANES single wave).

## Vintage & Revisions
- Logged in `data/vintages.md`.  
- Policy: ANES wave files are fixed; treat re-releases as new vintages.

## Outputs
- `data/processed/mass_public_polarization.csv`

Example row:
