$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\route-fanout.log"
if (Test-Path $log) { Remove-Item $log -Force }
if (Test-Path ($log + '.err')) { Remove-Item ($log + '.err') -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\route_fanout_body.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("launched: " + $log)
