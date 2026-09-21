$cli = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\kicad-cli.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
& $cli pcb drc --all-track-errors --severity-error --format json -o hardware\review_outputs\peek-drc.json hardware\review_outputs\peek.kicad_pcb | Out-Null
$j = Get-Content hardware\review_outputs\peek-drc.json -Raw | ConvertFrom-Json
Write-Output ("violations: " + $j.violations.Count + "  unconnected: " + $j.unconnected_items.Count)
$j.violations | Group-Object type | ForEach-Object { Write-Output ("  " + $_.Name + ": " + $_.Count) }
$j.unconnected_items | Select-Object -First 25 | ForEach-Object { Write-Output ("  UNC " + $_.description) }
