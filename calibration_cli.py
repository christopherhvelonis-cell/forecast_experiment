import os, sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from math import erf

# --- Path setup: ensure model + utils importable ---
REPO = Path(__file__).resolve().parent
COMMON_DIR = REPO / "models" / "common"
HSM_DIR = REPO / "models" / "HSM_chatgpt"
sys.path.insert(0, str(COMMON_DIR))
sys.path.insert(0, str(HSM_DIR))

from utils import load_indicator
from models.HSM_chatgpt.hsm import hsm_forecast

# --- Normal CDF helpers (no SciPy) ---
def _phi(z): 
    return np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)

def _Phi(z):
    # vectorized standard normal CDF via math.erf
    return 0.5 * (1.0 + np.vectorize(erf)(z / np.sqrt(2.0)))

# Useful z-values
Z05 = 1.6448536269514722
Z25 = 0.6744897501960817

def infer_mu_sigma(q5: float, q50: float, q95: float):
    """Infer Gaussian mu≈q50, sigma from (q5, q95)."""
    mu = float(q50)
    spread = float(q95 - q5)
    sigma = max(spread / (2 * Z05), 1e-6)  # since q95 - q5 = 2*z0.95*sigma
    return mu, sigma

def ks_uniform_D(pits: np.ndarray):
    """Kolmogorov–Smirnov D-statistic vs U(0,1), no SciPy."""
    # Sort and compare to i/(n)
    pits = np.sort(pits)
    n = len(pits)
    if n == 0:
        return np.nan
    i = np.arange(1, n + 1)
    D_plus = np.max(i / n - pits)
    D_minus = np.max(pits - (i - 1) / n)
    return float(max(D_plus, D_minus))

