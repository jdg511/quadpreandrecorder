"""One-off patch of the routed Rev C3 board (2026-09-12): re-bend the U7.8
stub that grazed pin 7 by 0.7 um, and draw the U10.12 -> C65 escape that
Freerouting never manages. Both are now also in fanout_decouple.py, so the
next full rebuild reproduces them; this just avoids a 20-minute re-route.
"""
import math, sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))

def pad(ref, num):
    # iterate rather than FindFootprintByReference: the latter handed back a
    # bare SwigPyObject on the second call after a board.Remove()
    for fp in board.Footprints():
        if fp.GetReference() != ref:
            continue
        for p in fp.Pads():
            if p.GetNumber() == num:
                return p
    raise SystemExit(ref + "." + num)

def track(ax, ay, bx, by, net, w=0.20, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(sp.mm(ax), sp.mm(ay)))
    t.SetEnd(pcbnew.VECTOR2I(sp.mm(bx), sp.mm(by)))
    t.SetWidth(sp.mm(w)); t.SetLayer(layer); t.SetNetCode(net)
    board.Add(t)

# Look every pad up BEFORE touching the track list: after board.Remove() the
# SWIG proxies from Footprints() come back as bare SwigPyObjects.
p8 = pad("U7", "8")
px, py, net8 = sp.to_mm(p8.GetPosition().x), sp.to_mm(p8.GetPosition().y), p8.GetNetCode()
p12, c65 = pad("U10", "12"), pad("C65", "1")
x12, y12, net12 = sp.to_mm(p12.GetPosition().x), sp.to_mm(p12.GetPosition().y), p12.GetNetCode()
x65, y65 = sp.to_mm(c65.GetPosition().x), sp.to_mm(c65.GetPosition().y)

# 1) U7.8 stub: (80.6375,49.5) -> (82,49.3) becomes two segments via (81.6,49.5)
removed = 0
for t in list(board.GetTracks()):
    if t.Type() != pcbnew.PCB_TRACE_T or t.GetNetname() != "+3V3_A" or t.GetLayer() != pcbnew.F_Cu:
        continue
    s, e = t.GetStart(), t.GetEnd()
    ends = {(round(sp.to_mm(s.x), 3), round(sp.to_mm(s.y), 3)), (round(sp.to_mm(e.x), 3), round(sp.to_mm(e.y), 3))}
    if (round(px, 3), round(py, 3)) in ends and (82.0, 49.3) in ends:
        board.Remove(t); removed += 1
print("U7.8 old stub removed:", removed)
track(px, py, 81.6, 49.5, net8)
track(81.6, 49.5, 82.0, 49.3, net8)

# 2) U10.12 -> C65.1
track(x12, y12, x12 + 0.9, y12, net12)
track(x12 + 0.9, y12, x65, y65, net12)
print("U10.12 -> C65.1 drawn, %.2f mm" % math.hypot(x65 - x12, y65 - y12))

pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
