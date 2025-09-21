param(
  [Parameter(Mandatory=$true)] [string]$Root,
  [double]$CompositeMax = 0.60
)

$ErrorActionPreference = "Stop"

function Read-Composite {
  param([string]$FinalDir)
  $met = Join-Path $FinalDir "metrics_by_horizon.csv"
  if (-not (Test-Path $met)) { return $null }
  try {
    $r = Import-Csv $met | Where-Object { $_.metric -eq "composite_mean" -and $_.horizon -eq "1" } | Select-Object -First 1
    if ($r) { 
      $num = 0.0
      if ([double]::TryParse(($r.value -replace ",","."), [ref]$num)) { return $num }
    }
  } catch {}
  return $null
}

$years = 1995,2000,2005,2010
$items = New-Object System.Collections.Generic.List[object]

foreach ($y in $years) {
  $final = Join-Path $Root ("eval\results\v2\FINAL_{0}" -f $y)
  $comp  = if (Test-Path $final) { Read-Composite $final } else { $null }
  $ok    = ($null -ne $comp) -and ($comp -le $CompositeMax)
  $detail = if ($null -eq $comp) { "no composite_mean" } else { "composite_mean={0}" -f $comp }
  $items.Add([pscustomobject]@{
    id = "composite.$y"
    group = "accept"
    description = "Composite ≤ $CompositeMax (FINAL_$y)"
    ok = $ok
    detail = $detail
  })
}

"Acceptance Gate (thresholded composite)"
""
$items | Format-Table -AutoSize

$out = Join-Path $Root "eval\results\v2\acceptance_gate_threshold_summary.csv"
$items | Export-Csv -NoTypeInformation -Encoding UTF8 $out
Write-Host "`n[acceptance-threshold] wrote $out"
