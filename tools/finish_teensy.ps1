$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$jar = Join-Path $repo "tools\cache\freerouting19.jar"
$raw = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix.dsn"
$dsn = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix-plane.dsn"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix.ses"
$log = "review_outputs\finish-teensy.log"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }
Run "& '$py' tools\teensy_ripup_router_routes.py"
Run "& '$py' tools\export_dsn_from_board.py '$raw'"
Run "& '$py' tools\protect_fanout.py '$raw'"
Run "& '$py' tools\patch_dsn_plane.py '$raw' '$dsn'"
"=== freerouting start $(Get-Date -Format 'HH:mm:ss') ===" | Out-File -Encoding utf8 -Append $log
& java -jar $jar -de $dsn -do $ses -mp 40 -mt 1 -oit 2.0 2>&1 | Select-Object -Last 15 | Out-File -Encoding utf8 -Append $log
"=== freerouting done $(Get-Date -Format 'HH:mm:ss') ===" | Out-File -Encoding utf8 -Append $log
if (-not (Test-Path -LiteralPath $ses)) { "NO SES" | Out-File -Encoding utf8 -Append $log; exit 1 }
Run "& '$py' tools\import_ses_into_current.py '$ses'"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t12.json hardware\QuadPreRecorder.kicad_pcb"
"FINISH DONE" | Out-File -Encoding utf8 -Append $log
