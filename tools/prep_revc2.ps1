# Rev C2 pre-route: regenerate schematic, footprints, netlist, PCB. No routing.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardware = Join-Path $repoRoot "hardware"
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
$netlist = Join-Path $hardware "review_outputs\QuadPreRecorder.net"

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Force (Join-Path $hardware "review_outputs") | Out-Null
    Write-Host "--- generate_schematic ---"
    & $kicadPython tools\generate_schematic.py
    Write-Host "--- generate_footprints ---"
    & $kicadPython tools\generate_footprints.py
    Write-Host "--- netlist ---"
    & $kicadCli sch export netlist -o $netlist hardware\QuadPreRecorder.kicad_sch
    Write-Host "--- generate_pcb ---"
    & $kicadPython tools\generate_pcb.py
    Write-Host "--- panel orientation ---"
    & $kicadPython tools\check_panel_orientation.py
    Write-Host "--- ERC ---"
    & $kicadCli sch erc --severity-error --exit-code-violations `
        -o hardware\fabrication\QuadPreRecorder-erc.rpt hardware\QuadPreRecorder.kicad_sch
    Write-Host "ERC exit: $LASTEXITCODE"
}
finally {
    Pop-Location
}
