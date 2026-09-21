$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\fix_c3mic4b.log"
"=== BLD_MICC: lift the C99.1->C103.1 run to y=98.1 (opens a via slot at (41,98.85)) ===" | Out-File -Encoding utf8 $out
& $py tools\remove_net_items_in_box.py BLD_MICC 35.9 98.4 44.1 100.2 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py BLD_MICC "B:36.0,98.875;36.45,98.425;36.775,98.1;41.5,98.1;42.85,99.45;44.0,100.15" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== CHASSIS: C15.2 -> F band -> via (41,98.85) -> B.Cu down to D23.2 ===" | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py CHASSIS "F:38.0,97.325;41.0,97.325;41.0,98.85 V B:41.0,103.35;40.0,103.35" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== BRU_MICC: feeder hops over BRU_RAWC on F.Cu, vias (34.5,102.3) (39.0,105.3) ===" | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py BRU_MICC "B:33.659,101.745;34.5,102.3 V F:39.6,102.3;39.6,104.6;39.0,105.3 V B:39.0,106.052" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
"=== CHASSIS / BRU_MICC / BLD_MICC clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py CHASSIS 2>&1 | Select-Object -First 1 | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py BRU_MICC 2>&1 | Select-Object -First 1 | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py BLD_MICC 2>&1 | Select-Object -First 1 | Out-File -Encoding utf8 -Append $out
"=== DRC ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
