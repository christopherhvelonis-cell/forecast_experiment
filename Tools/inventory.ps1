param(
  [string]$Root = (Resolve-Path ".").Path
)

# ---------- helpers ----------
function Itm($id, $group, $desc, $pass, $detail="") {
  [pscustomobject]@{
    id = $id; group = $group; description = $desc; pass = [bool]$pass; detail = $detail
  }
}

function ExistsFile($path){ Test-Path $path -PathType Leaf }
function ExistsDir($path){ Test-Path $path -PathType Container }
function NonEmptyFile($path){ (Test-Path $path) -and ((Get-Item $path).Length -gt 0) -or `
  ((Test-Path $path) -and ((Get-Content $path -ErrorAction SilentlyContinue | Measure-Object -Line).Lines -gt 0)) }

function CountMatches($path, $pattern){
  if (!(Test-Path $path)) { return 0 }
  (Get-Content $path -ErrorAction SilentlyContinue | Select-String -Pattern $pattern -AllMatches).Count
}

function LossDiffHeaderOk($csvPath){
  if (!(Test-Path $csvPath)) { return $false, "missing" }
  try {
    $first = (Get-Content $csvPath -TotalCount 1)
    # Normalize commas/spaces/quotes just-in-case
    $cols = ($first -replace '"','').Split(',') | ForEach-Object { $_.Trim() }
    $desired = @('indicator','horizon','covered_50_rate','covered_90_rate','loss50_abs_error','loss90_abs_error')
    $ok = ($cols -join ',') -eq ($desired -join ',')
    return $ok, ($cols -join ',')
  } catch {
    return $false, "read_error: $($_.Exception.Message)"
  }
}

# ---------- start ----------
$items = New-Object System.Collections.Generic.List[object]

# A) repo structure
$items.Add((Itm "dir.configs" "structure" "configs/ exists" (ExistsDir (Join-Path $Root 'configs'))))
$items.Add((Itm "dir.data" "structure" "data/{raw,processed,docsheets} exist" `
  ((ExistsDir (Join-Path $Root 'data\raw')) -and (ExistsDir (Join-Path $Root 'data\processed')) -and (ExistsDir (Join-Path $Root 'data\docsheets')) )))
