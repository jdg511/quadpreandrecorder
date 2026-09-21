$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
Set-Location $repo
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\prep_revc2.ps1 2>&1 | Select-String -NotMatch "memory leak"
& $py tools\preflight_pads.py 2>&1 | Select-Object -Last 1
& $py tools\fanout_decouple.py 2>&1 | Select-String -NotMatch "memory leak"
& $py tools\fanout_gnd.py --allow-existing 2>&1 | Select-Object -Last 3
