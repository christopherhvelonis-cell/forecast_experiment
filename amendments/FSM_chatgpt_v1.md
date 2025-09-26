# Amendments v1 — FSM_chatgpt
## Targets (≤3)
1) Shock frequency drift → re-estimate Poisson λ by rolling blocks.
2) Severity tails too light → t-severity ν prior loosened.
3) Spillover asymmetry → add sign-dependent shock multiplier.

## Expected Effects: CRPS/Brier improve; tail coverage ↑
## Touchpoints: models/FSM_chatgpt/code/* ; simulate paths; export quantiles
## Complexity Count (P): +1
