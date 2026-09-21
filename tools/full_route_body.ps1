# Rev C2 full rebuild: pristine board -> pre-flight -> GND fanout -> autoroute
# -> import -> stitch -> finishing pass -> verify.
$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$jar = Join-Path $repo "tools\cache\freerouting19.jar"
$raw = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-unrouted.dsn"
$dsn = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-unrouted-plane.dsn"
$fin = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish.dsn"
$finp = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish-plane.dsn"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-routed.ses"
Set-Location $repo

if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }

Write-Host "=== pristine board + DSN ==="
& $py tools\generate_pcb.py | Select-Object -Last 2

Write-Host "=== PRE-FLIGHT: pads vs board edge and edge keepout ==="
& $py tools\preflight_pads.py
if ($LASTEXITCODE -ne 0) { Write-Host "PRE-FLIGHT FAILED - stopping"; exit 1 }

Write-Host "=== Rev C3: decoupling vias + U10 EP via array ==="
& $py tools\fanout_decouple.py
if ($LASTEXITCODE -ne 0) { Write-Host "FANOUT_DECOUPLE FAILED - stopping"; exit 1 }
Write-Host "=== GND fanout on every SMD ground pad ==="
& $py tools\fanout_gnd.py --allow-existing | Select-Object -Last 4
Write-Host "=== protect the fanout ==="
& $py tools\protect_fanout.py $raw
Write-Host "=== In1.Cu -> (type power) ==="
& $py tools\patch_dsn_plane.py $raw $dsn

Write-Host "=== freerouting $(Get-Date -Format 'HH:mm:ss') ==="
& java -jar $jar -de $dsn -do $ses -mp 100 -mt 1 -oit 2.0
Write-Host "=== freerouting done $(Get-Date -Format 'HH:mm:ss') ==="
if (-not (Test-Path -LiteralPath $ses)) { Write-Host "NO SES"; exit 1 }

Write-Host "=== regenerate pristine, import the route ==="
& $py tools\generate_pcb.py | Select-Object -Last 1
& $py tools\import_route.py
& $py tools\cleanup_board.py | Out-Null
& $py tools\fix_jumper_pads.py
& $py tools\add_gnd_stitching.py | Select-Object -Last 2
& $py tools\stitch_pass2.py | Select-Object -Last 3

Write-Host "=== FINISHING PASS: re-route whatever is left, everything else locked ==="
Remove-Item -LiteralPath $ses -Force
& $py tools\export_dsn_from_board.py $fin
& $py tools\protect_fanout.py $fin
& $py tools\patch_dsn_plane.py $fin $finp
& java -jar $jar -de $finp -do $ses -mp 30 -mt 1 -oit 2.0
if (Test-Path -LiteralPath $ses) {
    & $py tools\generate_pcb.py | Select-Object -Last 1
    & $py tools\import_route.py
    & $py tools\cleanup_board.py | Out-Null
    & $py tools\fix_jumper_pads.py
    & $py tools\add_gnd_stitching.py | Select-Object -Last 2
    & $py tools\stitch_pass2.py | Select-Object -Last 3
} else {
    Write-Host "finishing pass produced no SES - keeping the first route"
}

Write-Host "=== stackup block ==="
& $py tools\set_stackup.py
Write-Host "=== connectivity ==="
& $py tools\gnd_cluster_check.py
Write-Host "=== DRC ==="
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
Write-Host "=== FULL ROUTE DONE $(Get-Date -Format 'HH:mm:ss') ==="
