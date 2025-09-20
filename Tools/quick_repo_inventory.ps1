param(
  [Parameter(Mandatory=$true)][string]$Root
)

# --- helpers ---
function ExistsFile($p){ Test-Path $p -PathType Leaf }
function ExistsDir($p){ Test-Path $p -PathType Container }
function CountMatches($path, $pattern) {
  if (!(Test-Path $path)) { return 0 }
  try { ((Get-Content -Raw -Encoding UTF8 $path) -split "`r?`n") -match $pattern | Measure-Object | Select -Expand Count }
  catch { 0 }
}

$now = Get-Date
$stamp = $now.ToString('yyyy-MM-dd_HH-mm-ss')

# --- A) core structure ---
$structure = [ordered]@{
  configs            = ExistsDir (Join-Path $Root 'configs')
  data_raw           = ExistsDir (Join-Path $Root 'data\raw')
  data_processed     = ExistsDir (Join-Path $Root 'data\processed')
  data_docsheets     = ExistsDir (Join-Path $Root 'data\docsheets')
  eval_diag          = ExistsDir (Join-Path $Root 'eval\results\diagnostics')
  eval_v2            = ExistsDir (Join-Path $Root 'eval\results\v2')
  models             = ExistsDir (Join-Path $Root 'models')
  validation_nonUS   = ExistsDir (Join-Path $Root 'validation_nonUS')
  ensemble           = ExistsDir (Join-Path $Root 'ensemble')
  reports            = ExistsDir (Join-Path $Root 'reports')
  bias_logs          = ExistsDir (Join-Path $Root 'bias_logs')
}

# --- B) required configs present ---
$cfgList = @(
  'configs\experiment.yml',
  'configs\scoring.yml',
  'configs\indicators.yml',
  'configs\baselines.yml',
  'configs\indicator_transform_spec.yml',
  'configs\TEMPLATE_data_sheet.md',
  'configs\TEMPLATE_model_card.md',
  'configs\TEMPLATE_bias_log.md',
  'configs\TEMPLATE_scorecard.csv',
  'configs\TEMPLATE_run_manifest.json'
)
$configs = @()
foreach($rel in $cfgList){
  $p = Join-Path $Root $rel
  $configs += [ordered]@{ file=$rel; present=(ExistsFile $p) }
}

# --- C) indicators count (accepts "- id:" OR "- name:")
$indYml  = Join-Path $Root 'configs\indicators.yml'
$indYaml = Join-Path $Root 'configs\indicators.yaml'
$indPath = (Test-Path $indYml) ? $indYml : $indYaml
$indCount_id   = CountMatches $indPath '^\s*-\s*id\s*:'
$indCount_name = CountMatches $indPath '^\s*-\s*name\s*:'
$indCount = [math]::Max($indCount_id, $indCount_name)

$indicators = [ordered]@{
  path         = (Split-Path -Leaf $indPath)
  count_total  = $indCount
  counted_by   = $(if($indCount_id -gt $indCount_name){'id'} else {'name'})
  ok_ge_10     = ($indCount -ge 10)
}

# --- D) models (presence of code dirs) ---
$modelsWanted = @(
  'models\HSM_chatgpt\code',
  'models\FSM_chatgpt\code',
  'models\HSM_grok\code',
  'models\FSM_grok\code'
)
$models = @()
foreach($rel in $modelsWanted){
  $p = Join-Path $Root $rel
  $models += [ordered]@{ path=$rel; present=(ExistsDir $p) }
}

