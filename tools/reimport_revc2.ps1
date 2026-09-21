# Regenerate a clean board, import the EXISTING .ses, fill, DRC. No re-routing.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
Push-Location $repoRoot
try {
    Write-Host "--- generate_pcb (clean board) ---"
    & $kicadPython tools\generate_pcb.py
    Write-Host "--- import_route ---"
    & $kicadPython tools\import_route.py
    Write-Host "--- cleanup_board ---"
    & $kicadPython tools\cleanup_board.py
    Write-Host "--- DRC ---"
    & $kicadCli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
    Write-Host "=== REIMPORT DONE ==="
}
finally { Pop-Location }
