$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
Set-Location $repo
& $py tools\restore_analog_under_teensy.py 2>&1 | Select-String -NotMatch "memory leak"
& $py tools\poly_route.py BRU_PRE "B:74.3178,97.7918;74.3178,64.2;73.1444,63.0266;73.1444,61.5083" 2>&1 | Select-String -NotMatch "memory leak"
& $py tools\poly_route.py BRU_CFB "B:74.6695,86.085;74.72,86.0345;74.72,64.051;73.7961,63.127;73.7961,61.6627" 2>&1 | Select-String -NotMatch "memory leak"
