# Non-US Validation Plan — Origin 1995 (BA + TM)

**Bundle:** FINAL_hsm_chatgpt_1995.csv  
**Indicators:** 
- `ba_plus_25plus_share` (education attainment proxy)
- `trust_media_pct` (survey trust in media proxy)

**Objective**  
Evaluate calibration reliability out-of-sample using non-US series that are reasonably analogous in level/variation. We check 50%/90% coverage, PIT shape, and reliability curves. This is *not* score competition; it’s a stability/robustness check.

---

## Regions & Periods (Proxies)

Confidence scale: H (high), M (medium), L (low) — reflects conceptual proximity + data quality.

| Region (Proxy) | Period | BA proxy (share BA+) | Confidence | TM proxy (trust in media) | Confidence | Notes |
|---|---:|---|:---:|---|:---:|---|
| Western Europe (WEur) | 1945–1965 | OECD/UNESCO tertiary attainment share (25+) | M | Eurobarometer/ESS style trust (earliest avail) | L | Earlier survey modes vary; TM sparse pre-1970s. |
| India | 1947–1967 | Census/UNESCO tertiary share (25+) | M | National surveys on media trust (if available) | L | Mode/coverage issues likely; mark as exploratory. |
| Japan | 1950–1970 | MEXT/UNESCO tertiary share (25+) | H | NHK/ISSP trust media items (when available) | M | Strong administrative stats; survey mode modernizes in 1960s. |
| Brazil | 1985–2005 | PNAD/UNESCO tertiary share (25+) | M | Latinobarómetro media trust (post-1995) | M | TM starts mid-1990s; align origins accordingly. |
| South Africa | 1994–2014 | Stats SA/UNESCO tertiary share (25+) | M | Afrobarometer media trust | M | Good for TM; BA proxy quality moderate. |

*Action:* treat “WEur 1945–65” and “Japan 1950–70” as primary checks for BA; “Brazil 1995–2005” and “South Africa 1995–2014” as primary checks for TM.

---

## Data Handling

- **Vintages:** use best available snapshots; log SHA256 in `validation_nonUS/vintages.md`.
- **Annualization & transforms:** apply the same pipeline transforms used for US (see `indicator_transform_spec.yml`).
- **Alignment:** align **origin=1995** mechanics (train ≤ origin, evaluate horizons 1..15 where proxy data exists).
- **Missingness:** impute minimally with flags; do **not** backcast.

---

## Validation Procedure

For each (Region × Indicator):

1. **Prepare proxy series** (annual tidy with columns: `year, value, indicator, region`).
2. **Map indicator** to US-calibrated distributions by horizon:
   - Use the US-trained calibrated quantiles (centered at `q50`) as reference shape.
   - For each horizon h where proxy observation exists, check whether proxy value falls within the **50%** and **90%** US bands *(scenario-consistency check)*.
3. **Compute diagnostics**:
   - 50%/90% coverage rates across available horizons.
   - PIT values by ranking proxy versus calibrated CDF (approx via piecewise linear between quantiles).
   - Reliability curve: bin nominal probs vs empirical frequencies (10 bins).
4. **Acceptance thresholds** (soft gates):
   - Coverage within **±10 pp** of nominal (0.40–0.60 for 50%; 0.80–1.00 for 90%).
   - PIT roughly uniform (no single tail bin > 2× expected mass).
   - Document deviations; *no automatic rejection* — this is a robustness read.

---

## Outputs

For each Region × Indicator, write to `validation_nonUS/out/{region}_{indicator}/`:
- `coverage_points_nonUS.csv`  (tidy: region, indicator, horizon, level, covered)
- `coverage_summary_nonUS.csv`
- `pit_values_nonUS.csv`
- `reliability_nonUS.csv`
- `notes.md` (data provenance + caveats)

Append a roll-up table: `validation_nonUS/summary_1995.csv`.

---

## Risks & Caveats

- **Mode differences (TM):** wording/mode/response scales vary; treat results as directional.
- **Level shifts (BA):** tertiary definitions can differ; we compare inclusion, not absolute level.
- **Dependence:** univariate checks; multivariate coherence will be handled by ECC/Schaake at ensemble stage.

---

## Next Steps

1. Acquire proxy series per the `specs.json` below.  
2. Run the provided CLI to build non-US diagnostics (Step 13 helper).  
3. Review `summary_1995.csv`, then proceed to Step 14 (Ensemble) after core indicators are validated.
