$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
& $py -u tools\astar_route.py hardware\fabrication\drc-teensyfix5.json 2>&1 | Select-String -NotMatch "memory leak" | Out-File -Encoding utf8 -Append review_outputs\astar-teensy3.log
& $py tools\refill_zones.py 2>&1 | Select-String -NotMatch "memory leak" | Out-File -Encoding utf8 -Append review_outputs\astar-teensy3.log
& $cli pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-teensyfix6.json hardware\QuadPreRecorder.kicad_pcb 2>&1 | Out-File -Encoding utf8 -Append review_outputs\astar-teensy3.log
"ASTAR3 DONE" | Out-File -Encoding utf8 -Append review_outputs\astar-teensy3.log
