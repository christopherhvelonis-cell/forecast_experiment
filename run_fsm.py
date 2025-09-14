import sys, os
from pathlib import Path

# Ensure repo root and models/common are importable
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.join(REPO_ROOT, "models", "common")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, COMMON_DIR)

import argparse
from models.FSM_chatgpt.fsm import fsm_forecast
from utils import save_quantiles_csv  # from models/common/utils.py

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True,
                    help="Indicator names matching files in data/processed/<name>.csv")
    ap.add_argument("--origin", type=int, required=True, help="Origin year (inclusive)")
    ap.add_argument("--h_scored", type=int, default=15, help="Scored forecast horizon (years)")
    ap.add_argument("--h_scenario", type=int, default=40, help="Scenario horizon (years)")
    ap.add_argument("--out_scored", type=str, default="eval/results/fsm_quantiles_scored.csv",
                    help="Output CSV for scored quantiles")
    ap.add_argument("--out_scenario", type=str, default="eval/results/fsm_quantiles_scenario.csv",
                    help="Output CSV for scenario quantiles")
    ap.add_argument("--n_paths", type=int, default=10000, help="Number of simulated paths")
    ap.add_argument("--lambda_shock", type=float, default=0.2, help="Poisson shock rate per step")
    ap.add_argument("--t_df", type=int, default=4, help="Student-t df for shock severity")
    args = ap.parse_args()

    res = fsm_forecast(
        args.indicators,
        args.origin,
        args.h_scored,
        args.h_scenario,
        args.n_paths,
        args.lambda_shock,
        args.t_df,
    )

    Path("eval/results").mkdir(parents=True, exist_ok=True)
    save_quantiles_csv(res["scored"], Path(args.out_scored))
    save_quantiles_csv(res["scenario"], Path(args.out_scenario))
    print(f"[FSM] wrote {args.out_scored} and {args.out_scenario}")
