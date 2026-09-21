"""Where, if anywhere, can U7.23 escape to? Report each stage separately."""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
import connect_orphan_net as co

board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
NET = "I2C_SDA"
code = board.FindNet(NET).GetNetCode()
sp.GND_NAMES = (NET,)
sp.TRACK_W = 0.20
sp.CLEARANCE = 0.16
obs = sp.build_obstacles(board)

pad = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() == "U7" and p.GetNumber() == "23":
            pad = p
pos = pad.GetPosition()
px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
skip = pad.m_Uuid.AsString()

print("stage 1: can a 0.20 mm track leave the pad at all?")
ok_dirs = []
for deg in range(0, 360, 5):
    a = math.radians(deg)
    for reach in (1.0, 1.5, 2.0):
        x, y = px + reach * math.cos(a), py + reach * math.sin(a)
        if sp.track_is_legal(px, py, x, y, pcbnew.F_Cu, obs, skip):
            ok_dirs.append((deg, reach))
            break
print("   legal escape directions: %d -> %s"
      % (len(ok_dirs), [d for d, _ in ok_dirs][:20]))

print("\nstage 2: legal 0.60 mm via spots within 8 mm")
spots = []
r = 0.9
while r <= 8.0:
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        x, y = px + r * math.cos(a), py + r * math.sin(a)
        if sp.via_is_legal(x, y, 0.60, obs, skip):
            spots.append((r, deg, x, y))
    r += 0.2
print("   legal via spots: %d" % len(spots))
for r, deg, x, y in spots[:6]:
    print("      r=%.1f deg=%3d (%.2f, %.2f)" % (r, deg, x, y))

print("\nstage 3: pad -> via reachable?")
reach_ok = []
for r, deg, x, y in spots:
    if co.try_paths(px, py, x, y, pcbnew.F_Cu, obs, skip):
        reach_ok.append((r, deg, x, y))
print("   via spots reachable from the pad: %d" % len(reach_ok))
for r, deg, x, y in reach_ok[:6]:
    print("      r=%.1f deg=%3d (%.2f, %.2f)" % (r, deg, x, y))

print("\nstage 4: from those vias, can B.Cu reach the rest of the net?")
groups, index = co.clusters(board, code)
cands = co.points_of(index, groups[0], pcbnew.B_Cu)
print("   main-cluster B.Cu points: %d" % len(cands))
hits = 0
for r, deg, vx, vy in reach_ok[:40]:
    cs = sorted(cands, key=lambda c: math.hypot(c[0] - vx, c[1] - vy))
    for tx, ty, kind in cs[:25]:
        if co.try_paths(vx, vy, tx, ty, pcbnew.B_Cu, obs, skip):
            print("      via (%.2f, %.2f) -> %s (%.2f, %.2f)  %.2f mm"
                  % (vx, vy, kind, tx, ty, math.hypot(tx - vx, ty - vy)))
            hits += 1
            break
    if hits >= 5:
        break
if not hits:
    print("      none of the reachable vias can get to the net on B.Cu")
