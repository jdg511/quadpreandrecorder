$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\route-revc2-4layer.log"
if (Test-Path $log) { Remove-Item $log -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\route_revc2.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("route launched, log: " + $log)
