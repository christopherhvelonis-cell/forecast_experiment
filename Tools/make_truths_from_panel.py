import argparse, pandas as pd, pathlib
parser = argparse.ArgumentParser()
parser.add_argument("--panel_csv", required=True)
parser.add_argument("--origin", type=int, required=True)
parser.add_argument("--indicators", nargs="+", required=True)
parser.add_argument("--out_csv", required=True)
parser.add_argument("--max_h", type=int, default=15)
args = parser.parse_args()

panel = pd.read_csv(args.panel_csv)
if "year" not in panel.columns:
    raise SystemExit("panel must have a 'year' column")

need = ["year"] + args.indicators
missing = [c for c in args.indicators if c not in panel.columns]
if missing:
    raise SystemExit(f"missing indicator columns in panel: {missing}")

panel = panel[need].set_index("year")
rows = []
for ind in args.indicators:
    for h in range(1, args.max_h + 1):
        y = args.origin + h
        if y in panel.index:
            rows.append({"indicator": ind, "horizon": h, "truth": panel.at[y, ind]})
out = pd.DataFrame(rows, columns=["indicator","horizon","truth"])
pathlib.Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
out.to_csv(args.out_csv, index=False)
print(f"[truths] wrote {len(out)} rows to {args.out_csv}")
