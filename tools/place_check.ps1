$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Push-Location $repo
try {
    Write-Host "=== netlist ==="
    & $cli sch export netlist -o hardware\review_outputs\QuadPreRecorder.net hardware\QuadPreRecorder.kicad_sch
    Write-Host "=== ERC ==="
    & $cli sch erc --severity-error -o hardware\fabrication\QuadPreRecorder-erc.rpt hardware\QuadPreRecorder.kicad_sch
    Write-Host "=== generate board (unrouted) ==="
    & $py tools\generate_pcb.py | Select-Object -Last 4
    Write-Host "=== dump placement ==="
    & $py tools\dump_placement.py hardware\QuadPreRecorder.kicad_pcb review_outputs\placement.json
    Write-Host "=== overlap report ==="
    & python tools\overlap_report.py
}
finally { Pop-Location }
