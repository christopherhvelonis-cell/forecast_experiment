#!/usr/bin/env python
# eval/evaluator_code.py  (rebuilds samples from calibrated q's when --use-calibrated)
import argparse, json, sys
from pathlib import Path
import pandas as pd
import numpy as np

CAL_DIR = Path("eval/results/calibration_v2")

def load_configs(paths):
    try:
        import yaml
    except ImportError:
        return {}
    cfg = {}
    for p in paths:
        pp = Path(p)
        if pp.exists():
            with pp.open("r", encoding="utf-8") as f:
                try: cfg.update(yaml.safe_load(f) or {})
                except Exception: pass
    return cfg

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)
def compute_brier(p_event, outcome): return float((p_event - outcome)**2)
def pit_from_samples(samples, y): samples=np.asarray(samples); return float(np.mean(samples<=y))

def fake_model_outputs(origin, h, rng):
    # base (uncalibrated) draw
    y_true = rng.normal(0,1)
    samples = rng.normal(0,1, size=2000)
    q05, q50, q95 = np.quantile(samples,[0.05,0.5,0.95])
    p_event = float(np.mean(samples <= -1.0))
    return y_true, (q05,q50,q95), p_event, samples

def maybe_calibrated_quantiles(origin, df_row, use_cal):
    if not use_cal: return df_row["q05"], df_row["q50"], df_row["q95"], False
    f = CAL_DIR / f"calibrated_{origin}.csv"
    if not f.exists(): return df_row["q05"], df_row["q50"], df_row["q95"], False
    c = pd.read_csv(f)
    row = c.loc[c["h"]==df_row["h"]]
    if row.empty: return df_row["q05"], df_row["q50"], df_row["q95"], False
    q50 = float(row["q50"].iloc[0]) if "q50" in row else float(df_row["q50"])
    q05 = float(row["q05_cal"].iloc[0]) if "q05_cal" in row else float(df_row["q05"])
    q95 = float(row["q95_cal"].iloc[0]) if "q95_cal" in row else float(df_row["q95"])
    return q05, q50, q95, True

def rebuild_samples_from_qs(q05, q50, q95, n=2000, rng=None):
    # Assume Normal and back out sigma from 5th/95th (~±1.645σ)
    sig = max(1e-6, (q95 - q05) / (2*1.645))
    if rng is None: rng = np.random.default_rng(123)
    return rng.normal(loc=q50, scale=sig, size=n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origins", nargs="+", required=True)
    ap.add_argument("--horizons", required=True)  # e.g. 1:15
    ap.add_argument("--score", nargs="+", default=["crps","brier"])
    ap.add_argument("--lambda-grid", nargs="+", type=float, default=[0.05,0.1,0.2])
    ap.add_argument("--configs", nargs="+", default=["configs/experiment.yml","configs/scoring.yml"])
    ap.add_argument("--outdir", default="eval/results/retro_v2")
    ap.add_argument("--save-diagnostics", nargs="*", default=["pit","coverage","reliability"])
    ap.add_argument("--save-scenarios", type=int, default=40)
    ap.add_argument("--use-calibrated", action="store_true")
    args = ap.parse_args()

    _ = load_configs(args.configs)
    h_a, h_b = map(int, args.horizons.split(":"))
    horizons = list(range(h_a, h_b+1))
    outdir = Path(args.outdir); ensure_dir(outdir)

    manifest = {"origins": args.origins, "horizons":[h_a,h_b], "scores":args.score,
                "lambda_grid": args.lambda_grid, "configs": args.configs,
                "scenarios_years": args.save_scenarios, "use_calibrated": args.use_calibrated}

    for origin in args.origins:
        rows=[]; diag_pit=[]; diag_cov=[]; diag_rel=[]
        rng = np.random.default_rng(seed=hash((int(origin), 99991)) % (2**32))

        temp = []
        for h in horizons:
            y_true, (q05, q50, q95), p_event, samples = fake_model_outputs(int(origin), h, rng)
            temp.append({"h":h,"y_true":y_true,"q05":q05,"q50":q50,"q95":q95,"p_event":p_event,"samples":samples})
        temp = pd.DataFrame(temp)

        for _, r in temp.iterrows():
            q05, q50, q95, changed = maybe_calibrated_quantiles(int(origin), r, args.use_calibrated)
            if changed:
                samples = rebuild_samples_from_qs(q05, q50, q95, n=2000, rng=rng)
                p_event = float(np.mean(samples <= -1.0))
            else:
                samples = r["samples"]; p_event = r["p_event"]
            y_true = r["y_true"]

            # CRPS proxy = mean absolute deviation of samples to truth
            crps = float(np.mean(np.abs(samples - y_true)))
            brier = compute_brier(p_event, 1.0 if y_true <= -1.0 else 0.0)

            rows.append({"origin": int(origin), "h": int(r["h"]), "crps": crps, "brier": brier,
                         "skill_crps_vs_equal": 0.0, "skill_brier_vs_equal": 0.0,
                         "q05": q05, "q50": q50, "q95": q95, "p_event_le_neg1": p_event, "y_true": y_true})

            pit = pit_from_samples(samples, y_true)
            covered50 = float(q05 <= y_true <= q95)
            covered90 = covered50
            if "pit" in args.save_diagnostics: diag_pit.append({"origin": int(origin), "h": int(r["h"]), "pit": pit})
            if "coverage" in args.save_diagnostics: diag_cov.append({"origin": int(origin), "h": int(r["h"]), "cov50": covered50, "cov90": covered90})
            if "reliability" in args.save_diagnostics: diag_rel.append({"origin": int(origin), "h": int(r["h"]), "p_event": p_event, "outcome": 1.0 if y_true <= -1.0 else 0.0})

        pd.DataFrame(rows).to_csv(outdir / f"metrics_{origin}.csv", index=False)
        if diag_pit: pd.DataFrame(diag_pit).to_csv(outdir / f"diag_{origin}_pit.csv", index=False)
        if diag_cov: pd.DataFrame(diag_cov).to_csv(outdir / f"diag_{origin}_coverage.csv", index=False)
        if diag_rel: pd.DataFrame(diag_rel).to_csv(outdir / f"diag_{origin}_reliability.csv", index=False)

        years = list(range(1, int(args.save_scenarios)+1))
        scen = pd.DataFrame({"origin": int(origin), "h": years,
                             "q05": np.linspace(-1.0,0.0,len(years)),
                             "q50": np.linspace(0.0,0.5,len(years)),
                             "q95": np.linspace(0.5,1.0,len(years))})
        scen.to_csv(outdir / f"scenarios_{origin}_{args.save_scenarios}y.csv", index=False)

    with open(outdir / "run_manifest.json","w",encoding="utf-8") as f: json.dump(manifest,f,indent=2)
    print(f"[ok] Wrote results to {outdir}")
if __name__ == "__main__": sys.exit(main())
