$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Push-Location $repo
try {
    Write-Host "=== netlist (schematic changed) ==="
    & $cli sch export netlist -o hardware\review_outputs\QuadPreRecorder.net hardware\QuadPreRecorder.kicad_sch
    Write-Host "=== ERC ==="
    & $cli sch erc --severity-error -o hardware\fabrication\QuadPreRecorder-erc.rpt hardware\QuadPreRecorder.kicad_sch
    Write-Host "=== regenerate board + re-import existing route ==="
    & $py tools\generate_pcb.py | Select-Object -Last 3
    & $py tools\import_route.py
    & $py tools\cleanup_board.py | Out-Null
    & $py tools\add_gnd_stitching.py | Select-Object -Last 2
    & $py tools\stitch_pass2.py | Select-Object -Last 3
    Write-Host "=== DRC ==="
    & $cli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
    Write-Host "=== REBUILD DONE ==="
}
finally { Pop-Location }
