"""python remove_net_items_in_box.py NET x0 y0 x1 y1 : delete NET's segments AND vias inside the box (all layers)."""
import sys
from pathlib import Path
import pcbnew
NET = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6])
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
n = 0
for t in list(board.GetTracks()):
    if t.GetNetname() != NET:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); pts = [p]
    else:
        pts = [t.GetStart(), t.GetEnd()]
    if all(x0 <= mm(p.x) <= x1 and y0 <= mm(p.y) <= y1 for p in pts):
        board.Remove(t); n += 1
pcbnew.SaveBoard(str(BOARD), board)
print("%s items removed in box: %d" % (NET, n))
