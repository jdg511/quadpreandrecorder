$ErrorActionPreference = "Continue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cli = Join-Path $env:LOCALAPPDATA "Programs\KiCad\10.0\bin\kicad-cli.exe"
$out = Join-Path $repoRoot "review_outputs\BOM-current.csv"
Push-Location $repoRoot
try {
    & $cli sch export bom `
        --fields "Reference,Value,Footprint,Manufacturer,MPN,Datasheet,Description,${QUANTITY},${DNP}" `
        --labels "Reference,Value,Footprint,Manufacturer,MPN,Datasheet,Description,Qty,DNP" `
        --group-by "Value,Footprint,Manufacturer,MPN" `
        --sort-field "Reference" `
        -o $out hardware\QuadPreRecorder.kicad_sch
    Write-Host ("exit " + $LASTEXITCODE)
    if (Test-Path $out) { Write-Host ("lines: " + (Get-Content $out).Count) }
}
finally { Pop-Location }
