param(
  [Parameter(Mandatory=$true)] [string]$Repo,
  [Parameter(Mandatory=$true)] [string]$Python,
  [Parameter(Mandatory=$true)] [string]$Config,
  [Parameter(Mandatory=$true)] [string]$Scoring,
  [Parameter(Mandatory=$true)] [string]$Indicators,
  [int[]]$YearsEval = @(1995,2000,2005,2010),
  [int[]]$YearsSig  = @(1995,2000,2005,2010)
)

$runner = Join-Path $Repo "Tools\run_accuracy_pass.ps1"
powershell -ExecutionPolicy Bypass -File $runner `
  -Repo $Repo -Python $Python -Config $Config -Scoring $Scoring -Indicators $Indicators `
  -YearsEval $YearsEval -YearsSig $YearsSig

# Post-run normalization (safe if a year is missing)
$fix = Join-Path $Repo "Tools\fix_lossdiff_headers.py"
foreach ($y in $YearsEval) {
  & $Python $fix $y 2>$null
}

# Optional spot-check + inventory
$expect = 'indicator,horizon,covered_50_rate,covered_90_rate,loss50_abs_error,loss90_abs_error'
foreach ($y in $YearsEval) {
  $p = Join-Path $Repo "eval\results\v2\FINAL_$y\loss_differences.csv"
  if (Test-Path $p) {
    $first = Get-Content $p -First 1
    Write-Host ("[{0}] {1}" -f $y, ($(if ($first -eq $expect){"OK"}else{"MISMATCH: $first"})))
  }
}
powershell -ExecutionPolicy Bypass -File (Join-Path $Repo "Tools\inventory.ps1") -Root $Repo
