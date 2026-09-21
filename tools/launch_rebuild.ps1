$log = "C:\Users\Jason\Documents\quadpreandrecorder\review_outputs\rebuild-diodefix.log"
if (Test-Path $log) { Remove-Item $log -Force }
$a = '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\Jason\Documents\quadpreandrecorder\tools\rebuild_all.ps1"'
Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
Write-Output ("rebuild launched: " + $log)