$items.Add((Itm "dir.eval" "structure" "eval/results/{diagnostics,v2} exist" `
  ((ExistsDir (Join-Path $Root 'eval\results\diagnostics')) -and (ExistsDir (Join-Path $Root 'eval\results\v2')) )))
$items.Add((Itm "dir.models" "structure" "models/HSM_*/, FSM_*/ exist" `
  ((ExistsDir (Join-Path $Root 'models\HSM_chatgpt\code')) -and (ExistsDir (Join-Path $Root 'models\FSM_chatgpt\code')) -and `
   (ExistsDir (Join-Path $Root 'models\HSM_grok\code')) -and (ExistsDir (Join-Path $Root 'models\FSM_grok\code')) )))
$items.Add((Itm "dir.misc" "structure" "bias_logs/, ensemble/, validation_nonUS/, reports/ exist" `
  ((ExistsDir (Join-Path $Root 'bias_logs')) -and (ExistsDir (Join-Path $Root 'ensemble')) -and (ExistsDir (Join-Path $Root 'validation_nonUS')) -and (ExistsDir (Join-Path $Root 'reports')) )))

# B) required configs & templates
$cfgFiles = @(
  'configs\experiment.yml','configs\scoring.yml','configs\indicators.yml','configs\baselines.yml',
  'configs\indicator_transform_spec.yml',
  'configs\TEMPLATE_data_sheet.md','configs\TEMPLATE_model_card.md','configs\TEMPLATE_bias_log.md',
  'configs\TEMPLATE_scorecard.csv','configs\TEMPLATE_run_manifest.json'
)
foreach($f in $cfgFiles){
  $items.Add((Itm ("cfg."+($f -replace '[\\/]','_')) "configs" "$f present" (ExistsFile (Join-Path $Root $f))))
}

# C) vintages & revisions docs
$items.Add((Itm "doc.vintages" "data" "data/vintages.md exists" (ExistsFile (Join-Path $Root 'data\vintages.md'))))
$items.Add((Itm "doc.revisions" "data" "data/revisions.md exists" (ExistsFile (Join-Path $Root 'data\revisions.md'))))

# D) indicators defined (rough check: count '- id:' lines)
$indPath = Join-Path $Root 'configs\indicators.yml'
$indCount = CountMatches $indPath '^\s*-\s*id\s*:'
$items.Add((Itm "cfg.indicators.count" "configs" "≥10 indicators defined" ($indCount -ge 10) "count=$indCount"))

# E) tools presence (core)
$toolCore = @(
  'Tools\sweep_and_route_coverage_by_year.py',
  'Tools\evaluator_code_v2_min.py',
  'Tools\backfill_evaluator_artifacts.py',
  'Tools\evaluator_significance_min.py',
  'Tools\check_outputs.ps1'
)
foreach($t in $toolCore){
  $items.Add((Itm ("tool."+($t -replace '[\\/]','_')) "tools" "$t present" (ExistsFile (Join-Path $Root $t))))
}

# F) optional upgrade tools (ECC/stacking/EBMA/conformal/Murphy)
$toolOpt = @(
  'Tools\ecc_schaake.py',
  'Tools\meta_stacking_fforma.py',
  'Tools\ebma_psisloo.py',
  'Tools\conformal_calibration.py',
  'Tools\murphy_append.py',
  'Tools\evaluator_code_v3.py'
)
foreach($t in $toolOpt){
  $items.Add((Itm ("toolopt."+($t -replace '[\\/]','_')) "tools+upgrades" "$t present" (ExistsFile (Join-Path $Root $t))))
}

# G) processed data signals
$items.Add((Itm "data.processed.any" "data" "Any data/processed/*.csv exist" `
  ((Get-ChildItem -Path (Join-Path $Root 'data\processed') -Filter *.csv -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)))

# H) diagnostics by origin (coverage exists & non-empty)
$years = @(1985,1990,1995,2000,2005,2010,2015,2020)
foreach($y in $years){
  $diag = Join-Path $Root ("eval\results\diagnostics\FINAL_{0}" -f $y)
  $cov  = Join-Path $diag 'coverage_points_calibrated.csv'
  $has  = (Test-Path $cov) -and ((Get-Content $cov | Measure-Object -Line).Lines -gt 1)
  $items.Add((Itm ("diag."+$y) "diagnostics" ("FINAL_{0}: coverage_points_calibrated.csv non-empty" -f $y) $has))
}

# I) scored outputs per origin + loss_differences header check
foreach($y in $years){
  $outDir = Join-Path $Root ("eval\results\v2\FINAL_{0}" -f $y)
  $metrics = Join-Path $outDir 'metrics_by_horizon.csv'
  $lossdif = Join-Path $outDir 'loss_differences.csv'
  $covsum  = Join-Path $outDir 'coverage_overall.csv'
  $crpsbr  = Join-Path $outDir 'crps_brier_summary.csv'

  $items.Add((Itm ("score."+$y+".metrics") "scored" ("FINAL_{0}: metrics_by_horizon.csv present" -f $y) (ExistsFile $metrics)))
  $ok,$hdr = LossDiffHeaderOk $lossdif
  $items.Add((Itm ("score."+$y+".lossdiff") "scored" ("FINAL_{0}: loss_differences.csv header OK" -f $y) $ok $hdr))
  $items.Add((Itm ("score."+$y+".covoverall") "scored" ("FINAL_{0}: coverage_overall.csv present" -f $y) (ExistsFile $covsum)))
  $items.Add((Itm ("score."+$y+".crpsbrier") "scored" ("FINAL_{0}: crps_brier_summary.csv present" -f $y) (ExistsFile $crpsbr)))

  # significance
  $sig = Join-Path $outDir 'significance\fdr_adjusted_results.csv'
  $items.Add((Itm ("score."+$y+".significance") "scored" ("FINAL_{0}: significance/FDR results present" -f $y) (ExistsFile $sig)))
}

# J) ensemble + validation + bias logs + reports
$items.Add((Itm "ensemble.readme" "ensemble" "ensemble/README.md present" (ExistsFile (Join-Path $Root 'ensemble\README.md'))))
$items.Add((Itm "validation.specs" "validation" "validation_nonUS/plan.md & specs.json present" `
  ((ExistsFile (Join-Path $Root 'validation_nonUS\plan.md')) -and (ExistsFile (Join-Path $Root 'validation_nonUS\specs.json')))))
# bias logs: at least one md
$biasAny = (Get-ChildItem -Path (Join-Path $Root 'bias_logs') -Filter *.md -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
$items.Add((Itm "bias.any" "bias" "At least one bias_logs/*.md present" $biasAny))
$items.Add((Itm "reports.final" "reports" "reports/final_report.md present" (ExistsFile (Join-Path $Root 'reports\final_report.md'))))
$items.Add((Itm "reports.release" "reports" "reports/release_manifest.md present" (ExistsFile (Join-Path $Root 'reports\release_manifest.md'))))

# K) quick acceptance-gate proxies
# coverage error bound is a metric-level thing; we only check presence of artifacts here.
$gateArtifacts = @(
  ExistsFile (Join-Path $Root 'eval\results\v2\FINAL_1995\metrics_by_horizon.csv'),
  ExistsFile (Join-Path $Root 'eval\results\v2\FINAL_2000\metrics_by_horizon.csv'),
  ExistsFile (Join-Path $Root 'eval\results\v2\FINAL_2005\metrics_by_horizon.csv'),
  ExistsFile (Join-Path $Root 'eval\results\v2\FINAL_2010\metrics_by_horizon.csv')
) -contains $true
$items.Add((Itm "gate.artifacts" "governance" "Scored metrics exist for at least one origin" $gateArtifacts))

# ---------- reporting ----------
# 1) Console summary
$fail = $items | Where-Object { -not $_.pass }
$pass = $items | Where-Object { $_.pass }

Write-Host ""
Write-Host "Inventory Summary for $Root" -ForegroundColor Cyan
"{0} checks passed / {1} total" -f ($pass.Count), ($items.Count) | Write-Host
if ($fail.Count -gt 0) {
  Write-Host "`nMissing/Failing:" -ForegroundColor Yellow
  $fail | Select-Object group, id, description, detail | Format-Table -AutoSize | Out-String | Write-Host
}

# 2) Machine-readable
$reportJson = Join-Path $Root 'inventory_report.json'
$items | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $reportJson
$reportCsv  = Join-Path $Root 'inventory_checklist.csv'
$items | Export-Csv -NoTypeInformation -Encoding UTF8 $reportCsv

Write-Host "`nWrote:" -ForegroundColor Green
Write-Host "  $reportJson"
Write-Host "  $reportCsv"
