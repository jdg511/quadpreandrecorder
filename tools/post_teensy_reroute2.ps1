$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$log = "review_outputs\post-teensy-reroute2.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
"=== stitching vias drilled into THT GND pad holes ===" | Out-File -Encoding utf8 -Append $log
Run "& '$py' tools\remove_net_items_in_box.py GND 123.45 108.95 123.55 109.05"
Run "& '$py' tools\remove_net_items_in_box.py GND 74.45 26.95 74.55 27.05"
Run "& '$py' tools\remove_net_items_in_box.py GND 74.95 59.95 75.05 60.05"
Run "& '$py' tools\remove_net_items_in_box.py GND 49.95 75.45 50.05 75.55"
Run "& '$py' tools\refill_zones.py"
Run "& '$py' tools\gnd_cluster_check.py"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-all -o hardware\review_outputs\final-drc.rpt hardware\QuadPreRecorder.kicad_pcb"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb"
Get-Content hardware\review_outputs\final-drc.rpt | Select-String -Pattern '^\[' | Group-Object { $_.Line.Split(']')[0] } | ForEach-Object { "$($_.Count) x $($_.Name)]" } | Out-File -Encoding utf8 -Append $log
"POST2 DONE" | Out-File -Encoding utf8 -Append $log
