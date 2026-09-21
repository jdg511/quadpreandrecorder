r"""Move one GND fanout via a fraction of a millimetre to free a signal escape.

U7.23 (I2C_SDA on the PCM1864) is a 0.30 mm pin whose only way out runs west.
A GND fanout via I placed at (85.09, 49.05) sits in that corridor with 0.558 mm
of room where 0.560 mm is needed - short by two microns. Rather than shave the
clearance rule down to win by a hair, move the via: it is a stub I added, and
the GND pad it serves has the pour and its neighbours as well.

    python tools/nudge_via.py 85.09 49.05 86.362 49.500 84.67 49.65
    (via x, via y, then the corridor the via must get out of)
"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

BOARD_PATH = sp.BOARD_PATH
VX, VY = float(sys.argv[1]), float(sys.argv[2])
AX, AY = float(sys.argv[3]), float(sys.argv[4])
BX, BY = float(sys.argv[5]), float(sys.argv[6])
NEED = 0.62        # clearance the corridor wants, with margin

board = pcbnew.LoadBoard(str(BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
gndcode = board.FindNet("GND").GetNetCode()

target, stubs = None, []
for t in board.GetTracks():
    if t.GetNetCode() != gndcode:
        continue
    p = t.GetPosition()
    if t.Type() == pcbnew.PCB_VIA_T:
        if math.hypot(sp.to_mm(p.x) - VX, sp.to_mm(p.y) - VY) < 0.05:
            target = t
if target is None:
    raise SystemExit("no GND via near (%.2f, %.2f)" % (VX, VY))

tp = target.GetPosition()
tx, ty = sp.to_mm(tp.x), sp.to_mm(tp.y)
for t in board.GetTracks():
    if t.GetNetCode() != gndcode or t.Type() == pcbnew.PCB_VIA_T:
        continue
    for which, p in (("start", t.GetStart()), ("end", t.GetEnd())):
        if math.hypot(sp.to_mm(p.x) - tx, sp.to_mm(p.y) - ty) < 0.02:
            stubs.append((t, which))
print("via at (%.3f, %.3f) with %d attached stub(s)" % (tx, ty, len(stubs)))
for t, which in stubs:
    s, e = t.GetStart(), t.GetEnd()
    print("   stub on %s: (%.2f,%.2f)-(%.2f,%.2f)"
          % (board.GetLayerName(t.GetLayer()), sp.to_mm(s.x), sp.to_mm(s.y),
             sp.to_mm(e.x), sp.to_mm(e.y)))

# the fixed end of each stub is the pad it serves
anchors = []
for t, which in stubs:
    p = t.GetEnd() if which == "start" else t.GetStart()
    anchors.append((sp.to_mm(p.x), sp.to_mm(p.y), t.GetLayer(), t, which))

# take the via out of the obstacle set while we look for its new home
board.Remove(target)
for t, _w in stubs:
    board.Remove(t)
obs = sp.build_obstacles(board)

best = None
r = 0.1
while r <= 1.6 and best is None:
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        nx, ny = tx + r * math.cos(a), ty + r * math.sin(a)
        if sp.seg_dist(nx, ny, AX, AY, BX, BY) < NEED:
            continue
        if not sp.via_is_legal(nx, ny, 0.60, obs, None):
            continue
        ok = True
        for ax, ay, layer, _t, _w in anchors:
            if math.hypot(nx - ax, ny - ay) > 3.0:
                ok = False
                break
            if not sp.track_is_legal(ax, ay, nx, ny, layer, obs, None,
                                     new_via=(nx, ny)):
                ok = False
                break
        if ok:
            best = (nx, ny, r)
            break
    r += 0.05

if best is None:
    raise SystemExit("no better spot found; leaving the board untouched")

nx, ny, moved = best
print("moving via to (%.3f, %.3f), %.2f mm away; corridor clearance now %.3f mm"
      % (nx, ny, moved, sp.seg_dist(nx, ny, AX, AY, BX, BY)))

via = pcbnew.PCB_VIA(board)
via.SetPosition(pcbnew.VECTOR2I(sp.mm(nx), sp.mm(ny)))
via.SetWidth(sp.mm(0.60))
via.SetDrill(sp.mm(0.30))
via.SetNetCode(gndcode)
via.SetViaType(pcbnew.VIATYPE_THROUGH)
via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
board.Add(via)

for ax, ay, layer, _t, _w in anchors:
    trk = pcbnew.PCB_TRACK(board)
    trk.SetStart(pcbnew.VECTOR2I(sp.mm(ax), sp.mm(ay)))
    trk.SetEnd(pcbnew.VECTOR2I(sp.mm(nx), sp.mm(ny)))
    trk.SetWidth(sp.mm(0.30))
    trk.SetLayer(layer)
    trk.SetNetCode(gndcode)
    board.Add(trk)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(BOARD_PATH), board)
print(BOARD_PATH)
