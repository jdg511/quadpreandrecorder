"""python remove_tracks_in_box.py NET LAYER x0 y0 x1 y1 : delete NET's segments on LAYER lying fully inside the box (vias untouched)."""
import sys
from pathlib import Path
import pcbnew
NET, LAYER = sys.argv[1], sys.argv[2]; x0, y0, x1, y1 = map(float, sys.argv[3:7])
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
layer = pcbnew.F_Cu if LAYER == "F.Cu" else pcbnew.B_Cu
mm = pcbnew.ToMM
n = 0
for t in list(board.GetTracks()):
    if t.Type() != pcbnew.PCB_TRACE_T or t.GetNetname() != NET or t.GetLayer() != layer:
        continue
    s, e = t.GetStart(), t.GetEnd()
    if all(x0 <= mm(p.x) <= x1 and y0 <= mm(p.y) <= y1 for p in (s, e)):
        board.Remove(t); n += 1
pcbnew.SaveBoard(str(BOARD), board)
print("%s %s segments removed in box: %d" % (NET, LAYER, n))
