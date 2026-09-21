Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\resch_erc.ps1
$r = Get-Content review_outputs\resch.log -Raw
if ($r -match "Errors 0  Warnings 0" -and $r -match "Found 0 schematic parity issues") {
  Copy-Item hardware\QuadPreRecorder.kicad_sch hardware\QuadPreRecorder.kicad_sch.revc3mic4-20260912 -Force
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\fab_and_audit.ps1 2>&1 | Out-File -Encoding utf8 review_outputs\fab-audit.log
  "RESCH+FAB DONE" | Out-File -Encoding utf8 -Append review_outputs\resch.log
} else {
  "RESCH FAILED - fab not rebuilt" | Out-File -Encoding utf8 -Append review_outputs\resch.log
}
