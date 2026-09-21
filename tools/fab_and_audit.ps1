$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
Set-Location $repo
& $py tools\build_manufacturing.py 2>&1 | Select-String -NotMatch "memory leak" | Select-Object -Last 6
& $py tools\audio_audit.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit_c3tp.txt
& $py tools\audio_audit2.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit2_c3tp.txt
& $py tools\audio_audit3.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit3_c3tp.txt
Write-Output "FAB+AUDIT DONE"
