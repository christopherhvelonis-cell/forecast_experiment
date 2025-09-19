param(
  [string]$Root = (Resolve-Path ".").Path
)

$desired = 'indicator','horizon','covered_50_rate','covered_90_rate','loss50_abs_error','loss90_abs_error'

Get-ChildItem -Path (Join-Path $Root 'eval\results\v2') -Filter 'FINAL_*' -Directory |
  Sort-Object Name | ForEach-Object {
    $dir = $_.FullName
    $year = $_.Name -replace '^FINAL_',''
    Write-Host "`n=== $year ($dir) ==="

    $files = 'metrics_by_horizon.csv','loss_differences.csv','coverage_overall.csv','crps_brier_summary.csv'
    foreach ($f in $files) {
      $p = Join-Path $dir $f
      if (Test-Path $p) {
        $lines = (Get-Content $p | Measure-Object -Line).Lines
        "{0,-25} {1,5} lines" -f ($f+':'), $lines
      } else {
        "{0,-25} {1}" -f ($f+':'), 'missing'
      }
    }

    # header check for loss_differences
    $ld = Join-Path $dir 'loss_differences.csv'
    if (Test-Path $ld) {
      $rows = Import-Csv $ld
      if ($rows.Count -gt 0) {
        $present = $rows[0].PSObject.Properties.Name
        $inOrder = ($desired | Where-Object { $present -contains $_ })
        $ok = ($inOrder -join ',') -eq (($present | Where-Object { $desired -contains $_ }) -join ',')
        if ($ok) {
          "loss_differences header OK: yes"
        } else {
          "loss_differences header OK: no -> $($present -join ',')"
        }
      }
    }
  }
