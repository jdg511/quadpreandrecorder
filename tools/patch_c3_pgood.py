"""Rev C3 test-point rebuild: free U13.7 (PGOOD_N). Pin 6's GND fanout via at
(129.25,18.70) boxed pin 7 in; pins 6 and 8 are both GND, pin 8 keeps its via."""
import math, sys
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
def near(p, x, y): return math.hypot(mm(p.x) - x, mm(p.y) - y) < 0.06
n = 0
for t in list(board.GetTracks()):
    if t.GetNetname() != "GND":
        continue
    if t.Type() == pcbnew.PCB_VIA_T and near(t.GetPosition(), 129.25, 18.70):
        board.Remove(t); n += 1
    elif t.Type() == pcbnew.PCB_TRACE_T and near(t.GetStart(), 129.25, 17.96) and near(t.GetEnd(), 129.25, 18.70):
        board.Remove(t); n += 1
    elif t.Type() == pcbnew.PCB_TRACE_T and near(t.GetEnd(), 129.25, 17.96) and near(t.GetStart(), 129.25, 18.70):
        board.Remove(t); n += 1
print("U13.6 fanout items removed:", n)
pcbnew.SaveBoard(str(BOARD), board)
