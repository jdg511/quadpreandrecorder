Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "name='powershell.exe'" | Where-Object { $_.CommandLine -like '*full_route_body*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output ("killed " + $_.ProcessId) }
Start-Sleep 2
Write-Output ("java left: " + (Get-Process java -ErrorAction SilentlyContinue | Measure-Object).Count)
