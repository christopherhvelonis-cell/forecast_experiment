# Release Manifest — v1.5.1-ebma-overlap

Created: 2025-09-23 03:00:28  
Platform: Windows-10-10.0.19045-SP0  
Python: 3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]

## Files in `release/` (SHA256)

| file | sha256 |
|:-----|:-------|
| coverage_summary_calibrated.csv | `0af01b0e0b399c76d88031bb62878eed5993a3f34004512923e1b79db6b4cc74` |
| coverage_summary_calibrated_ensemble.csv | `0af01b0e0b399c76d88031bb62878eed5993a3f34004512923e1b79db6b4cc74` |
| FINAL_ensemble_1995_equal.csv | `667d653b07b93fcc9f549fd326b165fc934d6b48f024c5c487c0bd99d4168bf9` |
| FINAL_hsm_chatgpt_1995.csv | `991f19e72828ae0841aea316cf80819f00597cd3cb15e6463d5c005e6d493027` |
| final_report.md | `78742460e150e6125acb2da724ae3710551e284a9a559d9e359a885880ae71c2` |
| forecast_experiment_1995_a085_equal.zip | `34968a9c2d3478f1aebaf7dc68ac82a6b2acc77af6460c07d6c04000d2771278` |
| forecast_experiment_preview_20250920-210427.zip | `396266d636552cb799c4819370ef634a95fb5d4bb5cd9367349bfae55c5dc127` |
| forecast_experiment_preview_20250922-015337.zip | `3598bbd43f05cded336137d5bf8c0cc032d49a2b2a3d04301d473f5b0de7b3f8` |
| forecast_experiment_preview_20250922-175141.zip | `2043e22258cd3983074ba35d21636225027d2bb49f0af4c76eefe59cc924b6b6` |
| forecast_experiment_preview_20250922-213350.zip | `dccf08330a895050cd33b72b1b7b2856949e9d395e1f9184261cce91ba120a88` |
| forecast_experiment_preview_20250922-214134.zip | `f518e87c3f33b4a20923485d4985322087e9b8d2d0f27679b151ecd15e0ff613` |
| forecast_experiment_preview_20250923-015954.zip | `c5e07ad736932588ad12e0d012a10cde8ed3fb609ee681a7cfd417a30bc31caf` |
| forecast_experiment_preview_20250923-023051.zip | `2c6614d93d96e1e532d749262e3255b74a3b0e888db76388cf669462789e6186` |
| hsm_chatgpt_1995_audit.md | `2dc3b6551223a2fbb329498a7c7f86cd73e8744f80a55b3f760f9b30038c1eb1` |
| release_manifest.md | `3732bd596f298c22058f42a4153e2a9eaebe0c209f1b5715734187020f7664b2` |

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
joblib==1.5.2
numpy==1.26.4
pandas==2.3.2
pyarrow==21.0.0
python-dateutil==2.9.0.post0
pytz==2025.2
scikit-learn==1.5.2
scipy==1.16.2
six==1.17.0
tabulate==0.9.0
threadpoolctl==3.6.0
tzdata==2025.2
```
