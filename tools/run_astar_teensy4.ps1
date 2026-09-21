$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$log = "review_outputs\astar-teensy6.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
Run "& '$py' tools\clear_pad_net.py U8 3V3B"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t10.json hardware\QuadPreRecorder.kicad_pcb"
Run "& '$py' -u tools\astar_route.py hardware\fabrication\drc-t10.json"
Run "& '$py' tools\refill_zones.py"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t11.json hardware\QuadPreRecorder.kicad_pcb"
"ASTAR6 DONE" | Out-File -Encoding utf8 -Append $log
