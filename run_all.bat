@echo off
set ORIGINS=1985 1990 1995 2000 2005 2010 2015 2020
set INDICATORS=mass_public_polarization public_trust_government vep_turnout_pct trust_media_pct union_membership_rate unemployment_rate real_gdp_growth house_polarization_dw mil_spend_gdp_share_pct ba_plus_25plus_share

for %%O in (%ORIGINS%) do (
  python C:\Users\Owner\Downloads\forecast_experiment\run_hsm.py --indicators %INDICATORS% --origin %%O --h 15 --out "C:\Users\Owner\Downloads\forecast_experiment\eval\results\hsm_chatgpt\hsm_chatgpt_%%O.csv"
  python C:\Users\Owner\Downloads\forecast_experiment\calibrate_sigma_cli.py --in "C:\Users\Owner\Downloads\forecast_experiment\eval\results\hsm_chatgpt\hsm_chatgpt_%%O.csv" --out "C:\Users\Owner\Downloads\forecast_experiment\eval\results\calibrated\hsm_chatgpt_%%O_cal.csv" --origins %%O --indicators %INDICATORS% --h 15 --target_cov 0.90
  python C:\Users\Owner\Downloads\forecast_experiment\verify_calibrated_cli.py --calibrated_csv "C:\Users\Owner\Downloads\forecast_experiment\eval\results\calibrated\hsm_chatgpt_%%O_cal.csv" --indicators %INDICATORS% --origin %%O --h 15 --out_dir "C:\Users\Owner\Downloads\forecast_experiment\eval\results\diagnostics\hsm_chatgpt_%%O_cal"
)

python C:\Users\Owner\Downloads\forecast_experiment\summarize_diagnostics_csv.py
