$repo = "C:\Users\Jason\Documents\quadpreandrecorder"
Write-Host "=== where placeholder MPN strings live ==="
Select-String -Path "$repo\tools\*.py" -Pattern 'GRM series|RC0603FR series|TNPW0603 series|EEE-FK series' |
    Select-Object -First 12 |
    ForEach-Object { "{0}:{1}  {2}" -f (Split-Path -Leaf $_.Path), $_.LineNumber, $_.Line.Trim() }

Write-Host ""
Write-Host "=== load_design_parts definition ==="
Select-String -Path "$repo\tools\*.py" -Pattern 'def load_design_parts|DESIGN_PARTS|parts_table|Part\(' |
    Select-Object -First 15 |
    ForEach-Object { "{0}:{1}  {2}" -f (Split-Path -Leaf $_.Path), $_.LineNumber, $_.Line.Trim() }

Write-Host ""
Write-Host "=== any data files ==="
Get-ChildItem -Path $repo -Recurse -Include *.csv,*.json,*.yaml,*.yml -File |
    Where-Object { $_.FullName -notmatch 'manufacturing|gerbers|\.git|cache|__pycache__|review_outputs|node_modules' } |
    Select-Object -First 20 |
    ForEach-Object { $_.FullName.Replace($repo, '.') + "   " + $_.Length }
