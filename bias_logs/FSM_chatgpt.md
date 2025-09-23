# Bias Audit – FSM_chatgpt
## Diversity & Framing
- Sources reviewed: shocks from historical news/event catalogs; macro covariates (vintaged).
- Risks flagged: shock narrative bias; tail calibration sensitivity to assumed severities.
- Subgroup coverage issues: none (aggregate indicator focus).

## Error Tables
- Group 1: Post-shock rebounds underpredicted (CRPS tail miss).
- Group 2: Pre-shock drift occasionally overestimated.

## Mitigation
- Actions: thicken-tails via t-severity, conformal residual bootstrap; scenario-only for 40y.
- Status: PASS
