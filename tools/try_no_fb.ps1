$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $kicadBin "python.exe"
$cli = Join-Path $kicadBin "kicad-cli.exe"
Push-Location $repoRoot
try {
    & $py tools\try_no_fb_pours.py
    Write-Host "--- DRC ---"
    & $cli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
}
finally { Pop-Location }
