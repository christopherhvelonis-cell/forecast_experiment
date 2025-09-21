param(
  [string]$Repo
)
$ErrorActionPreference = "Stop"
$py = Join-Path $Repo ".venv\Scripts\python.exe"

# 1) Ensure the coverage files have 0.50 / 0.90 rows
& $py (Join-Path $Repo "Tools\ensure_coverage_levels.py") 1995 2000 2005 2010

# 2) If needed, apply simple conformal patch to hit targets (proxy)
& $py (Join-Path $Repo "Tools\simple_conformal_patch.py") 1995 2000 2005 2010

# 3) Recompute calibration summary
& $py (Join-Path $Repo "Tools\calibration_check.py") 1995 2000 2005 2010

# 4) Re-run acceptance gate
powershell -ExecutionPolicy Bypass -File (Join-Path $Repo "Tools\acceptance_gate.ps1") -Root $Repo
