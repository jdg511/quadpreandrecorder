$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$log = "review_outputs\astar-teensy5.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
Run "& '$py' tools\restore_analog_under_teensy.py"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t7.json hardware\QuadPreRecorder.kicad_pcb"
Run "& '$py' -u tools\astar_route.py hardware\fabrication\drc-t7.json --only BRU_PRE"
Run "& '$py' -u tools\astar_route.py hardware\fabrication\drc-t7.json --only BRU_CFB"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t8.json hardware\QuadPreRecorder.kicad_pcb"
Run "& '$py' -u tools\astar_route.py hardware\fabrication\drc-t8.json"
Run "& '$py' tools\refill_zones.py"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t9.json hardware\QuadPreRecorder.kicad_pcb"
"ASTAR5 DONE" | Out-File -Encoding utf8 -Append $log
