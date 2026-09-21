Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|kicad-cli|java' } | ForEach-Object { Write-Output ($_.ProcessId.ToString() + "  " + $_.Name + "  " + [string]$_.CommandLine) }
Write-Output "done"
