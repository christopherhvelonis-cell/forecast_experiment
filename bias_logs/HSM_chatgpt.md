# Bias Audit – HSM_chatgpt
## Diversity & Framing
- Sources reviewed: Bureau of Labor Statistics (vintages), BEA (ALFRED), GSS, ANES, media-trust surveys.
- Risks flagged: proxy leakage from post-origin revisions; over-reliance on survey subwaves; US-centric framing for cross-national interpretation.
- Subgroup coverage issues: limited race/education cross-tabs for early years.

## Error Tables
- Group 1: Younger cohorts under-dispersion at long horizons.
- Group 2: Low-education subgroup over-dispersion at short horizons.

## Mitigation
- Actions: enforce vintage-only ingestion; conformal top-up on tails; add survey-mode flags; down-weight unstable proxies.
- Status: PASS
