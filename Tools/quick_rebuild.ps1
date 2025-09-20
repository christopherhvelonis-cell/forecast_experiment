param(
  [string]$Root = "$(Resolve-Path .)",
  [string]$YearsCsv = "1985,1990,1995,2000,2005,2010,2015,2020"
)

Write-Host "== Forecast Experiment quick rebuild =="
Write-Host ("Root: " + $Root)

Set-Location $Root

function Resolve-Tool {
  param(
    [string]$CandidateRootRel,
    [string]$CandidateToolsRel,
    [string]$NameForError
  )
  if (Test-Path $CandidateRootRel) { return (Resolve-Path $CandidateRootRel).Path }
  if (Test-Path $CandidateToolsRel) { return (Resolve-Path $CandidateToolsRel).Path }
  $leaf = Split-Path $CandidateRootRel -Leaf
  $hit = Get-ChildItem -Recurse -ErrorAction SilentlyContinue -Filter $leaf | Select-Object -First 1
  if ($hit) { return $hit.FullName }
  throw ("Missing required file: " + $NameForError + " (looked in '.', 'Tools\', and recursively)")
}

# Prefer repo venv Python if present; otherwise fall back to system python/py
$repoVenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$py = $null
if (Test-Path $repoVenvPy) {
  $py = (Resolve-Path $repoVenvPy).Path
  # ensure child processes inherit venv on PATH
  $env:PATH = (Split-Path $py) + ";" + $env:PATH
} else {
  $pyCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pyCmd) { $py = $pyCmd.Path } else {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) { $py = $pyCmd.Path }
  }
}
if (-not $py) { throw "Python not found. Create venv at $($Root)\.venv or add Python to PATH." }