# --- E) diagnostics coverage file non-empty ---
$diagYears = 1985,1990,2000,2015,2020
$diagnostics = @()
foreach($y in $diagYears){
  $p = Join-Path $Root ("eval\results\diagnostics\FINAL_{0}\coverage_points_calibrated.csv" -f $y)
  $nonempty = (Test-Path $p) -and (
    ((Get-Item $p).Length -gt 0) -or
    (((Get-Content $p -ea SilentlyContinue) | Measure-Object -Line).Lines -gt 0)
  )
  $diagnostics += [ordered]@{ year=$y; path=$p.Replace($Root+'\',''); nonempty=$nonempty }
}

# --- F) scored artifacts for each FINAL_* under eval/results/v2 ---
$expectedHeader = 'indicator,horizon,covered_50_rate,covered_90_rate,loss50_abs_error,loss90_abs_error'
$finalDirs = Get-ChildItem -Directory -ea SilentlyContinue (Join-Path $Root 'eval\results\v2') | Where-Object { $_.Name -like 'FINAL_*' }
$scored = @()
foreach($dir in $finalDirs){
  if ($dir.Name -match 'FINAL_(\d{4})'){ $yr=[int]$Matches[1] } else { $yr=$null }
  $base = $dir.FullName
  $p_metrics = Join-Path $base 'metrics_by_horizon.csv'
  $p_loss    = Join-Path $base 'loss_differences.csv'
  $p_cov     = Join-Path $base 'coverage_overall.csv'
  $p_crps    = Join-Path $base 'crps_brier_summary.csv'
  $p_fdr     = Join-Path $base 'significance\fdr_adjusted_results.csv'

  $lossHeaderOk = $false
  if (Test-Path $p_loss){
    try { $first = Get-Content $p_loss -First 1; $lossHeaderOk = ($first -eq $expectedHeader) } catch {}
  }

  $scored += [ordered]@{
    year=$yr
    metrics_by_horizon = ExistsFile $p_metrics
    loss_differences   = ExistsFile $p_loss
    loss_header_ok     = $lossHeaderOk
    coverage_overall   = ExistsFile $p_cov
    crps_brier_summary = ExistsFile $p_crps
    significance_fdr   = ExistsFile $p_fdr
  }
}

# --- G) data governance docs ---
$gov = [ordered]@{
  vintages_md  = ExistsFile (Join-Path $Root 'data\vintages.md')
  revisions_md = ExistsFile (Join-Path $Root 'data\revisions.md')
}

# --- H) processed datasets present (quick glance) ---
$processed = @()
$procDir = Join-Path $Root 'data\processed'
if (ExistsDir $procDir) {
  $processed = Get-ChildItem $procDir -File -ea SilentlyContinue |
    Select-Object @{n='file';e={$_.Name}}, @{n='kb';e={[int]([math]::Round($_.Length/1kb,0))}}
}

# --- assemble & print ---
$report = [ordered]@{
  generated_at = $now
  root         = $Root
  structure    = $structure
  configs      = $configs
  indicators   = $indicators
  models       = $models
  diagnostics  = $diagnostics
  scored       = $scored | Sort-Object year
  governance   = $gov
  processed    = $processed
}

# Console summary (human friendly)
Write-Host "`n=== QUICK INVENTORY @ $($now.ToString('u')) ===" -ForegroundColor Cyan
"{0,-24} {1}" -f "Repo root:", $Root
"{0,-24} {1}" -f "Indicators (>=10?):", ("$($indicators.count_total)  -> " + ($(if($indicators.ok_ge_10){"OK"}else{"NEEDS WORK"})))
"{0,-24} {1}" -f "Vintages.md:", ($(if($gov.vintages_md){"OK"}else{"missing"}))
"{0,-24} {1}" -f "Revisions.md:", ($(if($gov.revisions_md){"OK"}else{"missing"}))

Write-Host "`n-- Structure --"
$structure.GetEnumerator() | Sort-Object Name | ForEach-Object {
  "{0,-24} {1}" -f ($_.Name+':'), ($(if($_.Value){"OK"}else{"missing"}))
}

Write-Host "`n-- Configs --"
$configs | ForEach-Object { "{0,-50} {1}" -f ($_.file+':'), ($(if($_.present){"OK"}else{"missing"})) }

Write-Host "`n-- Models (code dirs) --"
$models | ForEach-Object { "{0,-35} {1}" -f ($_.path+':'), ($(if($_.present){"OK"}else{"missing"})) }

Write-Host "`n-- Diagnostics coverage (non-empty) --"
$diagnostics | Sort-Object year | ForEach-Object {
  "{0}  {1}" -f ($_.year), ($(if($_.nonempty){"OK"}else{"missing/empty"}))
}

Write-Host "`n-- Scored artifacts by FINAL_* --"
$scored | Sort-Object year | Format-Table -AutoSize

if ($processed.Count -gt 0) {
  Write-Host "`n-- data/processed (size KB) --"
  $processed | Sort-Object file | Format-Table -AutoSize
}

# --- write snapshots ---
$jsonOut = Join-Path $Root ("quick_inventory_report_{0}.json" -f $stamp)
$csvOut  = Join-Path $Root ("quick_inventory_summary_{0}.csv" -f $stamp)

# JSON
$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $jsonOut

# CSV (one line per check)
$csvRows = @()
$csvRows += [pscustomobject]@{ group='indicators'; key='count'; value=$indicators.count_total; ok=$indicators.ok_ge_10 }
foreach($k in $structure.Keys){ $csvRows += [pscustomobject]@{ group='structure'; key=$k; value=$structure[$k]; ok=$structure[$k] } }
foreach($c in $configs){ $csvRows += [pscustomobject]@{ group='configs'; key=$c.file; value=$c.present; ok=$c.present } }
foreach($m in $models){ $csvRows += [pscustomobject]@{ group='models'; key=$m.path; value=$m.present; ok=$m.present } }
foreach($d in $diagnostics){ $csvRows += [pscustomobject]@{ group='diagnostics'; key=$d.year; value=$d.nonempty; ok=$d.nonempty } }
foreach($s in $scored){
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):metrics"; value=$s.metrics_by_horizon; ok=$s.metrics_by_horizon }
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):lossdiff"; value=$s.loss_differences;   ok=$s.loss_differences }
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):loss_header"; value=$s.loss_header_ok; ok=$s.loss_header_ok }
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):coverage_overall"; value=$s.coverage_overall; ok=$s.coverage_overall }
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):crps_brier"; value=$s.crps_brier_summary; ok=$s.crps_brier_summary }
  $csvRows += [pscustomobject]@{ group='scored'; key="FINAL_$($s.year):significance_fdr"; value=$s.significance_fdr; ok=$s.significance_fdr }
}
$csvRows | Export-Csv -NoTypeInformation -Encoding UTF8 $csvOut

Write-Host "`nSaved:"
Write-Host "  $jsonOut"
Write-Host "  $csvOut"
