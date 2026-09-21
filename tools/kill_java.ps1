Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Output "java killed"
