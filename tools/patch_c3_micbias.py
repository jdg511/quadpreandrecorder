"""Rev C3: drop C38 and leave U7.5 (MICBIAS) unconnected on the ROUTED board,
matching the regenerated schematic (see generate_schematic.py)."""
import math, sys
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
c38 = None
pads = {}
for fp in board.Footprints():
    if fp.GetReference() == "C38":
        c38 = fp
        pads = {p.GetNumber(): (mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fp.Pads()}
    if fp.GetReference() == "U7":
        for p in fp.Pads():
            if p.GetNumber() == "5":
                p.SetNetCode(0)
                print("U7.5 net cleared")
if c38 is None:
    raise SystemExit("C38 not on the board (already removed?)")
gx, gy = pads["2"]
# collect first, remove last: SWIG proxies go stale after board.Remove()
doomed, via_pts = [], []
for t in board.GetTracks():
    name = t.GetNetname()
    if t.Type() == pcbnew.PCB_TRACE_T and name in ("GND", "ADC_MICBIAS"):
        s, e = t.GetStart(), t.GetEnd()
        sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
        at_s = math.hypot(sx - gx, sy - gy) < 0.05
        at_e = math.hypot(ex - gx, ey - gy) < 0.05
        if name == "ADC_MICBIAS" or at_s or at_e:
            doomed.append(t)
            if name == "GND":
                via_pts.append((ex, ey) if at_s else (sx, sy))
    elif t.Type() == pcbnew.PCB_VIA_T and name == "ADC_MICBIAS":
        doomed.append(t)
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND":
        vx, vy = mm(t.GetPosition().x), mm(t.GetPosition().y)
        if any(math.hypot(vx - x, vy - y) < 0.05 for x, y in via_pts):
            doomed.append(t)
for t in doomed:
    board.Remove(t)
board.Remove(c38)
print("C38 removed; tracks/vias removed:", len(doomed))
pcbnew.SaveBoard(str(BOARD), board)
