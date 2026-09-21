$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
$cli = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\kicad-cli.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\resch.log"
"=== generate_schematic ===" | Out-File -Encoding utf8 $out
& $py tools\generate_schematic.py 2>&1 | Out-File -Encoding utf8 -Append $out
"=== ERC ===" | Out-File -Encoding utf8 -Append $out
& $cli sch erc --severity-all -o hardware\review_outputs\erc-c3mic.rpt hardware\QuadPreRecorder.kicad_sch 2>&1 | Out-File -Encoding utf8 -Append $out
Get-Content hardware\review_outputs\erc-c3mic.rpt | Select-String "ERC messages|^\[" | Out-File -Encoding utf8 -Append $out
"=== DRC + parity ===" | Out-File -Encoding utf8 -Append $out
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\peek_drc2.ps1 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