def compute_calibration(indicators, origins, H=15, out_dir="eval/calibration", bins=10, plots=False):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_pit = []        # per (indicator, origin, h): pit
    rows_cover = []      # per (indicator, origin, h): inside50, inside90

    for origin in origins:
        # get quantiles from HSM for this origin
        qdict = hsm_forecast(indicators, origin, H)

        for ind in indicators:
            # observed values series (year-indexed, 'imputed' column in utils)
            s = load_indicator(ind)

            # quantiles for 1..H
            qdf = qdict[ind]  # columns q5,q50,q95; index = horizon
            for h in range(1, H + 1):
                year = origin + h
                if year not in s.index:
                    continue  # no target

                y = float(s.loc[year])
                q5 = float(qdf.loc[h, "q5"])
                q50 = float(qdf.loc[h, "q50"])
                q95 = float(qdf.loc[h, "q95"])

                mu, sigma = infer_mu_sigma(q5, q50, q95)

                # PIT
                z = (y - mu) / max(sigma, 1e-9)
                pit = float(_Phi(z))
                rows_pit.append({"indicator": ind, "origin": origin, "horizon": h, "year": year, "y": y, "mu": mu, "sigma": sigma, "pit": pit})

                # Coverage checks:
                # 50% nominal: [q25,q75]; 90% nominal: [q10,q90]
                # derive from mu/sigma (Gaussian)
                q25 = mu - Z25 * sigma
                q75 = mu + Z25 * sigma
                q10 = mu - (Z05 / 1.6448536269514722) * Z05 * sigma  # but Z10=1.28155..., compute directly:
                Z10 = 1.2815515655446004
                q10 = mu - Z10 * sigma
                q90 = mu + Z10 * sigma

                inside50 = int(q25 <= y <= q75)
                inside90 = int(q10 <= y <= q90)

                rows_cover.append({"indicator": ind, "origin": origin, "horizon": h, "year": year,
                                   "inside50": inside50, "inside90": inside90})

    # Save PIT values
    pit_df = pd.DataFrame(rows_pit)
    pit_csv = out_dir / "pit_values.csv"
    pit_df.to_csv(pit_csv, index=False)

    # Coverage summary
    cover_df = pd.DataFrame(rows_cover)
    def summarize_cover(df, name):
        if df.empty:
            return pd.DataFrame([{"indicator": name, "n": 0,
                                  "cov50": np.nan, "err50_pp": np.nan,
                                  "cov90": np.nan, "err90_pp": np.nan}])
        n = len(df)
        cov50 = float(df["inside50"].mean()) if n else np.nan
        cov90 = float(df["inside90"].mean()) if n else np.nan
        return pd.DataFrame([{"indicator": name, "n": n,
                              "cov50": cov50, "err50_pp": (cov50 - 0.50) * 100.0,
                              "cov90": cov90, "err90_pp": (cov90 - 0.90) * 100.0}])

    parts = []
    for ind, g in cover_df.groupby("indicator"):
        parts.append(summarize_cover(g, ind))
    parts.append(summarize_cover(cover_df, "ALL"))
    coverage_summary = pd.concat(parts, ignore_index=True)
    coverage_csv = out_dir / "coverage_summary.csv"
    coverage_summary.to_csv(coverage_csv, index=False)

    # PIT KS summary
    def summarize_pit(df, name):
        if df.empty:
            return pd.DataFrame([{"indicator": name, "n": 0, "ks_D": np.nan}])
        pits = df["pit"].to_numpy(dtype=float)
        D = ks_uniform_D(pits)
        return pd.DataFrame([{"indicator": name, "n": len(df), "ks_D": D}])

    parts = []
    for ind, g in pit_df.groupby("indicator"):
        parts.append(summarize_pit(g, ind))
    parts.append(summarize_pit(pit_df, "ALL"))
    pit_summary = pd.concat(parts, ignore_index=True)
    pit_sum_csv = out_dir / "pit_summary.csv"
    pit_summary.to_csv(pit_sum_csv, index=False)

    # Optional plots
    if plots:
        try:
            import matplotlib.pyplot as plt

            # PIT hist per indicator
            for ind, g in pit_df.groupby("indicator"):
                if g.empty:
                    continue
                plt.figure()
                plt.hist(g["pit"].to_numpy(), bins=bins, range=(0, 1), edgecolor="black")
                plt.xlabel("PIT")
                plt.ylabel("Count")
                plt.title(f"PIT histogram — {ind}")
                plt.tight_layout()
                plt.savefig(out_dir / f"pit_hist_{ind}.png", dpi=150)
                plt.close()

            # Coverage bar per indicator
            for _, row in coverage_summary.iterrows():
                ind = row["indicator"]
                if ind == "ALL":
                    continue
                cov50 = row["cov50"]; cov90 = row["cov90"]
                if pd.isna(cov50) or pd.isna(cov90):
                    continue
                plt.figure()
                xs = np.arange(2)
                vals = [cov50, cov90]
                plt.bar(xs, vals)
                plt.xticks(xs, ["50% nominal", "90% nominal"])
                plt.ylim(0, 1)
                plt.title(f"Coverage — {ind}")
                plt.tight_layout()
                plt.savefig(out_dir / f"coverage_{ind}.png", dpi=150)
                plt.close()
        except Exception as e:
            print(f"[WARN] Plotting failed: {e}")

    print(f"[Calibration] Wrote:\n - {pit_csv}\n - {coverage_csv}\n - {pit_sum_csv}")
    if plots:
        print(f"[Calibration] Plots in {out_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicators", nargs="+", required=True, help="Indicators to evaluate")
    ap.add_argument("--origins", nargs="+", required=True, type=int, help="Origin years")
    ap.add_argument("--h", type=int, default=15, help="Forecast horizon for evaluation")
    ap.add_argument("--out_dir", type=str, default="eval/calibration", help="Output directory")
    ap.add_argument("--bins", type=int, default=10, help="PIT histogram bins")
    ap.add_argument("--plots", action="store_true", help="Save PNG plots")
    args = ap.parse_args()

    compute_calibration(args.indicators, args.origins, H=args.h, out_dir=args.out_dir, bins=args.bins, plots=args.plots)

if __name__ == "__main__":
    main()
