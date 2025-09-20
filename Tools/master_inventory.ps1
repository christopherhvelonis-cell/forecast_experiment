<#
  master_inventory.ps1  —  Full repo-wide inventory check (PowerShell 5-safe)
#>

param(
  [Parameter(Mandatory = $true)] [string]$Root
)

# --- helpers ---
function ExistsFile($path) { Test-Path $path -PathType Leaf }
function ExistsDir($path)  { Test-Path $path -PathType Container }
function NonEmptyFile($path) {
  if (Test-Path $path -PathType Leaf) {
    $lines = Get-Content $path -ErrorAction SilentlyContinue | Measure-Object -Line
    return ($lines.Lines -gt 0)
  }
  return $false
}
function Itm($id,$group,$description,$ok,$detail="") {
  [PSCustomObject]@{ id=$id; group=$group; description=$description; ok=$ok; detail=$detail }
}
function CheckContains($path,$pattern){
  if (-not (Test-Path $path)) { return $false }
  return Select-String -Path $path -Pattern $pattern -Quiet -ErrorAction SilentlyContinue
}

$items = New-Object System.Collections.Generic.List[object]

# =================================================================
# A) Structure
# =================================================================
$items.Add((Itm "dir.configs"  "structure" "configs/ exists" (ExistsDir (Join-Path $Root 'configs'))))
$items.Add((Itm "dir.data"     "structure" "data/{raw,processed,docsheets} exist" (
  (ExistsDir (Join-Path $Root 'data\raw')) -and
  (ExistsDir (Join-Path $Root 'data\processed')) -and
  (ExistsDir (Join-Path $Root 'data\docsheets'))
)))
$items.Add((Itm "dir.eval"     "structure" "eval/results/{diagnostics,v2} exist" (
  (ExistsDir (Join-Path $Root 'eval\results\diagnostics')) -and
  (ExistsDir (Join-Path $Root 'eval\results\v2'))
)))
$items.Add((Itm "dir.models"   "structure" "models/HSM_*/, FSM_*/ exist" (
  (ExistsDir (Join-Path $Root 'models\HSM_chatgpt\code')) -and
  (ExistsDir (Join-Path $Root 'models\FSM_chatgpt\code')) -and
  (ExistsDir (Join-Path $Root 'models\HSM_grok\code'))    -and
  (ExistsDir (Join-Path $Root 'models\FSM_grok\code'))
)))
$items.Add((Itm "dir.misc"     "structure" "bias_logs/, ensemble/, validation_nonUS/, reports/ exist" (
  (ExistsDir (Join-Path $Root 'bias_logs')) -and
  (ExistsDir (Join-Path $Root 'ensemble')) -and
  (ExistsDir (Join-Path $Root 'validation_nonUS')) -and
  (ExistsDir (Join-Path $Root 'reports'))
)))

# =================================================================
# B) Configs & templates (presence)
# =================================================================
# indicators path fallback without ternary
$indicatorsPath = 'configs\indicators.yml'
if (-not (Test-Path (Join-Path $Root $indicatorsPath))) {
  $indicatorsPath = 'configs\indicators.yaml'
}

$cfgs = @(
  'configs\experiment.yml',
  'configs\scoring.yml',
  $indicatorsPath,
  'configs\baselines.yml',
  'configs\indicator_transform_spec.yml'
)
foreach ($c in $cfgs) {
  $items.Add((Itm ("cfg." + ($c -replace '[\\/]','_')) "configs" "$c present" (ExistsFile (Join-Path $Root $c))))
}

$templates = @(
  'TEMPLATE_data_sheet.md',
  'TEMPLATE_model_card.md',
  'TEMPLATE_bias_log.md',
  'TEMPLATE_scorecard.csv',
  'TEMPLATE_run_manifest.json'
)
foreach ($t in $templates) {
  $items.Add((Itm ("tpl."+$t) "templates" "$t present" (ExistsFile (Join-Path $Root $t))))
}

