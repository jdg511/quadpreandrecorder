$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
$snap = Join-Path $repo "hardware\snapshots\QuadPreRecorder-before-pass3.kicad_pcb"
Push-Location $repo
try {
    Write-Host "=== restore the routed board (undo any earlier pass-3 attempt) ==="
    Copy-Item $snap hardware\QuadPreRecorder.kicad_pcb -Force
    Write-Host "=== stitch pass 3 ==="
    & $py tools\stitch_pass3.py
    Write-Host "=== re-check with KiCad connectivity ==="
    & $py tools\gnd_cluster_check.py
    Write-Host "=== DRC ==="
    & $cli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
}
finally { Pop-Location }
