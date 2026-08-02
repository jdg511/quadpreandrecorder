$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"

Push-Location $repoRoot
try {
    Write-Host "=== Running mini_router.py ==="
    & $kicadPython tools\cache\mini_router.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "mini_router.py exited with code $LASTEXITCODE"
    }

    Write-Host "=== Running DRC ==="
    & $kicadCli pcb drc --all-track-errors --schematic-parity --severity-error -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
}
finally {
    Pop-Location
}
