$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\pass4.log"
if (Test-Path $log) { Remove-Item $log -Force }
$body = @'
$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\snapshots\QuadPreRecorder-before-pass4.kicad_pcb -Force
Write-Host "=== stitch pass 4 ==="
& $py tools\stitch_pass4.py
Write-Host "=== connectivity ==="
& $py tools\gnd_cluster_check.py
Write-Host "=== DRC ==="
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
Write-Host "=== PASS4 DONE ==="
'@
$script = "C:\Users\Jason\Documents\quadpreandrecorder\tools\_pass4_body.ps1"
Set-Content -Path $script -Value $body -Encoding UTF8
$a = '-NoProfile -ExecutionPolicy Bypass -File "' + $script + '"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("pass4 launched: " + $log)
