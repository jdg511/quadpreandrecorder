$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\fix_c3e.log"
"=== VREF: F.Cu lane east of the ATT/AC verticals, via at the BRU row ===" | Out-File -Encoding utf8 $out
& $py tools\poly_route.py VREF "F:57.067,84.483;57.2,84.616;57.2,102.85;57.25,102.85 V B:57.25,102.85;56.0,102.85" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
"=== DRC ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
