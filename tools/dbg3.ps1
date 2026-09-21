$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$p = Start-Process -FilePath $py -ArgumentList 'tools\final_check_fixes3.py' -NoNewWindow -Wait -PassThru -RedirectStandardOutput review_outputs\dbg3.out -RedirectStandardError review_outputs\dbg3.err
"exit " + $p.ExitCode
Get-Content review_outputs\dbg3.out
Get-Content review_outputs\dbg3.err
