$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
$cli = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\kicad-cli.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\final_fixes3.log"
"=== remove the 4 bad EP vias, the 2 pad-hole stitching vias, the HP_OUT_L sliver ===" | Out-File -Encoding utf8 $out
& $py tools\remove_net_items_in_box.py GND 8.45 33.4 8.55 33.5 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py GND 128.95 15.95 129.05 17.05 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py GND 129.45 16.45 129.55 16.55 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py GND 75.95 70.45 76.05 70.55 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py GND 49.45 75.95 49.55 76.05 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py HP_OUT_L 118.58 56.38 118.62 56.41 2>&1 | Out-File -Encoding utf8 -Append $out
"=== TP1/TP2 excluded from BOM on the board ===" | Out-File -Encoding utf8 -Append $out
& $py tools\tp_bom_attr.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
"=== DRC (all severities) ===" | Out-File -Encoding utf8 -Append $out
& $cli pcb drc --all-track-errors --schematic-parity --severity-all -o hardware\review_outputs\final-drc.rpt hardware\QuadPreRecorder.kicad_pcb 2>&1 | Select-String "Found" | Out-File -Encoding utf8 -Append $out
Get-Content hardware\review_outputs\final-drc.rpt | Select-String -Pattern '^\[' | Group-Object { $_.Line.Split(']')[0] } | ForEach-Object { "$($_.Count) x $($_.Name)]" } | Out-File -Encoding utf8 -Append $out
"=== DRC (errors only, the fab gate) ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
