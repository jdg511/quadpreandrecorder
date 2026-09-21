$py = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
& $py tools\patch_c3_micbias.py 2>&1 | Out-File -Encoding utf8 review_outputs\micbias.log
Get-Content review_outputs\micbias.log | Select-String -NotMatch "memory leak"
