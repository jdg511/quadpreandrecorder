$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$py = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\python.exe"
Set-Location $repo
& $py tools\audio_audit2.py 2>&1
