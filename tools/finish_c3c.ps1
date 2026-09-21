$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
& $py tools\set_stackup.py
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
& $py tools\audio_audit.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit_c3.txt
& $py tools\audio_audit2.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit2_c3.txt
& $py tools\audio_audit3.py 2>&1 | Out-File -Encoding utf8 review_outputs\audio_audit3_c3.txt
Write-Host "audits done"
