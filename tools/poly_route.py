r"""Rev C3: add a hand-specified multi-layer route for one net, every piece
checked against stitch_pass3's geometry rules before anything is saved.

    python tools/poly_route.py NET "B:x,y;x,y;x,y V F:x,y V B:x,y;x,y"

Tokens: 'B:' / 'F:' start a polyline on B.Cu / F.Cu (points separated by
';'), 'V' drops a 0.6/0.3 via at the current point and the next polyline
continues from it on its own layer. Width 0.20 mm.
"""
import math, sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

NET, SPEC = sys.argv[1], sys.argv[2]
FORCE = "--force" in sys.argv
W = 0.20
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
net = board.FindNet(NET)
if net is None:
    raise SystemExit("no net " + NET)
sp.GND_NAMES = (NET,)
sp.TRACK_W = W
obs = sp.build_obstacles(board)

segs, vias = [], []
cur = None
for tok in SPEC.split():
    if tok == "V":
        vias.append(cur)
        continue
    layer = pcbnew.F_Cu if tok[0] == "F" else pcbnew.B_Cu
    pts = [tuple(map(float, p.split(","))) for p in tok[2:].split(";")]
    if cur is not None and pts[0] != cur:
        pts.insert(0, cur)
    for a, b in zip(pts, pts[1:]):
        segs.append((a, b, layer))
    cur = pts[-1]

bad = 0
for (a, b, layer) in segs:
    ok = sp.track_is_legal(a[0], a[1], b[0], b[1], layer, obs, None)
    print("%s seg %s (%.2f,%.2f)-(%.2f,%.2f) %.1f mm" % ("ok " if ok else "BAD", board.GetLayerName(layer), a[0], a[1], b[0], b[1], math.hypot(b[0]-a[0], b[1]-a[1])))
    bad += not ok
for (x, y) in vias:
    ok = sp.via_is_legal(x, y, 0.6, obs, None)
    print("%s via (%.2f,%.2f)" % ("ok " if ok else "BAD", x, y))
    bad += not ok
# vias vs our own new segments on other layers are fine (same net); vias vs each other:
for i in range(len(vias)):
    for j in range(i + 1, len(vias)):
        d = math.hypot(vias[i][0]-vias[j][0], vias[i][1]-vias[j][1])
        if d < 0.75:
            print("BAD via-via %.2f" % d); bad += 1
if bad and not FORCE:
    raise SystemExit("%d problems - nothing saved" % bad)
for (a, b, layer) in segs:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(sp.mm(a[0]), sp.mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(sp.mm(b[0]), sp.mm(b[1])))
    t.SetWidth(sp.mm(W)); t.SetLayer(layer); t.SetNetCode(net.GetNetCode()); board.Add(t)
for (x, y) in vias:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y))); v.SetWidth(sp.mm(0.6)); v.SetDrill(sp.mm(0.3))
    v.SetNetCode(net.GetNetCode()); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v)
pcbnew.SaveBoard(str(BOARD), board)
print("%s: %d segments, %d vias added" % (NET, len(segs), len(vias)))
