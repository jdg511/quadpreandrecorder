"""Why can't U10.12 (+5V) reach the rest of its net?"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
import connect_orphan_net as co

NET = "+5V"
board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
code = board.FindNet(NET).GetNetCode()
sp.GND_NAMES = (NET,)
sp.TRACK_W = 0.20
sp.CLEARANCE = 0.16
obs = sp.build_obstacles(board)
pads_o, segs, vias, edges, holes, rule_areas = obs

pad = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() == "U10" and p.GetNumber() == "12":
            pad, parent = p, fp
pos = pad.GetPosition()
px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
bb = pad.GetBoundingBox()
print("U10.12 at (%.3f, %.3f)  pad %.2f x %.2f  layer %s  U10 rot %.0f"
      % (px, py, sp.to_mm(bb.GetWidth()), sp.to_mm(bb.GetHeight()),
         board.GetLayerName(pad.GetLayer()), parent.GetOrientationDegrees()))

print("\nneighbours within 2.0 mm:")
near = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.m_Uuid.AsString() == pad.m_Uuid.AsString():
            continue
        q = p.GetPosition()
        d = math.hypot(sp.to_mm(q.x) - px, sp.to_mm(q.y) - py)
        if d <= 2.0:
            near.append((d, "pad %s.%s [%s]" % (fp.GetReference(),
                                                p.GetNumber(),
                                                p.GetNetname() or "-")))
for t in board.GetTracks():
    q = t.GetPosition()
    d = math.hypot(sp.to_mm(q.x) - px, sp.to_mm(q.y) - py)
    if d <= 2.0:
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "trk"
        near.append((d, "%s [%s] on %s" % (kind, t.GetNetname() or "-",
                                           board.GetLayerName(t.GetLayer()))))
near.sort()
for d, what in near[:16]:
    print("   %5.2f mm  %s" % (d, what))

print("\nlegal escape directions for a 0.20 mm track:")
ok = []
for deg in range(0, 360, 5):
    a = math.radians(deg)
    for reach in (0.8, 1.2, 1.8):
        x, y = px + reach * math.cos(a), py + reach * math.sin(a)
        if sp.track_is_legal(px, py, x, y, pcbnew.F_Cu, obs,
                             pad.m_Uuid.AsString()):
            ok.append(deg)
            break
print("   %d directions: %s" % (len(ok), ok))

groups, index = co.clusters(board, code)
for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu):
    cands = co.points_of(index, groups[0], layer)
    cands.sort(key=lambda c: math.hypot(c[0] - px, c[1] - py))
    if cands:
        print("   nearest main-cluster %s point: %.2f mm away at (%.2f, %.2f)"
              % (board.GetLayerName(layer),
                 math.hypot(cands[0][0] - px, cands[0][1] - py),
                 cands[0][0], cands[0][1]))
