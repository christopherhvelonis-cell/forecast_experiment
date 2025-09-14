import pathlib, json, datetime as dt

files = {
    "SETUP.md": """# SETUP

**Project:** forecast_experiment — Origin 1995 (BA a=2.21, TM α=0.85)

## Tooling & Versions
- Python >=3.13
- pandas, numpy, scikit-learn, statsmodels, ruptures, MAPIE

## Folder Tree
data/{raw,processed,docsheets}
eval/{results,diagnostics,v2}
validation_nonUS/
bias_logs/
configs/
reports/
tools/
release/
templates/

## Reproducibility
- Seeds recorded in reports/release_manifest.md
- Data ≤ origin only
- SHA256 for all raw files

## Acceptance Gate
- 2 of 3 improve (composite, holdout, non-US median) AND Bias audit=PASS
- Coverage error ≤5pp, median skill ≥0 vs equal-weight
""",

    "templates/TEMPLATE_data_sheet.md": """# Data Sheet — <INDICATOR_NAME>

- Source: <SOURCE_TITLE>
- URL: <URL>
- Unit: <UNIT>   Transform: <z/logit/Box-Cox/none>
- Vintage access: <ALFRED/API/Archive/Manual>
- Revision policy: <none/regular/irregular>
- Survey/mode changes: <notes>
- Break markers: <PELT/Bai–Perron>
- Preprocessing: annualize=<rule>, impute=<method>, outliers=<rule>
- Provenance hash (SHA256): <…>
- Prepared by: <name>, <date>
""",

    "templates/TEMPLATE_model_card.md": """# Model Card — <MODEL_NAME>

- Version/Tag: <v…>
- Seeds: <…>
- Complexity Count P: <…>
- Leakage controls: vintages, ≤ origin, rolling-origin eval
- Calibration: EMOS/NGR, isotonic/beta-pool, conformal if needed
- Break handling: PELT/Bai–Perron
- Outputs: quantiles 5/50/95, PIT, coverage
- Metrics: CRPS, Brier, Murphy
- Multivariate postproc: ECC/Schaake
""",

    "templates/TEMPLATE_bias_log.md": """# Bias Audit — <MODEL_NAME>

Date: <YYYY-MM-DD>  
Auditor: <name>

## Source Diversity
<notes>

## Subgroup Errors
| subgroup | N | CRPS | Brier | cov50 | cov90 |
|----------|--|------|-------|-------|-------|
| <grp>    |   |      |       |       |       |

## Findings & Mitigations
- Findings: <…>
- Mitigations: <…>

Outcome: PASS / NEEDS WORK / FAIL
""",

    "templates/TEMPLATE_scorecard.csv": "indicator,level,covered,total,coverage_rate,crps,brier,notes\n<name>,0.5,,,,,\n<name>,0.9,,,,,\n",

    "templates/TEMPLATE_run_manifest.json": json.dumps({
        "git_tag": "<fill-me>",
        "created_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeds": {"global": None},
        "environment": {"python": ">=3.13", "os": "Windows"},
        "inputs": {"calibrated_csvs": []},
        "outputs": {"final_csv": "", "diagnostics_dir": ""},
        "commands": []
    }, indent=2)
}

for path, content in files.items():
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print("Wrote", path)
