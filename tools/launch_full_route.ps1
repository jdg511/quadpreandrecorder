$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\full-route.log"
if (Test-Path $log) { Remove-Item $log -Force }
if (Test-Path ($log + '.err')) { Remove-Item ($log + '.err') -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\full_route_body.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("launched: " + $log)
