param(
    [string]$FreeroutingJar = "$PSScriptRoot\cache\freerouting-2.2.4.jar",
    [int]$Passes = 40,
    [int]$Threads = 12
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardware = Join-Path $repoRoot "hardware"
$kicadPython = "C:\Program Files\KiCad\10.0\bin\python.exe"
$netlist = Join-Path $hardware "review_outputs\QuadPreRecorder.net"
$dsn = Join-Path $hardware "review_outputs\QuadPreRecorder-unrouted.dsn"
$ses = Join-Path $hardware "review_outputs\QuadPreRecorder-routed.ses"

if (-not (Test-Path -LiteralPath $FreeroutingJar)) {
    throw "Freerouting jar not found: $FreeroutingJar"
}
if (-not (Test-Path -LiteralPath $kicadPython)) {
    throw "KiCad 10 Python not found: $kicadPython"
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Force (Join-Path $hardware "review_outputs") | Out-Null
    & $kicadPython tools\generate_schematic.py
    & $kicadPython tools\generate_footprints.py
    & kicad-cli sch export netlist -o $netlist hardware\QuadPreRecorder.kicad_sch
    & $kicadPython tools\generate_pcb.py
    & java -jar $FreeroutingJar `
        -de $dsn -do $ses `
        --gui.enabled=false -mp $Passes -mt $Threads -da `
        --logging.console.level=INFO --logging.file.enabled=false
    & $kicadPython tools\import_route.py
    & $kicadPython tools\cleanup_board.py
    & kicad-cli pcb drc --all-track-errors --schematic-parity --severity-all `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
}
finally {
    Pop-Location
}
