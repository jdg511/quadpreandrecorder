$py = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe"
Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$out = "review_outputs\dump2.txt"
"===== all items x 81..87 y 46.5..50.5 =====" | Out-File -Encoding utf8 $out
& $py tools\dump_region.py 81 46.5 87 50.5 2>&1 | Out-File -Encoding utf8 -Append $out
"DONE" | Out-File -Encoding utf8 -Append $out
