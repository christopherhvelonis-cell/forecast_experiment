param(
  [string]$Repo = (Resolve-Path ".").Path,
  [int[]]$YearsEval = @(1985,1990,1995,2000,2005,2010,2015,2020),
  [int[]]$YearsSig  = @(1995,2000,2005,2010)
)

# --- find python in the repo venv (robust) ---
$pyCandidates = @(
  (Join-Path $Repo ".venv\Scripts\python.exe"),
  (Join-Path $Repo "venv\Scripts\python.exe"),
  (Join-Path $Repo "Scripts\python.exe")
)
$py = $pyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $py) { throw "Couldn't find Python venv in $Repo (.venv\Scripts\python.exe). Pass -Repo or activate venv." }

function Run([string[]]$argv) {
  & $py $argv
  if ($LASTEXITCODE -ne 0) { throw "Python failed: $($argv -join ' ')" }
}

Write-Host "[run] sweep coverage rows by year" -ForegroundColor Cyan
Run @((Join-Path $Repo 'Tools\sweep_and_route_coverage_by_year.py'))

foreach ($yr in $YearsEval) {
  $final = Join-Path $Repo ("eval\results\diagnostics\FINAL_{0}" -f $yr)
  $cov   = Join-Path $final "coverage_points_calibrated.csv"
  if (!(Test-Path $cov) -or ((Get-Content $cov | Measure-Object -Line).Lines -le 1)) {
    Write-Host "[SKIP] $($yr): no/empty coverage" -ForegroundColor Yellow
    continue
  }
  $out = Join-Path $Repo ("eval\results\v2\FINAL_{0}" -f $yr)
  if (!(Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

  Write-Host "[eval] FINAL_$($yr) -> evaluator v2 + backfill" -ForegroundColor Green
  Run @((Join-Path $Repo 'Tools\evaluator_code_v2_min.py'), '--diagnostics_dir', $final, '--out_dir', $out)
  Run @((Join-Path $Repo 'Tools\backfill_evaluator_artifacts.py'), $out)
}

Write-Host "[sig] run significance where metrics exist" -ForegroundColor Cyan
foreach ($yr in $YearsSig) {
  $out = Join-Path $Repo ("eval\results\v2\FINAL_{0}" -f $yr)
  $metrics = Join-Path $out 'metrics_by_horizon.csv'
  if (Test-Path $metrics) {
    Run @((Join-Path $Repo 'Tools\evaluator_significance_min.py'), '--metrics_csv', $metrics, '--out_dir', (Join-Path $out 'significance'))
  } else {
    Write-Host "[SKIP] $($yr): no metrics_by_horizon.csv" -ForegroundColor Yellow
  }
}

Write-Host "[check] verifying outputs" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $Repo 'Tools\check_outputs.ps1') -Root $Repo
