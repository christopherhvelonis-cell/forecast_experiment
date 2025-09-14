# run_hsm_grok.py
from __future__ import annotations

import argparse
from pathlib import Path

from models.HSM_grok.hsm import hsm_forecast
from models.common.utils import save_quantiles_csv

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--h", type=int, default=15)
    ap.add_argument("--h_scenario", type=int, default=40)
    ap.add_argument("--out", type=str, default="models/HSM_grok/predictions.csv")
    args = ap.parse_args()

    qdict = hsm_forecast(args.indicators, args.origin, args.h, args.h_scenario)
    save_quantiles_csv(qdict, Path(args.out))
    print(f"[HSM_grok] wrote {args.out}")

if __name__ == "__main__":
    main()