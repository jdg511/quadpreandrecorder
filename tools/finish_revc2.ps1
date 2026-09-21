# Clean rebuild from the existing .ses: board -> route import -> fill -> stitch -> DRC
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
Push-Location $repoRoot
try {
    & $kicadPython tools\generate_pcb.py | Out-Null
    Write-Host "--- board regenerated ---"
    & $kicadPython tools\import_route.py
    & $kicadPython tools\cleanup_board.py | Out-Null
    Write-Host "--- route imported + zones filled ---"
    & $kicadPython tools\add_gnd_stitching.py
    & $kicadPython tools\stitch_pass2.py
    Write-Host "--- DRC ---"
    & $kicadCli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
    Write-Host "=== FINISH DONE ==="
}
finally { Pop-Location }
