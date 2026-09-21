Set-Location "C:\Users\Jason\Documents\quadpreandrecorder"
$t = Get-Content hardware\review_outputs\final-drc.rpt
$want = 'shorting_items','hole_clearance','clearance','track_dangling','hole_to_hole','footprint_symbol_mismatch'
$n = 0
for ($i = 0; $i -lt $t.Count; $i++) {
  $l = $t[$i]
  if ($l -match '^\[(\w+)\]' -and $want -contains $Matches[1]) {
    ($t[$i..([Math]::Min($i + 3, $t.Count - 1))] -join ' | ')
    $n++
    if ($n -ge 22) { break }
  }
}
"--- net_conflict samples:"
$m = 0
for ($i = 0; $i -lt $t.Count; $i++) {
  if ($t[$i] -match '^\[net_conflict\]') { ($t[$i..($i + 2)] -join ' | '); $m++; if ($m -ge 3) { break } }
}
"--- field mismatch samples:"
$m = 0
for ($i = 0; $i -lt $t.Count; $i++) {
  if ($t[$i] -match '^\[footprint_symbol_field_mismatch\]') { ($t[$i..($i + 2)] -join ' | '); $m++; if ($m -ge 2) { break } }
}
