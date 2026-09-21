$cli = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\kicad-cli.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\review_outputs\peek-drc.rpt hardware\QuadPreRecorder.kicad_pcb | Select-String "Found"
Get-Content hardware\review_outputs\peek-drc.rpt | Select-String -Context 0,3 "unconnected_items\]" | Select-Object -First 12
