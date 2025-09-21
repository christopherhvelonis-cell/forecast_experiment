param([string]$Repo)
$ErrorActionPreference = "Stop"
$py = Join-Path $Repo ".venv\Scripts\python.exe"

# Features + placeholder weights
& $py (Join-Path $Repo "Tools\build_stacking_features.py")
& $py (Join-Path $Repo "Tools\train_meta_stacking.py")

# TODO (next): use weights to fuse per-model outputs once you have per-model forecast CSVs.
Write-Host "[ensemble] features+weights produced (placeholder)."
