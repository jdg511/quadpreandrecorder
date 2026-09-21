$p = "C:\Program Files\KiCad\10.0\share\kicad\footprints\Button_Switch_THT.pretty"
Write-Output "=== MEC / Multimec footprints ==="
Get-ChildItem $p | Where-Object { $_.Name -match 'MEC|Multimec|5G|5E' } |
    Select-Object -ExpandProperty Name
Write-Output ""
Write-Output "=== all THT button footprints ==="
Get-ChildItem $p | Select-Object -ExpandProperty Name
