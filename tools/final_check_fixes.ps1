$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\final_fixes.log"
Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\QuadPreRecorder.kicad_pcb.revc3mic4-prefinal-20260913 -Force
"=== inner layers typed as power planes ===" | Out-File -Encoding utf8 $out
$b = [System.IO.File]::ReadAllText("hardware\QuadPreRecorder.kicad_pcb")
$b = $b.Replace('(4 "In1.Cu" signal)', '(4 "In1.Cu" power)').Replace('(6 "In2.Cu" signal)', '(6 "In2.Cu" power)')
[System.IO.File]::WriteAllText("hardware\QuadPreRecorder.kicad_pcb", $b)
(Select-String -Path hardware\QuadPreRecorder.kicad_pcb -Pattern '"In[12].Cu" (signal|power)\)' | ForEach-Object { $_.Line.Trim() }) | Out-File -Encoding utf8 -Append $out
"=== +3V3_A: run the C42.1 entry to the pad centre ===" | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py +3V3_A "B:85.625,48.275;85.625,47.4" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== CHASSIS: re-seat the F.Cu link on the exact stub end ===" | Out-File -Encoding utf8 -Append $out
& $py tools\remove_net_items_in_box.py CHASSIS 38.40 103.2 38.6 103.4 2>&1 | Out-File -Encoding utf8 -Append $out
& $py tools\poly_route.py CHASSIS "F:38.4086,103.216;38.543,103.35" 2>&1 | Out-File -Encoding utf8 -Append $out
"=== thermal vias: U13 EP (5) and U11 EP (5) ===" | Out-File -Encoding utf8 -Append $out
foreach ($pt in @("129.5 16.5", "129.0 16.0", "130.0 16.0", "129.0 17.0", "130.0 17.0", "8.5 29.55", "9.5 29.55", "10.5 29.55", "8.5 33.45", "9.9 33.45")) {
  $xy = $pt.Split(" ")
  & $py tools\add_via.py GND $xy[0] $xy[1] 2>&1 | Out-File -Encoding utf8 -Append $out
}
"=== refill zones ===" | Out-File -Encoding utf8 -Append $out
& $py tools\refill_zones.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $out
& $py tools\gnd_cluster_check.py 2>&1 | Select-Object -Last 4 | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py CHASSIS 2>&1 | Select-Object -First 1 | Out-File -Encoding utf8 -Append $out
& $py tools\net_clusters.py +3V3_A 2>&1 | Select-Object -First 1 | Out-File -Encoding utf8 -Append $out
"=== DRC ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
