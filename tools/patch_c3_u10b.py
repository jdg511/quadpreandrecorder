"""Rev C3 one-off: drop the +5V feed that threads between C60's pads into C65
pad 1 (116.25,53.64)->(116.25,55.43)->(115.47,56.2). C65 is fed by U10.12's
stub and the (117.69,57.14) via instead, which frees the C60/C65 gap for
HP_OUT_L."""
import math, sys
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
def near(p, x, y): return math.hypot(mm(p.x) - x, mm(p.y) - y) < 0.05
kill = [((116.25, 53.64), (116.25, 55.43)), ((116.25, 55.43), (115.47, 56.2))]
n = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == "+5V":
        s, e = t.GetStart(), t.GetEnd()
        for a, b in kill:
            if (near(s, *a) and near(e, *b)) or (near(s, *b) and near(e, *a)):
                board.Remove(t); n += 1; break
print("+5V segments removed:", n)
pcbnew.SaveBoard(str(BOARD), board)
