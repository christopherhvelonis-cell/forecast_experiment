from __future__ import annotations
import argparse
from pathlib import Path
from models.HSM_chatgpt.hsm import hsm_forecast
from models.common.utils import save_quantiles_csv


if __name__ == "__main__":
ap = argparse.ArgumentParser()
ap.add_argument("--indicators", nargs="+", required=True)
ap.add_argument("--origin", type=int, required=True)
ap.add_argument("--h", type=int, default=15)
ap.add_argument("--out", type=str, default="eval/results/hsm_quantiles.csv")
args = ap.parse_args()


qdict = hsm_forecast(args.indicators, args.origin, args.h)
out_path = Path(args.out)
out_path.parent.mkdir(parents=True, exist_ok=True)
save_quantiles_csv(qdict, out_path)
print(f"[HSM] wrote {out_path}")