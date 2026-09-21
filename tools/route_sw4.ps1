# Rev C2 SW4 swap: patch the DSN so In1.Cu is a real plane, autoroute,
# import, stitch, DRC. Expect ~5 minutes for Freerouting.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardware = Join-Path $repoRoot "hardware"
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
$jar = Join-Path $PSScriptRoot "cache\freerouting19.jar"
$rawDsn = Join-Path $hardware "review_outputs\QuadPreRecorder-unrouted.dsn"
$dsn = Join-Path $hardware "review_outputs\QuadPreRecorder-unrouted-plane.dsn"
$ses = Join-Path $hardware "review_outputs\QuadPreRecorder-routed.ses"

Push-Location $repoRoot
try {
    # A stale .ses from an earlier run must never be imported by accident.
    if (Test-Path -LiteralPath $ses) { Remove-Item -LiteralPath $ses -Force }

    Write-Host "=== patch DSN: In1.Cu -> (type power) ==="
    & $kicadPython tools\patch_dsn_plane.py $rawDsn $dsn
    if (-not (Test-Path -LiteralPath $dsn)) { throw "no patched .dsn produced" }

    Write-Host "=== freerouting start $(Get-Date -Format 'HH:mm:ss') ==="
    & java -jar $jar -de $dsn -do $ses -mp 100 -mt 1 -oit 2.0
    Write-Host "=== freerouting done $(Get-Date -Format 'HH:mm:ss') ==="
    if (-not (Test-Path -LiteralPath $ses)) { throw "no .ses produced" }

    Write-Host "=== import_route ==="
    & $kicadPython tools\import_route.py
    Write-Host "=== cleanup_board (fills zones) ==="
    & $kicadPython tools\cleanup_board.py
    Write-Host "=== gnd stitching ==="
    & $kicadPython tools\add_gnd_stitching.py | Select-Object -Last 2
    & $kicadPython tools\stitch_pass2.py | Select-Object -Last 3
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
