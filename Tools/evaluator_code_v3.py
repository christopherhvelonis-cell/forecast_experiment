import os
import pandas as pd

from ecc_schaake import ecc_reorder, schaake_shuffle
from meta_stacking_fforma import FFORMAStacker
from conformal_calibration import split_conformal_intervals
from ebma_psisloo import psis_loo_weights

def murphy_decomposition(df_probs: pd.DataFrame, y: pd.Series, prob_col: str = "p_event"):
    """Return reliability, resolution, uncertainty (Murphy 1973) - placeholder with zeros."""
    return {"reliability": 0.0, "resolution": 0.0, "uncertainty": float(y.mean()*(1-y.mean()))}

def main(diagnostics_dir: str, out_dir: str):
    # Hook placeholder to keep current v2 flow stable
    mpath = os.path.join(out_dir, "metrics_by_horizon.csv")
    if os.path.exists(mpath):
        met = pd.read_csv(mpath)
        met.to_csv(mpath, index=False)
    print("[Evaluator v3] Hooked (placeholders active).")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostics_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    main(args.diagnostics_dir, args.out_dir)