# =================================================================
# C) Key config contents (sanity, tied to your upgrade plan)
# =================================================================
$items.Add((Itm "content.experiment.ecc"      "configs" "experiment.yml mentions ecc_enabled" (CheckContains (Join-Path $Root 'configs\experiment.yml') 'ecc_enabled')))
$items.Add((Itm "content.experiment.stacking" "configs" "experiment.yml mentions stacking/fforma" (CheckContains (Join-Path $Root 'configs\experiment.yml') 'fforma|stacking')))
$items.Add((Itm "content.scoring.calib"       "configs" "scoring.yml has calibration_targets" (CheckContains (Join-Path $Root 'configs\scoring.yml') 'calibration_targets')))
$items.Add((Itm "content.scoring.mv"          "configs" "scoring.yml has multivariate_postproc (ECC/Schaake)" (CheckContains (Join-Path $Root 'configs\scoring.yml') 'multivariate_postproc|ECC|Schaake')))
$items.Add((Itm "content.scoring.conformal"   "configs" "scoring.yml mentions conformal (CQR/EnbPI) or split-conformal" (CheckContains (Join-Path $Root 'configs\scoring.yml') 'conformal|CQR|EnbPI|split-conformal')))
$items.Add((Itm "content.acceptance"          "configs" "experiment.yml has acceptance gate rules" (CheckContains (Join-Path $Root 'configs\experiment.yml') 'acceptance_gate|coverage_abs_error_pp_max|median_skill_vs_equal_weight')))
$items.Add((Itm "content.tests"               "configs" "experiment.yml lists DM/Clark–McCracken/Giacomini–White" (CheckContains (Join-Path $Root 'configs\experiment.yml') 'DM|Clark|Giacomini')))
$items.Add((Itm "content.penalty"             "configs" "experiment.yml has lambda_penalty_grid" (CheckContains (Join-Path $Root 'configs\experiment.yml') 'lambda_penalty_grid')))

# =================================================================
# D) Data governance
# =================================================================
$items.Add((Itm "data.vintages"  "data" "data/vintages.md exists"  (ExistsFile (Join-Path $Root 'data\vintages.md'))))
$items.Add((Itm "data.revisions" "data" "data/revisions.md exists" (ExistsFile (Join-Path $Root 'data\revisions.md'))))

# =================================================================
# E) Evaluation results by origin (presence only; content verified elsewhere)
# =================================================================
$years = 1985,1990,1995,2000,2005,2010,2015,2020
foreach ($y in $years) {
  $base = Join-Path $Root ("eval\results\v2\FINAL_{0}" -f $y)
  $items.Add((Itm ("score.{0}.metrics" -f $y)      "scored" ("FINAL_{0}: metrics_by_horizon.csv present" -f $y) (ExistsFile (Join-Path $base 'metrics_by_horizon.csv'))))
  $items.Add((Itm ("score.{0}.covoverall" -f $y)   "scored" ("FINAL_{0}: coverage_overall.csv present"    -f $y) (ExistsFile (Join-Path $base 'coverage_overall.csv'))))
  $items.Add((Itm ("score.{0}.crpsbrier" -f $y)    "scored" ("FINAL_{0}: crps_brier_summary.csv present" -f $y) (ExistsFile (Join-Path $base 'crps_brier_summary.csv'))))
  $items.Add((Itm ("score.{0}.significance" -f $y) "scored" ("FINAL_{0}: significance/ (FDR) present"    -f $y) (ExistsDir  (Join-Path $base 'significance'))))
}

# =================================================================
# F) Diagnostics (non-empty coverage points)
# =================================================================
foreach ($y in $years) {
  $diag = Join-Path $Root ("eval\results\diagnostics\FINAL_{0}\coverage_points_calibrated.csv" -f $y)
  $items.Add((Itm ("diag.{0}" -f $y) "diagnostics" ("FINAL_{0}: coverage_points_calibrated.csv non-empty" -f $y) (NonEmptyFile $diag)))
}

# =================================================================
# G) Headers sanity for loss_differences.csv where present (optional, fast)
# =================================================================
$expectedLossHeader = 'indicator,horizon,covered_50_rate,covered_90_rate,loss50_abs_error,loss90_abs_error'
foreach ($y in $years) {
  $p = Join-Path $Root ("eval\results\v2\FINAL_{0}\loss_differences.csv" -f $y)
  $ok = $false
  if (Test-Path $p) {
    $first = (Get-Content $p -First 1 -ErrorAction SilentlyContinue)
    $ok = ($first -eq $expectedLossHeader)
  }
  $items.Add((Itm ("losshdr.{0}" -f $y) "scored" ("FINAL_{0}: loss_differences.csv header OK" -f $y) $ok))
}

# =================================================================
# Output
# =================================================================
$all  = $items.Count
$pass = ($items | Where-Object { $_.ok }).Count

Write-Host ""
Write-Host "Master Inventory Summary for $Root"
Write-Host "$pass checks passed / $all total"
Write-Host ""

$items | Where-Object { -not $_.ok } | Sort-Object group,id | Format-Table -AutoSize

# Save artifacts
$items | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $Root 'master_inventory_report.json')
$items | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $Root 'master_inventory_checklist.csv')

Write-Host ""
Write-Host "Wrote:"
Write-Host "  $(Join-Path $Root 'master_inventory_report.json')"
Write-Host "  $(Join-Path $Root 'master_inventory_checklist.csv')"
