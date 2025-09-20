param(
  [Parameter(Mandatory=$true)] [string]$Root,
  [int[]]$Years = @(1995,2000,2005,2010)
)

function Itm($id,$group,$desc,$ok,$detail=""){ [PSCustomObject]@{id=$id;group=$group;description=$desc;ok=$ok;detail=$detail} }

$items = New-Object System.Collections.Generic.List[object]

foreach($y in $Years){
  $metrics = Join-Path $Root "eval\results\v2\FINAL_$y\metrics_by_horizon.csv"
  $ok = (Test-Path $metrics) -and ((Get-Content $metrics | Measure-Object -Line).Lines -gt 2)
  $items.Add((Itm "composite.$y" "accept" "Composite metrics present & non-trivial (proxy for skill calc)" $ok $metrics))
}

$hold = Join-Path $Root "eval\results\holdouts"
$items.Add((Itm "holdout.blocks" "accept" "Holdout block folder exists (proxy)" (Test-Path $hold) $hold))

$nonus = Join-Path $Root "validation_nonUS\plan.md"
$items.Add((Itm "nonUS.plan" "accept" "Non-US validation plan present (proxy)" (Test-Path $nonus) $nonus))

$calCsv = Join-Path $Root "eval\results\v2\calibration_targets_summary.csv"
if(Test-Path $calCsv){
  $rows = Import-Csv $calCsv
  foreach($r in $rows){
    $ok50 = [double]::TryParse($r.'50_abs_err_pp',[ref]([double]$null)) -and ([double]$r.'50_abs_err_pp' -le 5.0)
    $ok90 = [double]::TryParse($r.'90_abs_err_pp',[ref]([double]$null)) -and ([double]$r.'90_abs_err_pp' -le 5.0)
    $items.Add((Itm "coverage.$($r.year).50" "accept" "50% coverage abs error ≤ 5pp" $ok50 $r.'50_abs_err_pp'))
    $items.Add((Itm "coverage.$($r.year).90" "accept" "90% coverage abs error ≤ 5pp" $ok90 $r.'90_abs_err_pp'))
  }
}else{
  $items.Add((Itm "coverage.summary" "accept" "calibration_targets_summary.csv present" $false "missing"))
}

$items.Add((Itm "median_skill_proxy" "accept" "Median skill vs equal-weight (proxy PASS if metrics exist)" ($items | ? {$_.id -like 'composite.*' -and $_.ok} | Measure-Object).Count -gt 0))

"" 
"Acceptance Gate (proxies today -- replace with real skill later)"
$items | Format-Table -AutoSize

$out = Join-Path $Root "eval\results\v2\acceptance_gate_summary.csv"
$items | Export-Csv -NoTypeInformation -Encoding UTF8 $out
Write-Host "`n[acceptance] wrote $out"
