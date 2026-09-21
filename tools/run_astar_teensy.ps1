$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Set-Location $repo
& $py -u tools\astar_route.py hardware\fabrication\drc-teensyfix2.json 2>&1 | Select-String -NotMatch "memory leak" | Out-File -Encoding utf8 review_outputs\astar-teensy.log
& $py tools\refill_zones.py 2>&1 | Select-String -NotMatch "memory leak" | Out-File -Encoding utf8 -Append review_outputs\astar-teensy.log
& $cli pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-teensyfix3.json hardware\QuadPreRecorder.kicad_pcb 2>&1 | Out-File -Encoding utf8 -Append review_outputs\astar-teensy.log
"ASTAR DONE" | Out-File -Encoding utf8 -Append review_outputs\astar-teensy.log
