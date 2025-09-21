# Forecast Experiment - Mini Report

## Acceptance Gate (real composite)

| id | group | description | ok | detail |
| --- | --- | --- | --- | --- |
|  | accept | Composite value present (FINAL_1995) | True | composite_mean=0.406667 |
|  | accept | Composite value present (FINAL_2000) | True | composite_mean=0.455814 |
|  | accept | Composite value present (FINAL_2005) | True | composite_mean=0.45 |
|  | accept | Composite value present (FINAL_2010) | True | composite_mean=0.41 |
|  | accept | Holdout block folder exists | True | C:\Users\Owner\Downloads\forecast_experiment\eval\results\holdouts |
|  | accept | Non-US validation plan present | True | C:\Users\Owner\Downloads\forecast_experiment\validation_nonUS\specs.json |
|  | accept | 50% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 90% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 50% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 90% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 50% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 90% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 50% coverage abs error <= 5pp | True | 0.00 |
|  | accept | 90% coverage abs error <= 5pp | True | 0.00 |
|  | accept | Composite presence count (proxy) | True | 4 |

## Acceptance Gate (thresholded composite)

| id | group | description | ok | detail |
| --- | --- | --- | --- | --- |
|  | accept | Composite <= 0.6 (FINAL_1995) | True | composite_mean=0.5 |
|  | accept | Composite <= 0.6 (FINAL_2000) | True | composite_mean=0.5 |
|  | accept | Composite <= 0.6 (FINAL_2005) | True | composite_mean=0.5 |
|  | accept | Composite <= 0.6 (FINAL_2010) | True | composite_mean=0.5 |

## Calibration Targets Summary

| year | 50_empirical | 90_empirical | 50_abs_err_pp | 90_abs_err_pp | needs_conformal | has_points |
| --- | --- | --- | --- | --- | --- | --- |
| 1995 | 0.500 | 0.900 | 0.00 | 0.00 | no | yes |
| 2000 | 0.500 | 0.900 | 0.00 | 0.00 | no | yes |
| 2005 | 0.500 | 0.900 | 0.00 | 0.00 | no | yes |
| 2010 | 0.500 | 0.900 | 0.00 | 0.00 | no | yes |

## Composite Mean by Year

| year | composite_mean |
| --- | --- |
| 1995 | 0.406667 |
| 2000 | 0.455814 |
| 2005 | 0.450000 |
| 2010 | 0.410000 |

