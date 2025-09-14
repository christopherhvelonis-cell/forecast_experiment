# validate_configs_step2_min.ps1 — resilient, text-only checks
param(
  [Parameter(Mandatory=$true)] [string]$Indicators,
  [Parameter(Mandatory=$true)] [string]$Baselines,
  [Parameter(Mandatory=$true)] [string]$Out
)

function Read-Text([string]$p) {
  if(!(Test-Path -LiteralPath $p)){ throw ("File not found: {0}" -f $p) }
  Get-Content -LiteralPath $p -Raw -Encoding UTF8
}

try {
  $indText  = Read-Text $Indicators
  $baseText = Read-Text $Baselines

  # --- Indicators: grab every 'name:' occurrence (very tolerant of formatting) ---
  $indNames = @()
  $rxName = [regex]'(?m)^\s*(?:-\s*)?name\s*:\s*(.+?)\s*$'
  foreach($m in $rxName.Matches($indText)) {
    $val = $m.Groups[1].Value.Trim()
    if($val){ $indNames += $val }
  }
  $indNames = $indNames | Select-Object -Unique

  # --- Baselines: treat any top-level-ish key as present (key:) ---
  $baseKeys = @()
  $rxKey = [regex]'(?m)^\s*([A-Za-z0-9_]+)\s*:\s*(?:#.*)?$'
  foreach($m in $rxKey.Matches($baseText)) {
    $baseKeys += $m.Groups[1].Value.Trim()
  }
  $baseKeys = $baseKeys | Select-Object -Unique

  # --- Checks ---
  $requiredBaselines = @('persistence','linear_trend','random_walk_drift','ets_local_level','equal_weight_combination')
  $missingBaselines  = @()
  foreach($rb in $requiredBaselines){
    if($baseKeys -notcontains $rb){ $missingBaselines += $rb }
  }

  $mustHaveIndicators = @('ba_plus_25plus_share','trust_media_pct')
  $missingIndicators  = @()
  foreach($m in $mustHaveIndicators){
    if($indNames -notcontains $m){ $missingIndicators += $m }
  }

  # --- Report ---
  $lines = New-Object System.Collections.Generic.List[string]
  $lines.Add("# Step 2 Audit - MIN")
  $lines.Add("")
  $lines.Add(("**Indicators file:** {0}" -f $Indicators))
  $lines.Add(("**Baselines file:**  {0}" -f $Baselines))
  $lines.Add("")
  $lines.Add("## Indicators present")
  if($indNames.Count -gt 0){
    foreach($n in $indNames){ $lines.Add(("- {0}" -f $n)) }
  } else {
    $lines.Add("(none found)")
  }
  $lines.Add("")
  if($missingIndicators.Count -gt 0){
    $lines.Add("**Missing required indicators used earlier:** " + ($missingIndicators -join ", "))
  } else {
    $lines.Add("All required indicators (ba_plus_25plus_share, trust_media_pct) are present.")
  }
  $lines.Add("")
  $lines.Add("## Baselines")
  $lines.Add(("Present: {0}" -f ($(if($baseKeys){ $baseKeys -join ", " } else { "(none)" }))))
  if($missingBaselines.Count -gt 0){
    $lines.Add(("**Missing recommended baselines:** {0}" -f ($missingBaselines -join ", ")))
  } else {
    $lines.Add("All recommended baselines found.")
  }
  $lines.Add("")
  $outDir = Split-Path -Parent $Out
  if($outDir -and -not (Test-Path -LiteralPath $outDir)){ New-Item -ItemType Directory -Path $outDir | Out-Null }
  $lines -join "`r`n" | Set-Content -LiteralPath $Out -Encoding UTF8

  Write-Host ("[validate_configs_step2_min] wrote {0}" -f $Out)
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
