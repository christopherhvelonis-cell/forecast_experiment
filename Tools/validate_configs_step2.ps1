# validate_configs_step2.ps1
param(
  [Parameter(Mandatory=$true)] [string]$Indicators,
  [Parameter(Mandatory=$true)] [string]$Baselines,
  [Parameter(Mandatory=$true)] [string]$Out
)

# --- Helpers ---
function Read-Text([string]$p) {
  if(!(Test-Path -LiteralPath $p)){ throw "File not found: $p" }
  return Get-Content -LiteralPath $p -Raw -Encoding UTF8
}

# Very lightweight YAML-ish parsing for our specific files

# Parse indicators.yml where items look like:
# - name: foo
#   transform: ...
#   data_vintage_available: ...
#   mode_changes: ...
#   break_flags: ...
function Parse-Indicators([string]$text) {
  # Split into blocks beginning with a top-level "- "
  # Keep the leading "- " with each block for easier regexes
  $blocks = @()
  $lines  = $text -split "`r?`n"
  $current = New-Object System.Collections.Generic.List[string]
  foreach($ln in $lines){
    if($ln -match '^[\s-]*-\s' -and ($ln -match '^\s*-\s')){
      if($current.Count -gt 0){ $blocks += ($current -join "`n"); $current.Clear() }
    }
    $current.Add($ln)
  }
  if($current.Count -gt 0){ $blocks += ($current -join "`n") }

  # If file was a top-level list without leading dash (unlikely), fallback to whole text as one block
  if($blocks.Count -eq 0){ $blocks = @($text) }

  $items = @()
  foreach($b in $blocks){
    $name     = ($b | Select-String -Pattern '^\s*-\s*name\s*:\s*(.+)$' -AllMatches).Matches |
                ForEach-Object { $_.Groups[1].Value.Trim() } | Select-Object -First 1
    if(-not $name){
      $name = ($b | Select-String -Pattern '^\s*name\s*:\s*(.+)$' -AllMatches).Matches |
              ForEach-Object { $_.Groups[1].Value.Trim() } | Select-Object -First 1
    }
    if(-not $name){ $name = "<missing_name>" }

    $hasTransform = [bool]([regex]::IsMatch($b,'(?m)^\s*(?:-\s*)?transform\s*:'))
    $hasVintage   = [bool]([regex]::IsMatch($b,'(?m)^\s*(?:-\s*)?data_vintage_available\s*:'))
    $hasMode      = [bool]([regex]::IsMatch($b,'(?m)^\s*(?:-\s*)?mode_changes\s*:'))
    $hasBreaks    = [bool]([regex]::IsMatch($b,'(?m)^\s*(?:-\s*)?break_flags\s*:'))

    $items += [pscustomobject]@{
      Name               = $name
      HasTransform       = $hasTransform
      HasVintage         = $hasVintage
      HasModeChanges     = $hasMode
      HasBreakFlags      = $hasBreaks
      Raw                = $b
    }
  }
  return $items
}

# Parse baselines.yml top-level keys like:
# persistence:
# linear_trend:
# ...
function Parse-Baselines([string]$text) {
  $keys = @()
  $lines = $text -split "`r?`n"
  foreach($ln in $lines){
    if($ln -match '^[A-Za-z0-9_]+:\s*(#.*)?$'){
      $keys += ($ln -replace ':.*$','').Trim()
    }
  }
  return ($keys | Select-Object -Unique)
}

# --- Main ---
try {
  $indText = Read-Text $Indicators
  $baseText = Read-Text $Baselines

  $indItems = Parse-Indicators $indText
  $baseKeys = Parse-Baselines $baseText

  $requiredBaselines = @('persistence','linear_trend','random_walk_drift','ets_local_level','equal_weight_combination')
  $missingBaselines = @()
  foreach($rb in $requiredBaselines){
    if($baseKeys -notcontains $rb){ $missingBaselines += $rb }
  }

  $problems = @()
  $names = @()
  foreach($it in $indItems){
    $names += $it.Name
    if(-not $it.HasTransform){ $problems += ("[indicators.yml] $($it.Name): missing 'transform'") }
    if(-not $it.HasVintage)  { $problems += ("[indicators.yml] $($it.Name): missing 'data_vintage_available'") }
    if(-not $it.HasModeChanges){ $problems += ("[indicators.yml] $($it.Name): missing 'mode_changes'") }
    if(-not $it.HasBreakFlags){ $problems += ("[indicators.yml] $($it.Name): missing 'break_flags'") }
  }

  $mustHaveIndicators = @('ba_plus_25plus_share','trust_media_pct')
  $missingUsed = @()
  foreach($m in $mustHaveIndicators){
    if($names -notcontains $m){ $missingUsed += $m }
  }

  # Build markdown
  $outLines = New-Object System.Collections.Generic.List[string]
  $outLines.Add("# Step 2 Audit - Configs")
  $outLines.Add("")
  $outLines.Add("**Indicators file:** $Indicators")
  $outLines.Add("**Baselines file:**  $Baselines")
  $outLines.Add("")
  $outLines.Add("## Indicators present")
  if($names.Count -gt 0){
    foreach($n in $names){ $outLines.Add("- $n") }
  } else {
    $outLines.Add("(none found)")
  }
  $outLines.Add("")

  if($missingUsed.Count -gt 0){
    $outLines.Add("## MISSING required indicators (used earlier)")
    foreach($m in $missingUsed){ $outLines.Add("- $m") }
  } else {
    $outLines.Add("All required indicators used earlier are present (ba_plus_25plus_share, trust_media_pct).")
  }
  $outLines.Add("")

  if($problems.Count -gt 0){
    $outLines.Add("## Indicator field warnings")
    foreach($p in $problems){ $outLines.Add("- $p") }
  } else {
    $outLines.Add("No indicator field warnings detected (transform, data_vintage_available, mode_changes, break_flags present for each).")
  }
  $outLines.Add("")

  $outLines.Add("## Baselines")
  if($baseKeys.Count -gt 0){
    $outLines.Add("Present: " + ($baseKeys -join ", "))
  } else {
    $outLines.Add("Present: (none)")
  }
  if($missingBaselines.Count -gt 0){
    $outLines.Add("**Missing recommended baselines:** " + ($missingBaselines -join ", "))
  } else {
    $outLines.Add("All recommended baselines found.")
  }
  $outLines.Add("")

  $outDir = Split-Path -Parent $Out
  if($outDir -and -not (Test-Path -LiteralPath $outDir)){ New-Item -ItemType Directory -Path $outDir | Out-Null }
  $outLines -join "`r`n" | Set-Content -LiteralPath $Out -Encoding UTF8
  Write-Host "[validate_configs_step2] wrote $Out"
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
