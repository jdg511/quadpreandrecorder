$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix.ses"
$log = "review_outputs\finish-teensy-import.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
Run "& '$py' tools\import_ses_into_current.py '$ses'"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t12.json hardware\QuadPreRecorder.kicad_pcb"
"IMPORT DONE" | Out-File -Encoding utf8 -Append $log
