$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\final_fixes2.log"
"=== EP vias U13 (5) + U11 (5), inner layers -> power ===" | Out-File -Encoding utf8 $out
& $py tools\add_ep_vias.py GND 129.5,16.5 129.0,16.0 130.0,16.0 129.0,17.0 130.0,17.0 8.5,29.55 9.5,29.55 10.5,29.55 8.5,33.45 9.9,33.45 2>&1 | Out-File -Encoding utf8 -Append $out
(Select-String -Path hardware\QuadPreRecorder.kicad_pcb -Pattern '"In[12].Cu" (signal|power)\)' | ForEach-Object { $_.Line.Trim() }) | Out-File -Encoding utf8 -Append $out
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
"=== DRC (all severities) ===" | Out-File -Encoding utf8 -Append $out
$cli = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\kicad-cli.exe"
& $cli pcb drc --all-track-errors --schematic-parity --severity-all -o hardware\review_outputs\final-drc.rpt hardware\QuadPreRecorder.kicad_pcb 2>&1 | Select-String "Found" | Out-File -Encoding utf8 -Append $out
Get-Content hardware\review_outputs\final-drc.rpt | Select-String -Pattern '^\[' | Group-Object { $_.Line.Split(']')[0] } | ForEach-Object { "$($_.Count) x $($_.Name)]" } | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
