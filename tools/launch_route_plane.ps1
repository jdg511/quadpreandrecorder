Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\route-revc2-plane.log"
if (Test-Path $log) { Remove-Item $log -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\route_revc2_plane.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("plane route launched: " + $log)
