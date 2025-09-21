# Tools/run_ci.ps1
param([string]$Repo)
$ErrorActionPreference = "Stop"
$py = Join-Path $Repo ".venv\Scripts\python.exe"
# refresh derived artifacts quickly (optional)
powershell -ExecutionPolicy Bypass -File (Join-Path $Repo "Tools\acceptance_gate.ps1") -Root $Repo
# validate
& $py (Join-Path $Repo "Tools\validate_schema.py")
Write-Host "[ci-local] OK"
