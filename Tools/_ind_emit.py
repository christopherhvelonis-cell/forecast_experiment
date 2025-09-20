import json, yaml, pathlib
base = pathlib.Path(r"C:\Users\Owner\Downloads\forecast_experiment\configs")
yml  = base / "indicators.yml"
data = yaml.safe_load(yml.read_text(encoding="utf-8"))
items = data.get("indicators", data) if isinstance(data, dict) else data
(base / "indicators.json").write_text(json.dumps({"indicators": items}, indent=2), encoding="utf-8")
(base / "indicators_list.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
print("[ok] wrote indicators.json and indicators_list.json")
