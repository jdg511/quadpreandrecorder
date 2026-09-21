$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$netlist = Join-Path $repo "hardware\review_outputs\QuadPreRecorder.net"
Set-Location $repo
& $py tools\generate_schematic.py | Select-Object -Last 1
& $cli sch export netlist -o $netlist hardware\QuadPreRecorder.kicad_sch
& $cli sch erc --severity-error --exit-code-violations -o hardware\fabrication\QuadPreRecorder-erc.rpt hardware\QuadPreRecorder.kicad_sch | Select-String "Found"
& $py tools\patch_c3_micbias.py 2>&1 | Select-String -NotMatch "memory leak"
& $py tools\cleanup_board.py | Select-Object -Last 1
& $py tools\gnd_cluster_check.py | Select-Object -Last 3
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
