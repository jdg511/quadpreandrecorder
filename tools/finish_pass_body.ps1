$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$jar = Join-Path $repo "tools\cache\freerouting19.jar"
$raw = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish.dsn"
$dsn = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish-plane.dsn"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-routed.ses"
Set-Location $repo

Copy-Item hardware\QuadPreRecorder.kicad_pcb hardware\snapshots\QuadPreRecorder-before-finish.kicad_pcb -Force
if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }

Write-Host "=== export DSN from the routed board ==="
& $py tools\export_dsn_from_board.py $raw
Write-Host "=== protect everything already routed ==="
& $py tools\protect_fanout.py $raw
Write-Host "=== In1.Cu -> (type power) ==="
& $py tools\patch_dsn_plane.py $raw $dsn

Write-Host "=== freerouting finishing pass $(Get-Date -Format 'HH:mm:ss') ==="
# -oit 0 means "optimize until nothing improves", which ran for 7 minutes with
# nothing to gain because every existing wire is protected. 2.0 is the value
# that finishes in about a minute.
& java -jar $jar -de $dsn -do $ses -mp 30 -mt 1 -oit 2.0
Write-Host "=== freerouting done $(Get-Date -Format 'HH:mm:ss') ==="
if (-not (Test-Path -LiteralPath $ses)) { Write-Host "NO SES"; exit 1 }

Write-Host "=== regenerate pristine board, import the finished route ==="
& $py tools\generate_pcb.py | Select-Object -Last 1
& $py tools\import_route.py
& $py tools\cleanup_board.py | Out-Null
& $py tools\fix_jumper_pads.py
& $py tools\add_gnd_stitching.py | Select-Object -Last 2
& $py tools\stitch_pass2.py | Select-Object -Last 3
Write-Host "=== connectivity ==="
& $py tools\gnd_cluster_check.py
Write-Host "=== DRC ==="
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
Write-Host "=== FINISH PASS DONE $(Get-Date -Format 'HH:mm:ss') ==="
