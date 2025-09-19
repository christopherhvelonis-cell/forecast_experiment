# SETUP (Deterministic Repro)

## Tool versions
- Python: 3.10+
- pandas, numpy, statsmodels, scipy, scikit-learn (pin in requirements.txt)
- Optional: ruptures (PELT), linearmodels/breaks for Bai-Perron, arviz/loo

## Seeds
- Global seed: 20250918 (override in configs/experiment.yml)

## Folder Tree
- configs
- data/raw
- data/processed
- data/docsheets
- eval/metrics
- eval/results
- eval/results/v2
- eval/results/diagnostics
- eval/holdouts
- validation_nonUS
- bias_logs
- ensemble
- reports
- models/HSM_chatgpt/code
- models/FSM_chatgpt/code
- models/HSM_grok/code
- models/FSM_grok/code
- Tools

## Vintages & Governance
- Track all snapshots in data/vintages.md, revisions in data/revisions.md.
- Acceptance gate (see configs/experiment.yml → governance.acceptance_gate).

## Quickstart
1. Edit configs/indicators.yml (add up to 15 finalized indicators).
2. Fill three data sheets from configs/TEMPLATE_data_sheet.md.
3. Run your existing evaluator v2 flow.
4. (Optional) Switch to Tools/evaluator_code_v3.py once ready.
