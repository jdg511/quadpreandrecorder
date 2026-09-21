$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\fix_c3mic4.log"
Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\QuadPreRecorder.kicad_pcb.revc3mic4-prefix-20260912 -Force
"=== +3V3_A: drop U7.26 fanout via, stub U7.26->U7.25, B.Cu lane at y=48.5 ===" | Out-File -Encoding utf8 $out
& $py tools\remove_net_items_in_box.py GND 84.5 47.9 86.4 48.7 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py GND "F:86.362,48.0;86.362,48.5" 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py +3V3_A "B:82.025,49.3;82.025,48.5;85.35,48.5;85.625,48.275" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== BRU_MICC: move the feeder fence south (y=102.75) ===" | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py BRU_MICC 33.5 101.6 40.7 103.2 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py BRU_MICC 40.4 103.0 40.7 106.1 2>&1 | Out-File -Encoding utf8 -Append $out
"=== CHASSIS: drop island via, new vias (40.7,99.5) (37.5,101.95) (39.0,103.35) ===" | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py CHASSIS 38.3 102.5 38.5 103.4 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py BRU_MICC "B:33.659,101.745;34.664,102.75;40.236,102.75;40.541,103.055" 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py CHASSIS "F:38.0,97.325;40.5,97.325;40.7,97.525;40.7,99.5 V B:40.7,100.6;37.5,100.6;37.5,101.95 V F:37.5,103.125;38.0,103.625" 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py CHASSIS "B:39.3,103.35;39.0,103.35 V F:38.543,103.35;38.409,103.216" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
"=== CHASSIS clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py CHASSIS 2>&1 | Select-Object -First 3 | Out-File -Encoding utf8 -Append $out
"=== DRC ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
