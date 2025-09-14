# run_fsm_grok.py
from __future__ import annotations

import argparse
from pathlib import Path

from models.FSM_grok.fsm import fsm_forecast
from models.common.utils import save_quantiles_csv

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True)
    ap.add_argument("--origin", type=int, required=True)
    ap.add_argument("--h_scored", type=int, default=15)
    ap.add_argument("--h_scenario", type=int, default=40)
    ap.add_argument("--n_paths", type=int, default=10000)
    ap.add_argument("--lam", type=float, default=0.2)
    ap.add_argument("--t_df", type=float, default=4.0)
    ap.add_argument("--out_scored", type=str, default="models/FSM_grok/scored.csv")
    ap.add_argument("--out_scenario", type=str, default="models/FSM_grok/scenarios.csv")
    args = ap.parse_args()

    res = fsm_forecast(
        args.indicators, args.origin, args.h_scored, args.h_scenario, args.n_paths, args.lam, args.t_df
    )
    save_quantiles_csv(res["scored"], Path(args.out_scored))
    save_quantiles_csv(res["scenario"], Path(args.out_scenario))
    print(f"[FSM_grok] wrote {args.out_scored} and {args.out_scenario}")

if __name__ == "__main__":
    main()