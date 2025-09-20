import sys, json, yaml, pathlib
src = pathlib.Path(r"C:\Users\Owner\Downloads\forecast_experiment\configs\indicators.yml")
data = yaml.safe_load(src.read_text(encoding="utf-8"))
# Accept either a wrapped dict or a plain list
items = data.get("indicators", data) if isinstance(data, dict) else data

out1 = pathlib.Path(r"C:\Users\Owner\Downloads\forecast_experiment\configs\indicators.json")          # wrapped
out2 = pathlib.Path(r"C:\Users\Owner\Downloads\forecast_experiment\configs\indicators_list.json")     # plain
out1.write_text(json.dumps({"indicators": items}, indent=2), encoding="utf-8")
out2.write_text(json.dumps(items, indent=2), encoding="utf-8")
print("[wrote]", out1)
print("[wrote]", out2)
