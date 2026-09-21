"""Rev C3 one-off on the routed board: BOOST_SS via a relocated C79, and the
BOOST_EN via-pair hop over the CHASSIS B.Cu wall. See rev_c3_status memory.
Both placements/escapes are also in generate_pcb.py / fanout_decouple.py.
"""
import math, sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
gnd = board.FindNet("GND").GetNetCode()
ss = board.FindNet("BOOST_SS").GetNetCode()

def pad(ref, num):
    for fp in board.Footprints():
        if fp.GetReference() != ref:
            continue
        for p in fp.Pads():
            if p.GetNumber() == num:
                return p
    raise SystemExit(ref + "." + num)

def track(ax, ay, bx, by, net, w=0.20, layer=pcbnew.B_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(sp.mm(ax), sp.mm(ay))); t.SetEnd(pcbnew.VECTOR2I(sp.mm(bx), sp.mm(by)))
    t.SetWidth(sp.mm(w)); t.SetLayer(layer); t.SetNetCode(net); board.Add(t)

def via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y))); v.SetWidth(sp.mm(0.60)); v.SetDrill(sp.mm(0.30))
    v.SetNetCode(net); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v)

# pad lookups first (SWIG proxies go stale after board.Remove)
p5 = pad("U11", "5")
x5, y5 = sp.to_mm(p5.GetPosition().x), sp.to_mm(p5.GetPosition().y)
c79 = None
for fp in board.Footprints():
    if fp.GetReference() == "C79":
        c79 = fp

# 1) move C79 to the bottom at (5.5, 37.0) rot 270 (pad 1 = BOOST_SS north)
#    - done BEFORE any board.Remove(), which stales the footprint proxies
if c79.GetLayer() != pcbnew.B_Cu:
    c79.Flip(c79.GetPosition(), False)
c79.SetPosition(pcbnew.VECTOR2I(sp.mm(5.5), sp.mm(37.0)))
c79.SetOrientationDegrees(270.0)
pads = {p.GetNumber(): (sp.to_mm(p.GetPosition().x), sp.to_mm(p.GetPosition().y)) for p in c79.Pads()}
print("C79 moved: pad1 %s pad2 %s" % (pads["1"], pads["2"]))
assert abs(pads["1"][1] - 36.22) < 0.05, pads

# 2) wipe every BOOST_SS track/via, re-add the escape stub + via
n = 0
for t in list(board.GetTracks()):
    if t.GetNetCode() == ss:
        board.Remove(t); n += 1
print("BOOST_SS items removed:", n)
track(x5, y5, 5.30, 32.30, ss, layer=pcbnew.F_Cu); via(5.30, 32.30, ss)

# 3) BOOST_SS via -> C79 pad 1, and C79 pad 2 GND stub + via
track(5.30, 32.30, pads["1"][0], pads["1"][1], ss)
track(pads["2"][0], pads["2"][1], pads["2"][0], pads["2"][1] + 1.1, gnd, w=0.30)
via(pads["2"][0], pads["2"][1] + 1.1, gnd)
print("BOOST_SS done; C79 GND via at (%.2f,%.2f)" % (pads["2"][0], pads["2"][1] + 1.1))

pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
