import textwrap, yaml, pathlib

raw_list = textwrap.dedent("""\
- name: real_gdp_growth
  source: "BEA NIPA; ALFRED"
  unit: percent_yoy
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: cpi_inflation
  source: "BLS CPI-U; ALFRED"
  unit: percent_yoy
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: unemployment_rate
  source: "BLS; ALFRED"
  unit: percent
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: labor_force_participation
  source: "BLS; ALFRED"
  unit: percent
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: treasury_10y_yield
  source: "FRED DGS10; ALFRED"
  unit: percent
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: term_spread_10y_3m
  source: "FRED DGS10 minus TB3MS; ALFRED"
  unit: percentage_points
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: housing_starts_total
  source: "Census; ALFRED"
  unit: thousands_sa
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: industrial_production
  source: "Fed G.17; ALFRED"
  unit: index
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: federal_spending_gdp_share
  source: "OMB Historical Tables; ALFRED where possible"
  unit: percent_gdp
  transform: z
  data_vintage_available: true
  scenario_only: false

- name: consumer_sentiment
  source: "Univ. Michigan ICS"
  unit: index
  transform: z
  data_vintage_available: false
  scenario_only: true

- name: sp500_real_total_return
  source: "S&P; Shiller"
  unit: percent_yoy
  transform: z
  data_vintage_available: false
  scenario_only: true

- name: baa_aaa_spread
  source: "FRED/ICE"
  unit: percentage_points
  transform: z
  data_vintage_available: false
  scenario_only: true

- name: immigration_rate
  source: "DHS Yearbook"
  unit: per_thousand_pop
  transform: z
  data_vintage_available: false
  scenario_only: true

- name: union_membership_rate
  source: "BLS CPS"
  unit: percent
  transform: z
  data_vintage_available: false
  scenario_only: true

- name: gini_income_inequality
  source: "Census CPS ASEC"
  unit: index
  transform: z
  data_vintage_available: false
  scenario_only: true
""")

items = yaml.safe_load(raw_list)
wrapped = {"indicators": items}

out_path = pathlib.Path(r"C:\Users\Owner\Downloads\forecast_experiment\configs\indicators.yml")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(yaml.dump(wrapped, sort_keys=False, allow_unicode=False), encoding="utf-8")

# Verify by re-reading the just-written file the same way an inventory script would
loaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
count = len(loaded.get("indicators", [])) if isinstance(loaded, dict) else 0
print(f"[write-ok] {out_path} indicators={count}")
