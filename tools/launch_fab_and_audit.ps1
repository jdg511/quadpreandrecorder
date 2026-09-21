$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\fab-audit.log"
if (Test-Path $log) { Remove-Item $log -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\fab_and_audit.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("launched: " + $log)
