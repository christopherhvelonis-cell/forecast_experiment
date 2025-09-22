#!/usr/bin/env python3
"""
Validate ECC/Schaake joint draws:
- Marginal check: empirical 5/50/95 from draws vs ensemble quantiles
- Coverage check: share within [q05,q95]
- Dependence check: cross-indicator correlations per (origin_year,horizon)

Inputs:
  - ensemble/joint_paths_ecc.csv   (origin_year,draw_id,horizon,indicator,value)
  - ensemble/quantiles_ensemble.csv (indicator,horizon,origin_year,quantile,value)

Outputs:
  - eval/results/ecc_marginal_check.csv
      indicator,origin_year,horizon,emp_q05,emp_q50,emp_q95,tgt_q05,tgt_q50,tgt_q95,abs_err_q05,abs_err_q50,abs_err_q95,coverage_5_95
  - eval/results/ecc_correlations.csv
      origin_year,horizon,indicator_i,indicator_j,corr
  - Appends a brief section to REPORT.md
"""

import os, numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENS_DIR = os.path.join(ROOT, "ensemble")
RES_DIR = os.path.join(ROOT, "eval", "results")
RPT = os.path.join(ROOT, "REPORT.md")

JOINT = os.path.join(ENS_DIR, "joint_paths_ecc.csv")
QENS  = os.path.join(ENS_DIR, "quantiles_ensemble.csv")
OUT_M = os.path.join(RES_DIR, "ecc_marginal_check.csv")
OUT_C = os.path.join(RES_DIR, "ecc_correlations.csv")

def main():
    if not os.path.exists(JOINT):
        raise SystemExit(f"[error] missing {os.path.relpath(JOINT, ROOT)}")
    if not os.path.exists(QENS):
        raise SystemExit(f"[error] missing {os.path.relpath(QENS, ROOT)}")

    draws = pd.read_csv(JOINT)
    draws["origin_year"] = draws["origin_year"].astype(int)
    draws["horizon"] = draws["horizon"].astype(int)
    draws["indicator"] = draws["indicator"].astype(str)

    q = pd.read_csv(QENS)
    q["origin_year"] = q["origin_year"].astype(int)
    q["horizon"] = q["horizon"].astype(int)
    q["indicator"] = q["indicator"].astype(str)
    q["quantile"] = q["quantile"].astype(float)

    # ---- Marginal check
    rows = []
    for (ind, oy, h), g in draws.groupby(["indicator","origin_year","horizon"]):
        emp_q05, emp_q50, emp_q95 = np.quantile(g["value"].to_numpy(), [0.05, 0.5, 0.95])
        tgt = q[(q["indicator"]==ind)&(q["origin_year"]==oy)&(q["horizon"]==h)]
        if tgt.empty:  # shouldn’t happen, but guard
            continue
        def tq(t): 
            s = tgt.loc[np.isclose(tgt["quantile"], t), "value"]
            return float(s.iloc[0]) if not s.empty else np.nan
        tgt_q05, tgt_q50, tgt_q95 = tq(0.05), tq(0.5), tq(0.95)
        band_low, band_high = tgt_q05, tgt_q95
        cov = np.mean((g["value"] >= band_low) & (g["value"] <= band_high))
        rows.append(dict(
            indicator=ind, origin_year=int(oy), horizon=int(h),
            emp_q05=float(emp_q05), emp_q50=float(emp_q50), emp_q95=float(emp_q95),
            tgt_q05=float(tgt_q05), tgt_q50=float(tgt_q50), tgt_q95=float(tgt_q95),
            abs_err_q05=abs(emp_q05 - tgt_q05),
            abs_err_q50=abs(emp_q50 - tgt_q50),
            abs_err_q95=abs(emp_q95 - tgt_q95),
            coverage_5_95=float(cov)
        ))
    marg = pd.DataFrame(rows).sort_values(["origin_year","horizon","indicator"])
    os.makedirs(RES_DIR, exist_ok=True)
    marg.to_csv(OUT_M, index=False)

    # ---- Dependence check: correlation across indicators for each (oy,h)
    cor_rows = []
    for (oy, h), g in draws.groupby(["origin_year","horizon"]):
        # pivot draws: rows=draw_id, cols=indicator
        piv = g.pivot_table(index="draw_id", columns="indicator", values="value", aggfunc="first")
        if piv.shape[1] >= 2:
            C = piv.corr()
            inds = list(C.columns)
            for i in range(len(inds)):
                for j in range(i+1, len(inds)):
                    cor_rows.append(dict(
                        origin_year=int(oy), horizon=int(h),
                        indicator_i=str(inds[i]), indicator_j=str(inds[j]),
                        corr=float(C.iloc[i,j])
                    ))
    cors = pd.DataFrame(cor_rows).sort_values(["origin_year","horizon","indicator_i","indicator_j"])
    cors.to_csv(OUT_C, index=False)

    # ---- Append to REPORT.md
    mean_abs_q05 = marg["abs_err_q05"].mean() if not marg.empty else float("nan")
    mean_abs_q50 = marg["abs_err_q50"].mean() if not marg.empty else float("nan")
    mean_abs_q95 = marg["abs_err_q95"].mean() if not marg.empty else float("nan")
    cov_mean     = marg["coverage_5_95"].mean() if not marg.empty else float("nan")
    lines = []
    lines.append("\n## ECC/Schaake Validation\n")
    lines.append(f"- Mean |emp−tgt| at q05/q50/q95: **{mean_abs_q05:.4f} / {mean_abs_q50:.4f} / {mean_abs_q95:.4f}**")
    lines.append(f"- Mean empirical coverage within [q05,q95]: **{cov_mean:.3f}** (target ≈ 0.90)")
    lines.append(f"- Correlations saved to: `eval/results/ecc_correlations.csv`")
    with open(RPT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[ok] wrote {OUT_M} rows={len(marg)}")
    print(f"[ok] wrote {OUT_C} rows={len(cors)}")
    print("[ok] appended ECC/Schaake validation summary to REPORT.md")

if __name__ == "__main__":
    main()
