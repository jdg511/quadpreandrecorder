$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$netlist = Join-Path $repo "hardware\review_outputs\QuadPreRecorder.net"
Set-Location $repo
& $py tools\generate_footprints.py 2>&1 | Select-String -NotMatch "memory leak|handler" | Select-Object -Last 2
& $py tools\generate_schematic.py 2>&1 | Select-String -NotMatch "memory leak|handler" | Select-Object -Last 1
& $cli sch export netlist -o $netlist hardware\QuadPreRecorder.kicad_sch 2>&1 | Select-Object -Last 1
& $cli sch erc --severity-error --exit-code-violations -o hardware\fabrication\QuadPreRecorder-erc.rpt hardware\QuadPreRecorder.kicad_sch 2>&1 | Select-String "Found"
Get-Content hardware\QuadPreRecorder.pretty\Teensy41_Socket.kicad_mod | Select-String '\(pad "(3V3B|GND3|23|13|41|33)"' -Context 0,1 | Select-Object -First 12
