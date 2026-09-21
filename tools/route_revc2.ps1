# Rev C2 route: Freerouting (4 layers) -> import -> cleanup/fill -> DRC.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardware = Join-Path $repoRoot "hardware"
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
$jar = Join-Path $PSScriptRoot "cache\freerouting19.jar"
$dsn = Join-Path $hardware "review_outputs\QuadPreRecorder-unrouted.dsn"
$ses = Join-Path $hardware "review_outputs\QuadPreRecorder-routed.ses"

Push-Location $repoRoot
try {
    Write-Host "=== freerouting start $(Get-Date -Format 'HH:mm:ss') ==="
    & java -jar $jar -de $dsn -do $ses -mp 100 -mt 1 -oit 2.0
    Write-Host "=== freerouting done $(Get-Date -Format 'HH:mm:ss') ==="
    if (-not (Test-Path -LiteralPath $ses)) { throw "no .ses produced" }
    Write-Host "=== import_route ==="
    & $kicadPython tools\import_route.py
    Write-Host "=== cleanup_board (fills zones) ==="
    & $kicadPython tools\cleanup_board.py
    Write-Host "=== DRC ==="
    & $kicadCli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
    Write-Host "DRC exit: $LASTEXITCODE"
    Write-Host "=== ALL DONE $(Get-Date -Format 'HH:mm:ss') ==="
}
catch {
    Write-Host "=== FAILED: $_ ==="
}
finally {
    Pop-Location
}