# Ensure Tools folder
$toolsDir = Join-Path $Root "Tools"
if (!(Test-Path $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null }

# Ensure minimal murphy_append.py exists
$murphyPath = Join-Path $toolsDir "murphy_append.py"
if (-not (Test-Path $murphyPath)) {
@'
#!/usr/bin/env python
import argparse, csv, pathlib, pandas as pd, numpy as np
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    ap.add_argument("--metricsdir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    md = pathlib.Path(a.metricsdir); outp = pathlib.Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    header = ["event","n","reliability","resolution","uncertainty","brier_mean"]
    cand_probs = ["event_probs.csv","events_probs.csv","event_probabilities.csv"]
    cand_outs  = ["event_outcomes.csv","events_outcomes.csv","event_labels.csv"]
    probs = next((md / c for c in cand_probs if (md / c).exists()), None)
    outs  = next((md / c for c in cand_outs  if (md / c).exists()), None)
    if probs is None or outs is None:
        with outp.open("w", newline="", encoding="utf-8") as f: csv.writer(f).writerow(header)
        print("[murphy] inputs missing; wrote empty {}".format(outp)); return 0
    def std(df):
        cols = {c.lower(): c for c in df.columns}; r = {}
        if "event" in cols: r[cols["event"]] = "event"
        if "horizon" in cols: r[cols["horizon"]] = "horizon"
        for k in ["p","prob","probability","event_prob","proba"]:
            if k in cols: r[cols[k]] = "p"
        for k in ["y","label","outcome","occurrence"]:
            if k in cols: r[cols[k]] = "y"
        return df.rename(columns=r)
    try:
        dfp = std(pd.read_csv(probs)); dfo = std(pd.read_csv(outs))
        keys = [c for c in ["event","horizon"] if c in dfp.columns and c in dfo.columns] or ["event"]
        df = pd.merge(dfp, dfo, on=keys, how="inner")
        if "p" not in df or "y" not in df or df.empty: raise RuntimeError("missing p/y or empty")
    except Exception as e:
        with outp.open("w", newline="", encoding="utf-8") as f: csv.writer(f).writerow(header)
        print("[murphy] fallback empty ({}); wrote {}".format(e, outp)); return 0
    df["bin"] = np.clip((df["p"]*10).astype(int), 0, 9)
    rows = []
    for ev, grp in df.groupby("event"):
        n = len(grp)
        if n == 0: rows.append({"event":ev,"n":0,"reliability":0,"resolution":0,"uncertainty":0,"brier_mean":0}); continue
        clim = grp["y"].mean(); rel = 0.0; res = 0.0; brier = ((grp["p"]-grp["y"])**2).mean()
        for _, g in grp.groupby("bin"):
            w = len(g)/n; pbar = g["p"].mean(); ybar = g["y"].mean()
            rel += w*(pbar-ybar)**2; res += w*(ybar-clim)**2
        unc = clim*(1-clim)
        rows.append({"event":ev,"n":int(n),"reliability":float(rel),"resolution":float(res),"uncertainty":float(unc),"brier_mean":float(brier)})
    pd.DataFrame(rows, columns=header).to_csv(outp, index=False, encoding="utf-8")
    print("[murphy] wrote {} (events={})".format(outp, len(rows))); return 0
if __name__ == "__main__": raise SystemExit(main())
'@ | Set-Content -Encoding UTF8 $murphyPath
  Write-Host "[created] Tools\murphy_append.py"
}

# Resolve tool/script paths
$sweepPy = if (Test-Path ".\sweep_and_route_coverage_by_year.py") {
  (Resolve-Path ".\sweep_and_route_coverage_by_year.py").Path
} elseif (Test-Path ".\Tools\sweep_and_route_coverage_by_year.py") {
  (Resolve-Path ".\Tools\sweep_and_route_coverage_by_year.py").Path
} else {
  $hit = Get-ChildItem -Recurse -ErrorAction SilentlyContinue -Filter "sweep_and_route_coverage_by_year.py" | Select-Object -First 1
  if ($hit) { $hit.FullName } else { throw "Missing required file: sweep_and_route_coverage_by_year.py" }
}
$runAccPs1 = Resolve-Tool ".\Tools\run_accuracy_pass.ps1" ".\Tools\run_accuracy_pass.ps1" "Tools\run_accuracy_pass.ps1"
$murphyPy  = (Resolve-Path $murphyPath).Path
$inventory = if (Test-Path ".\Tools\inventory.ps1") { (Resolve-Path ".\Tools\inventory.ps1").Path } else { $null }

Write-Host ("Using:")
Write-Host ("  sweep:   " + $sweepPy)
Write-Host ("  runner:  " + $runAccPs1)
Write-Host ("  murphy:  " + $murphyPy)
if ($inventory) { Write-Host ("  inventory: " + $inventory) }

# Optional inventory
if ($inventory) {
  powershell -ExecutionPolicy Bypass -File $inventory -Root $Root | Out-Host
}

# Rebuild coverage for specific years
$regenYears = @("1985","1990","2000","2015","2020")
foreach ($y in $regenYears) {
  Write-Host ("==> Building coverage diagnostics for " + $y)
  & $py $sweepPy `
     --origin $y `
     --config ".\configs\experiment.yml" `
     --scoring ".\configs\scoring.yml" `
     --indicators ".\configs\indicators.yml" `
     --outdir (Join-Path ".\eval\results\diagnostics" ("FINAL_" + $y)) `
     --require_vintage true `
     --save_calibrated_points true
  if ($LASTEXITCODE -ne 0) { throw ("Coverage sweep failed for " + $y) }
}

# Determine which origins actually have non-empty coverage
function Has-Coverage {
  param([string]$Year)
  $p = Join-Path (Join-Path ".\eval\results\diagnostics" ("FINAL_" + $Year)) "coverage_points_calibrated.csv"
  if (!(Test-Path $p)) { return $false }
  $info = Get-Item $p
  return ($info.Length -gt 0)
}

$allYears = $YearsCsv.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
$covOK, $covMiss = @(), @()
foreach ($y in $allYears) { if (Has-Coverage -Year $y) { $covOK += $y } else { $covMiss += $y } }

if ($covMiss.Count -gt 0) { Write-Warning ("Coverage not available for: " + ($covMiss -join ", ") + " - skipping these origins for scoring.") }
if ($covOK.Count -eq 0) { throw "No origins have usable coverage; cannot continue." }
Write-Host ("Scoring will run for origins: " + ($covOK -join ", "))

# Ensure header fixer exists, then run it
$fixer = Join-Path $Root "Tools\fix_lossdiff_headers.py"
if (-not (Test-Path $fixer)) {
@'
import sys, csv, pathlib
EXPECTED = ["indicator","horizon","covered_50_rate","covered_90_rate","loss50_abs_error","loss90_abs_error"]
def fix_one(path):
    p = pathlib.Path(path)
    rows = list(csv.DictReader(p.open(newline="", encoding="utf-8"))) if p.exists() else []
    if not rows:
        print("[skip] {} (missing or empty)".format(p)); return
    keys = list(rows[0].keys())
    if keys == EXPECTED:
        print("[ok] {}".format(p)); return
    mapping = {}
    for k in keys:
        lk = k.lower()
        if ("50" in lk) and ("cover" in lk): mapping[k] = "covered_50_rate"
        elif ("90" in lk) and ("cover" in lk): mapping[k] = "covered_90_rate"
        elif ("loss" in lk) and ("50" in lk): mapping[k] = "loss50_abs_error"
        elif ("loss" in lk) and ("90" in lk): mapping[k] = "loss90_abs_error"
        elif lk.startswith("ind"): mapping[k] = "indicator"
        elif lk.startswith("hor"): mapping[k] = "horizon"
        else: mapping[k] = k
    out = [{mapping.get(k,k): v for k,v in r.items()} for r in rows]
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPECTED)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in EXPECTED})
    print("[fixed] {}".format(p))
if __name__ == "__main__":
    base = pathlib.Path("eval/results")
    for ydir in base.rglob("FINAL_*"):
        f = ydir / "loss_differences.csv"
        if f.exists(): fix_one(f)
'@ | Set-Content -Encoding UTF8 $fixer
  Write-Host "[created] Tools\fix_lossdiff_headers.py"
}
& $py $fixer
if ($LASTEXITCODE -ne 0) { throw "Header fix failed." }

# ---- RUN ACCURACY PASS (detect -Repo/-Python params; pass Int32[] years) ----
Write-Host "==> Running accuracy pass"
[int[]]$yearsArr = @(); foreach ($y in $covOK) { $yearsArr += [int]$y }

$runnerMeta = Get-Command -ErrorAction SilentlyContinue $runAccPs1
$hasYears     = $false
$hasYearsEval = $false
$hasYearsSig  = $false
$hasRepo      = $false
$hasPython    = $false
$hasPy        = $false
if ($runnerMeta -and $runnerMeta.Parameters) {
  $hasYears     = $runnerMeta.Parameters.ContainsKey("Years")
  $hasYearsEval = $runnerMeta.Parameters.ContainsKey("YearsEval")
  $hasYearsSig  = $runnerMeta.Parameters.ContainsKey("YearsSig")
  $hasRepo      = $runnerMeta.Parameters.ContainsKey("Repo")
  $hasPython    = $runnerMeta.Parameters.ContainsKey("Python")
  $hasPy        = $runnerMeta.Parameters.ContainsKey("Py")
}

$args = @(
  "-Config", ".\configs\experiment.yml",
  "-Scoring", ".\configs\scoring.yml",
  "-Indicators", ".\configs\indicators.yml"
)
if ($hasRepo)   { $args += @("-Repo", $Root) }
if ($hasPython) { $args += @("-Python", $py) }
elseif ($hasPy) { $args += @("-Py", $py) }

if ($hasYearsEval -or $hasYearsSig) {
  if ($hasYearsEval) { $args += @("-YearsEval"); $args += $yearsArr }
  if ($hasYearsSig)  { $args += @("-YearsSig");  $args += $yearsArr }
} elseif ($hasYears) {
  $args += @("-Years"); $args += $yearsArr
} else {
  Write-Warning "Runner exposes no -Years/-YearsEval/-YearsSig. Proceeding without explicit year filter."
}

powershell -ExecutionPolicy Bypass -File $runAccPs1 @args
if ($LASTEXITCODE -ne 0) { throw "Accuracy pass failed." }

# Murphy decomposition for available years
foreach ($y in $covOK) {
  $metricsDir = Join-Path ".\eval\results\metrics" ("FINAL_" + $y)
  if (Test-Path $metricsDir) {
    Write-Host ("==> Murphy decomposition for " + $y)
    & $py $murphyPy `
       --origin $y `
       --metricsdir $metricsDir `
       --out (Join-Path $metricsDir "murphy_decomposition.csv")
    if ($LASTEXITCODE -ne 0) { throw ("Murphy decomposition failed for " + $y) }
  }
}

Write-Host "== Done. Metrics and Murphy decomposition updated."
Write-Host ("Skipped origins (no coverage): " + (($covMiss -join ", ") -replace '^$', '<none>'))
