$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
& $py tools\poly_route.py +5V "F:116.25,53.64;117.0,53.64 V B:117.0,56.9;117.69,57.22"
if ($LASTEXITCODE -ne 0) { exit 1 }
& $py tools\cleanup_board.py | Select-Object -Last 1
& $py tools\gnd_cluster_check.py | Select-Object -Last 3
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
