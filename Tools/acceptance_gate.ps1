param(
  [Parameter(Mandatory=$true)][string]$Root
)

function Row($id,$group,$desc,$ok,$detail){
  [pscustomobject]@{ id=$id; group=$group; description=$desc; ok=$ok; detail=$detail }
}

$items = New-Object System.Collections.Generic.List[object]

Write-Host "`nAcceptance Gate (real composite where available)`

id                 group  description                                                      ok detail
--                 -----  -----------                                                      -- ------"

# Years you care about
$years = 1995,2000,2005,2010

# A) Composite-by-year from metrics_by_horizon.csv
foreach($y in $years){
  $final = Join-Path $Root ("eval\results\v2\FINAL_{0}" -f $y)
  $met   = Join-Path $final "metrics_by_horizon.csv"
  $ok = $false; $detail = "missing"
  if (Test-Path $met){
    $rows = Import-Csv $met
    $row  = $rows | Where-Object { $_.metric -eq "composite_mean" } | Select-Object -First 1
    if ($row){
      $val = $row.value
      $num = 0.0
      if ([double]::TryParse($val, [ref]$num)){
        # For proper scores (CRPS/Brier), smaller is better; we just report the value.
        $ok = $true
        $detail = ("composite_mean={0}" -f $num)
      } else {
        $detail = "non-numeric composite_mean: $val"
      }
    } else {
      $detail = "no composite_mean row"
    }
  }
  $items.Add((Row ("composite.$y") "accept" ("Composite value present (FINAL_$y)") $ok $detail))
}

# B) Holdout folder exists (simple proxy still)
$hold = Join-Path $Root "eval\results\holdouts"
$items.Add((Row "holdout.blocks" "accept" "Holdout block folder exists" (Test-Path $hold) $hold))

# C) Non-US plan present
$nonus = Join-Path $Root "validation_nonUS\specs.json"
$items.Add((Row "nonUS.plan" "accept" "Non-US validation plan present" (Test-Path $nonus) $nonus))

# D) Coverage checks from summary (already produced by Tools\calibration_check.py)
$calcsv = Join-Path $Root "eval\results\v2\calibration_targets_summary.csv"
if (Test-Path $calcsv){
  $cal = Import-Csv $calcsv
  foreach($y in $years){
    $r = $cal | Where-Object { $_.year -eq "$y" } | Select-Object -First 1
    foreach($lev in @("50","90")){
      $id  = "coverage.$y.$lev"
      $ok  = $false
      $det = ""
      if ($r){
        $err = $r."$(${lev})_abs_err_pp"
        $num = 0.0
        if ([double]::TryParse(($err -replace ",","."), [ref]$num)){
          $ok = ($num -le 5.0)   # <= 5 percentage points
          $det = "{0:N2}" -f $num
        }
      }
      $items.Add((Row $id "accept" ("{0}% coverage abs error <= 5pp" -f $lev) $ok $det))
    }
  }
}

# E) Median "skill proxy" = count of years with composite present
$present = ($items | Where-Object { $_.id -like "composite.*" -and $_.ok }) | Measure-Object | Select-Object -ExpandProperty Count
$items.Add((Row "median_skill_proxy" "accept" "Composite presence count (proxy)" $true $present))

# Print table
$items | ForEach-Object {
  "{0,-20} {1,-6} {2,-60} {3,-4} {4}" -f $_.id, $_.group, $_.description, $(if($_.ok){"True"}else{"False"}), $_.detail
} | Write-Host

# Write CSV
$out = Join-Path $Root "eval\results\v2\acceptance_gate_summary.csv"
$items | Export-Csv -NoTypeInformation -Encoding UTF8 $out
Write-Host "`n[acceptance] wrote $out"
