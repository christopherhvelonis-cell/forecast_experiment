import pandas as pd

d = pd.read_csv(r"ensemble\quantiles_ensemble.csv")
d["quantile"] = d["quantile"].astype(float).round(2)

rows = []
for (indicator, horizon, origin_year), g in d.groupby(["indicator","horizon","origin_year"]):
    q = dict(zip(g["quantile"], g["value"]))
    if all(x in q for x in (0.05, 0.50, 0.95)):
        q25 = q[0.05] + (0.25-0.05)*(q[0.50]-q[0.05])/(0.50-0.05)
        q75 = q[0.50] + (0.75-0.50)*(q[0.95]-q[0.50])/(0.95-0.50)
        rows.append([indicator, horizon, origin_year, q[0.05], q25, q[0.50], q75, q[0.95]])

out = pd.DataFrame(rows, columns=["indicator","horizon","origin_year","q05","q25","q50","q75","q95"])
out.to_csv(r"ensemble\central_with_bands.csv", index=False)
print(f"[ok] wrote ensemble\\central_with_bands.csv rows={len(out)}")
