"""Rev C3 one-off: unbox U10.12. Freerouting wrapped HP_OUT_L (pin 14) around
the front of pin 12 (x=114.77, y 55.95-56.68), which is why pin 12 could never
escape east to C65. Remove that wrap; poly_route.py then re-lays HP_OUT_L
through the 0.65 mm gap between C60's and C65's pads. Also drops the C79 GND
via that landed on the +10V5 track."""
import math, sys
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
def near(p, x, y): return math.hypot(mm(p.x) - x, mm(p.y) - y) < 0.05
kill = [((113.96, 55.5), (114.33, 55.5)), ((114.33, 55.5), (114.77, 55.95)), ((114.77, 55.95), (114.77, 56.68)),
        ((114.77, 56.68), (115.97, 57.88)), ((115.97, 57.88), (118.44, 57.88))]
n = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == "HP_OUT_L":
        s, e = t.GetStart(), t.GetEnd()
        for a, b in kill:
            if (near(s, *a) and near(e, *b)) or (near(s, *b) and near(e, *a)):
                board.Remove(t); n += 1; break
    elif t.GetNetname() == "GND":
        if t.Type() == pcbnew.PCB_VIA_T and near(t.GetPosition(), 5.5, 38.875):
            board.Remove(t); n += 1
        elif t.Type() == pcbnew.PCB_TRACE_T and near(t.GetStart(), 5.5, 37.775) and near(t.GetEnd(), 5.5, 38.875):
            board.Remove(t); n += 1
print("items removed:", n)
pcbnew.SaveBoard(str(BOARD), board)
