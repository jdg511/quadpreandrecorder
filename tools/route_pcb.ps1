param(
    # 2026-09-06: switched to Freerouting 1.9.0. Freerouting 2.2.4 reports the
    # Rev B board routed but its .ses silently omits several nets' wires
    # (ADC_LRCLK_IC, ADC_MICBIAS, DAC_BCLK_IC, HP_OUT_R + partial drops), which
    # KiCad then reports as ~19 unconnected pads. 1.9.0 exports every net.
    # 1.9.0 must run single-threaded (-mt 1): its multi-threaded optimizer is
    # documented to create clearance violations. -oit 2.0 stops the (slow,
    # single-threaded) optimizer once a pass improves the design by <2%.
    [string]$FreeroutingJar = "$PSScriptRoot\cache\freerouting19.jar",
    [int]$Passes = 100,
    [int]$Threads = 1,
    [double]$OptimizationThreshold = 2.0
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardware = Join-Path $repoRoot "hardware"
$kicadBin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$kicadPython = Join-Path $kicadBin "python.exe"
$kicadCli = Join-Path $kicadBin "kicad-cli.exe"
$netlist = Join-Path $hardware "review_outputs\QuadPreRecorder.net"
$dsn = Join-Path $hardware "review_outputs\QuadPreRecorder-unrouted.dsn"
$ses = Join-Path $hardware "review_outputs\QuadPreRecorder-routed.ses"

if (-not (Test-Path -LiteralPath $FreeroutingJar)) {
    throw "Freerouting jar not found: $FreeroutingJar"
}
if (-not (Test-Path -LiteralPath $kicadPython)) {
    throw "KiCad 10 Python not found: $kicadPython"
}
if (-not (Test-Path -LiteralPath $kicadCli)) {
    throw "KiCad 10 CLI not found: $kicadCli"
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Force (Join-Path $hardware "review_outputs") | Out-Null
    & $kicadPython tools\generate_schematic.py
    & $kicadPython tools\generate_footprints.py
    & $kicadCli sch export netlist -o $netlist hardware\QuadPreRecorder.kicad_sch
    & $kicadPython tools\generate_pcb.py
    & python tools\check_panel_orientation.py
    & java -jar $FreeroutingJar `
        -de $dsn -do $ses `
        -mp $Passes -mt $Threads -oit $OptimizationThreshold
    & $kicadPython tools\import_route.py
    & $kicadPython tools\cleanup_board.py
    & $kicadCli pcb drc --all-track-errors --schematic-parity --severity-error `
        -o hardware\fabrication\QuadPreRecorder-drc.rpt hardware\QuadPreRecorder.kicad_pcb
}
finally {
    Pop-Location
}
