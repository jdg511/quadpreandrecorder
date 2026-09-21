"""Rev C3 one-off: give U11.4 (BOOST_EN) and U11.5 (BOOST_SS) escape vias.

With In2 gone as a routing layer the TPS61175's two control pins ended up
fenced in on F.Cu: VBOOST_IN wraps around the west pin column at x=4.55 and
the GND fanout of pin 6 sits right under them. Freerouting could not escape
either pin. Fix: drop pin 6's fanout (pins 6 and 7 are adjacent GND pads, and
pin 7 keeps its via; the top pour joins them), then via pins 4 and 5 down to
B.Cu in the 1.15 mm band between the VBOOST_IN track and the pad ends.
Also in fanout_decouple.py for the next full rebuild.
"""
import math, sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
gnd = board.FindNet("GND").GetNetCode()

def pad(ref, num):
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

def via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y)))
    v.SetWidth(sp.mm(0.60)); v.SetDrill(sp.mm(0.30))
    v.SetNetCode(net); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)

p4, p5, p6 = pad("U11", "4"), pad("U11", "5"), pad("U11", "6")
x4, y4, n4 = sp.to_mm(p4.GetPosition().x), sp.to_mm(p4.GetPosition().y), p4.GetNetCode()
x5, y5, n5 = sp.to_mm(p5.GetPosition().x), sp.to_mm(p5.GetPosition().y), p5.GetNetCode()
x6, y6 = sp.to_mm(p6.GetPosition().x), sp.to_mm(p6.GetPosition().y)

# 1) remove pin 6's GND stub and its via (the one at ~ (5.63, 32.80))
removed = 0
for t in list(board.GetTracks()):
    if t.GetNetCode() != gnd:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        if math.hypot(sp.to_mm(p.x) - 5.63, sp.to_mm(p.y) - 32.80) < 0.2:
            board.Remove(t); removed += 1
    elif t.Type() == pcbnew.PCB_TRACE_T:
        s, e = t.GetStart(), t.GetEnd()
        pts = [(sp.to_mm(s.x), sp.to_mm(s.y)), (sp.to_mm(e.x), sp.to_mm(e.y))]
        if any(math.hypot(px - x6, py - y6) < 0.05 for px, py in pts) and any(math.hypot(px - 5.63, py - 32.80) < 0.2 for px, py in pts):
            board.Remove(t); removed += 1
print("U11.6 fanout items removed:", removed)

# 2) escape vias
track(x4, y4, 5.30, 31.50, n4); via(5.30, 31.50, n4)
track(x5, y5, 5.30, 32.30, n5); via(5.30, 32.30, n5)
print("U11.4 %s via (5.30,31.50); U11.5 %s via (5.30,32.30)" % (p4.GetNetname(), p5.GetNetname()))

pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
