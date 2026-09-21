# Rev C3: finishing pass after the manual escape patches. Everything on the
# board is protected; Freerouting only has BOOST_EN / BOOST_SS left to do.
$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$jar = Join-Path $repo "tools\cache\freerouting19.jar"
$fin = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish.dsn"
$finp = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-finish-plane.dsn"
$ses = Join-Path $repo "hardware\review_outputs\QuadPreRecorder-routed.ses"
Set-Location $repo
& $py tools\patch_c3_escape.py
if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }
& $py tools\export_dsn_from_board.py $fin
& $py tools\protect_fanout.py $fin | Select-Object -First 1
& $py tools\patch_dsn_plane.py $fin $finp | Select-Object -First 2
Write-Host "=== freerouting $(Get-Date -Format 'HH:mm:ss') ==="
& java -jar $jar -de $finp -do $ses -mp 30 -mt 1 -oit 2.0
Write-Host "=== freerouting done $(Get-Date -Format 'HH:mm:ss') ==="
if (Test-Path -LiteralPath $ses) {
    & $py tools\generate_pcb.py | Select-Object -Last 1
    & $py tools\import_route.py
    & $py tools\cleanup_board.py | Out-Null
    & $py tools\fix_jumper_pads.py
    & $py tools\add_gnd_stitching.py | Select-Object -Last 2
    & $py tools\stitch_pass2.py | Select-Object -Last 3
} else {
    Write-Host "NO SES from the finishing pass"
}
& $py tools\gnd_cluster_check.py | Select-Object -Last 3
& $cli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
Write-Host "=== FINISH C3B DONE $(Get-Date -Format 'HH:mm:ss') ==="
