$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
& $py tools\patch_c3_stragglers.py
& $py tools\connect_orphan_net.py BOOST_EN | Select-Object -Last 4
& $py tools\connect_orphan_net.py BOOST_SS | Select-Object -Last 4
& $py tools\cleanup_board.py | Select-Object -Last 2
& $py tools\gnd_cluster_check.py | Select-Object -Last 3
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
Get-Content hardware\fabrication\QuadPreRecorder-drc.rpt | Select-Object -First 30
