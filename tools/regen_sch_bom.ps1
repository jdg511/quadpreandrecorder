$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin"
$py = Join-Path $bin "python.exe"
$cli = Join-Path $bin "kicad-cli.exe"
Push-Location $repo
try {
    Write-Host "=== generate_schematic ==="
    & $py tools\generate_schematic.py
    if ($LASTEXITCODE -ne 0) { Write-Host "SCHEMATIC GENERATION FAILED"; return }
    Write-Host "=== export BOM ==="
    & $cli sch export bom `
        --fields "Reference,Value,Footprint,Manufacturer,MPN,AltMPN,LCSC,${QUANTITY},${DNP}" `
        --labels "Reference,Value,Footprint,Manufacturer,MPN,AltMPN,LCSC,Qty,DNP" `
        --group-by "Value,Footprint,MPN" --sort-field "Reference" `
        -o review_outputs\BOM-current.csv hardware\QuadPreRecorder.kicad_sch
    Write-Host "=== audit ==="
    & python tools\audit_bom.py
}
finally { Pop-Location }
