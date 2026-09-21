# After the full re-route (2026-09-15 Teensy socket fix): the Rev C3 post passes.
$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$log = "review_outputs\post-teensy-reroute.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\QuadPreRecorder.kicad_pcb.revc3teensy-routed-raw-20260915 -Force
"=== EP thermal vias U13 / U11 + In1/In2 power ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\add_ep_vias.py GND 130,16 130,17 8.5,29.55 9.5,29.55 10.5,29.55 9.9,33.45"
"=== TP1/TP2 out of BOM ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\tp_bom_attr.py"
"=== stitch pass 3 (orphan GND rescue) ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\stitch_pass3.py"
"=== cleanup + refill ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\cleanup_board.py"
Run "& '$py' tools\refill_zones.py"
"=== GND clusters ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\gnd_cluster_check.py"
"=== DRC all severities ===" | Out-File -Encoding utf8 -Append $log
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-all --format json -o hardware\fabrication\drc-post.json hardware\QuadPreRecorder.kicad_pcb"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb"
"POST DONE" | Out-File -Encoding utf8 -Append $log
