$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$jar = Join-Path $repo "tools\cache\freerouting19.jar"
$raw = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix2.dsn"
$dsn = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix2-plane.dsn"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-teensyfix2.ses"
$log = "review_outputs\finish-teensy2.log"
$free = "NAV_DOWN,NAV_UP,NAV_LEFT,NAV_RIGHT,NAV_PUSH,NAV_ENC_A,NAV_ENC_B,REC_LED,GAIN_SW,LINE_MUTE,TFT_LED,TEENSY_VIN,BAT_SENSE,VBUS_SENSE,CHG_STAT_N,HP_ENABLE,DAC_MUTE,COLD_CTRL,KEEP_ON,PGOOD_N,REC_BUTTON,BOOST_EN,CTP_RST,TOUCH_IRQ,GAIN_A,GAIN_B,GAIN_PUSH,PAD_CTRL,MIC5_CTRL,MIC9_CTRL"
Set-Location $repo
function Run($cmd) { Invoke-Expression $cmd 2>&1 | Select-String -NotMatch "memory leak|duplicate image handler" | Out-File -Encoding utf8 -Append $log }
Remove-Item $log -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }
Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\QuadPreRecorder.kicad_pcb.teensyfix-fr1-20260915 -Force
Run "& '$py' tools\remove_net_items_in_box.py GND 76.8 64.3 77.2 64.7"
Run "& '$py' tools\export_dsn_from_board.py '$raw'"
Run "& '$py' tools\protect_except.py '$raw' '$free'"
Run "& '$py' tools\patch_dsn_plane.py '$raw' '$dsn'"
"=== freerouting start $(Get-Date -Format 'HH:mm:ss') ===" | Out-File -Encoding utf8 -Append $log
& java -jar $jar -de $dsn -do $ses -mp 150 -mt 1 -oit 2.0 2>&1 | Select-Object -Last 12 | Out-File -Encoding utf8 -Append $log
"=== freerouting done $(Get-Date -Format 'HH:mm:ss') ===" | Out-File -Encoding utf8 -Append $log
if (-not (Test-Path -LiteralPath $ses)) { "NO SES" | Out-File -Encoding utf8 -Append $log; exit 1 }
Run "& '$py' tools\import_ses_into_current.py '$ses'"
Run "& '$cli' pcb drc --all-track-errors --schematic-parity --severity-error --format json -o hardware\fabrication\drc-t13.json hardware\QuadPreRecorder.kicad_pcb"
"FINISH2 DONE" | Out-File -Encoding utf8 -Append $log
