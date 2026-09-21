$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Push-Location $repo
try {
    Write-Host "=== jumper pads ==="
    & $py tools\fix_jumper_pads.py
    Write-Host "=== DRC ==="
    & $cli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
    Write-Host "=== classify ==="
    & python tools\unconnected_report.py
}
finally { Pop-Location }
