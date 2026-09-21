$p = "C:\Program Files\KiCad\10.0\share\kicad\footprints\LED_THT.pretty"
Write-Output "=== horizontal 3mm LED footprints ==="
Get-ChildItem $p | Where-Object { $_.Name -match 'D3.0mm_Horizontal' } |
    Select-Object -ExpandProperty Name
Write-Output ""
Write-Output "=== horizontal 5mm ==="
Get-ChildItem $p | Where-Object { $_.Name -match 'D5.0mm_Horizontal' } |
    Select-Object -ExpandProperty Name
