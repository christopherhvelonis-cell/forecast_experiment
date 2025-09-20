param([string]$Repo = (Resolve-Path ".").Path)

function Has($p){ if(Test-Path $p){"1"} else {"0"} }
function OkMiss($p){ if(Test-Path $p){"OK"} else {"MISSING"} }

Write-Host "=== INVENTORY+ for forecast_experiment ===" -ForegroundColor Cyan

# 1) configs
$cfgs = @(
  "configs/experiment.yml",
  "configs/scoring.yml",
  "configs/baselines.yml",
  "configs/indicators.yml",
  "configs/indicator_transform_spec.yml"
)
$cfgPresent = 0
$cfgs | ForEach-Object {
  $p = Join-Path $Repo $_
  $status = OkMiss $p
  if($status -eq "OK"){$cfgPresent++}
  Write-Host ("[CONFIG] {0,-35} {1}" -f $_, $status)
}

# 2) templates
$templates = Get-ChildItem (Join-Path $Repo "configs") -Filter "TEMPLATE_*" -ErrorAction SilentlyContinue
Write-Host "[TEMPLATES] found $($templates.Count)"

# 3) tools
$tools = @(
  "Tools/ecc_schaake.py",
  "Tools/meta_stacking_fforma.py",
  "Tools/conformal_calibration.py",
  "Tools/ebma_psisloo.py",
  "Tools/evaluator_code_v2_min.py",
  "Tools/evaluator_code_v3.py"
)
$toolsPresent = 0
$tools | ForEach-Object {
  $p = Join-Path $Repo $_
  $status = OkMiss $p
  if($status -eq "OK"){$toolsPresent++}
  Write-Host ("[TOOLS] {0,-30} {1}" -f (Split-Path $_ -Leaf), $status)
}

# 4) governance docs
$docs = @("data/vintages.md","data/revisions.md")
$docsPresent = 0
$docs | ForEach-Object {
  $p = Join-Path $Repo $_
  $status = OkMiss $p
  if($status -eq "OK"){$docsPresent++}
  Write-Host ("[DOC] {0,-30} {1}" -f $_, $status)
}

# 5) evaluation years (metrics+loss both present)
$evalRoot = Join-Path $Repo "eval\results\v2"
$finalDirs = @(Get-ChildItem $evalRoot -Directory -ErrorAction SilentlyContinue)
$yearsDone = 0
$rows = @()
foreach($d in $finalDirs){
  $m = Join-Path $d.FullName "metrics_by_horizon.csv"
  $l = Join-Path $d.FullName "loss_differences.csv"
  $mOK = Test-Path $m
  $lOK = Test-Path $l
  if($mOK -and $lOK){ $yearsDone++ }
  Write-Host ("[FINAL] {0,-15} metrics:{1} loss:{2}" -f $d.Name, ($mOK?"Y":"N"), ($lOK?"Y":"N"))
  $rows += [pscustomobject]@{
    final_folder = $d.Name
    metrics = ($mOK?"Y":"N")
    loss    = ($lOK?"Y":"N")
  }
}

# Totals & percentages
$totalCfg = $cfgs.Count
$totalTools = $tools.Count
$totalDocs = $docs.Count
$totalYears = if($finalDirs){ $finalDirs.Count } else { 0 }

$cfgPct   = if($totalCfg){ [math]::Round(100*$cfgPresent/$totalCfg,1) } else { 0 }
$toolsPct = if($totalTools){ [math]::Round(100*$toolsPresent/$totalTools,1) } else { 0 }
$docsPct  = if($totalDocs){ [math]::Round(100*$docsPresent/$totalDocs,1) } else { 0 }
$evalPct  = if($totalYears){ [math]::Round(100*$yearsDone/$totalYears,1) } else { 0 }

# Simple overall (equal weight across 4 buckets)
$overallPct = [math]::Round(($cfgPct+$toolsPct+$docsPct+$evalPct)/4,1)

Write-Host ""
Write-Host ("[SUMMARY] Configs: {0}/{1} ({2}%)  Tools: {3}/{4} ({5}%)  Docs: {6}/{7} ({8}%)" -f `
  $cfgPresent,$totalCfg,$cfgPct,$toolsPresent,$totalTools,$toolsPct,$docsPresent,$totalDocs,$docsPct)
Write-Host ("[SUMMARY] Eval years ready: {0}/{1} ({2}%)" -f $yearsDone,$totalYears,$evalPct)
Write-Host ("[SUMMARY] Overall (simple average): {0}%" -f $overallPct) -ForegroundColor Green

# Export CSV + Markdown
$reportDir = Join-Path $Repo "reports"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$rows | Export-Csv (Join-Path $reportDir "inventory_finals.csv") -NoTypeInformation -Encoding UTF8
$md = @()
$md += "# Inventory Summary"
$md += ""
$md += "* Configs: $cfgPresent/$totalCfg ($cfgPct`%)"
$md += "* Tools: $toolsPresent/$totalTools ($toolsPct`%)"
$md += "* Governance docs: $docsPresent/$totalDocs ($docsPct`%)"
$md += "* Eval years ready: $yearsDone/$totalYears ($evalPct`%)"
$md += ""
$md += "**Overall (simple average): $overallPct`%**"
$md += ""
$md += "See `reports/inventory_finals.csv` for details per FINAL_*."
$md -join "`r`n" | Set-Content (Join-Path $reportDir "inventory_summary.md") -Encoding UTF8

Write-Host "Wrote: reports/inventory_finals.csv, reports/inventory_summary.md"
Write-Host "=== INVENTORY+ COMPLETE ===" -ForegroundColor Cyan
