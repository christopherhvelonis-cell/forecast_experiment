# Release Manifest — v1995-a085-equal

Created: 2025-09-10 20:26:57  
Platform: Windows-10-10.0.19045-SP0  
Python: 3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11) [MSC v.1944 64 bit (AMD64)]

## Files in `release/` (SHA256)

| file | sha256 |
|:-----|:-------|
| coverage_summary_calibrated.csv | `0af01b0e0b399c76d88031bb62878eed5993a3f34004512923e1b79db6b4cc74` |
| coverage_summary_calibrated_ensemble.csv | `0af01b0e0b399c76d88031bb62878eed5993a3f34004512923e1b79db6b4cc74` |
| FINAL_ensemble_1995_equal.csv | `667d653b07b93fcc9f549fd326b165fc934d6b48f024c5c487c0bd99d4168bf9` |
| FINAL_hsm_chatgpt_1995.csv | `991f19e72828ae0841aea316cf80819f00597cd3cb15e6463d5c005e6d493027` |
| final_report.md | `78742460e150e6125acb2da724ae3710551e284a9a559d9e359a885880ae71c2` |
| hsm_chatgpt_1995_audit.md | `2dc3b6551223a2fbb329498a7c7f86cd73e8744f80a55b3f760f9b30038c1eb1` |

## Reproduction (core commands)

- `python tools\ensemble_equal_cli.py --list_file configs\ensemble_models_1995.txt --out_csv eval\results\calibrated\FINAL_ensemble_1995_equal.csv`
- `python verify_calibrated_cli.py --calibrated_csv eval\results\calibrated\FINAL_ensemble_1995_equal.csv --indicators ba_plus_25plus_share trust_media_pct --origin 1995 --h 15 --out_dir eval\results\diagnostics\FINAL_ensemble_1995_equal`
- `python validation_nonUS\nonus_check_cli.py --final_calibrated_csv eval\results\calibrated\FINAL_hsm_chatgpt_1995.csv --proxy_csv validation_nonUS\proxies_japan_ba.csv --origin 1995 --out_dir validation_nonUS\out\Japan_ba_plus_25plus_share`
- `python validation_nonUS\nonus_check_cli.py --final_calibrated_csv eval\results\calibrated\FINAL_hsm_chatgpt_1995.csv --proxy_csv validation_nonUS\proxies_brazil_tm.csv --origin 1995 --out_dir validation_nonUS\out\Brazil_trust_media_pct`

## Seeds / Config Notes

- Seeds: (record here if applicable)
- Configs: `configs/ensemble_models_1995.txt` lists included models for the ensemble.

## Library Versions (`pip freeze`)

```
conformal==0.1
contourpy==1.3.3
copulae==0.8.0
cycler==0.12.1
Cython==3.1.3
fonttools==4.59.2
formulaic==1.2.0
interface-meta==1.3.0
joblib==1.5.2
kiwisolver==1.4.9
MAPIE==0.9.2
matplotlib==3.10.6
narwhals==2.3.0
numpy==2.3.2
packaging==25.0
pandas==2.3.2
patsy==1.0.1
pillow==11.3.0
pyparsing==3.2.3
python-dateutil==2.9.0.post0
pytz==2025.2
PyYAML==6.0.2
ruptures @ git+https://github.com/deepcharles/ruptures.git@e88da13b5f625f37321abd07c5d14b91701c6655
scikit-learn==1.5.2
scipy==1.16.1
setuptools==70.0.0
six==1.17.0
statsmodels @ git+https://github.com/statsmodels/statsmodels.git@d0608bb1a8fe1d9019e8e3d71a684c8b49788745
tabulate==0.9.0
threadpoolctl==3.6.0
typing_extensions==4.15.0
tzdata==2025.2
wrapt==1.17.3
xlsxwriter==3.2.5
```
