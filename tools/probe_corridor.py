"""What exactly blocks U7.23's escape corridor to the nearest legal via?"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
NET = "I2C_SDA"
sp.GND_NAMES = (NET,)
sp.TRACK_W = 0.20
sp.CLEARANCE = 0.16
pads_o, segs, vias, edges, holes, rule_areas = sp.build_obstacles(board)

pad = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() == "U7" and p.GetNumber() == "23":
            pad = p
pos = pad.GetPosition()
px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
skip = pad.m_Uuid.AsString()
hw = sp.TRACK_W / 2.0
layer = pcbnew.F_Cu

TARGETS = [(84.67, 49.65), (84.31, 48.07), (84.15, 47.95)]

for tx, ty in TARGETS:
    print("\n=== corridor to (%.2f, %.2f), %.2f mm"
          % (tx, ty, math.hypot(tx - px, ty - py)))
    blockers = []
    for cx, cy, phw, phh, same, uuid, on in pads_o:
        if uuid == skip or same or layer not in on:
            continue
        steps = max(2, int(math.hypot(tx - px, ty - py) / 0.05))
        m = min(sp.rect_dist(px + (tx - px) * i / steps,
                             py + (ty - py) * i / steps, cx, cy, phw, phh)
                for i in range(steps + 1))
        if m < hw + sp.CLEARANCE:
            blockers.append(("pad at (%.2f,%.2f) gap %.3f need %.3f"
                             % (cx, cy, m, hw + sp.CLEARANCE)))
    for sx, sy, ex, ey, shw, slayer in segs:
        if slayer != layer:
            continue
        d = sp.seg_seg_dist((px, py), (tx, ty), (sx, sy), (ex, ey))
        if d < hw + shw + sp.CLEARANCE:
            blockers.append("track (%.2f,%.2f)-(%.2f,%.2f) w%.2f gap %.3f"
                            % (sx, sy, ex, ey, shw * 2, d))
    for vx, vy, vr, vsame in vias:
        if vsame:
            continue
        d = sp.seg_dist(vx, vy, px, py, tx, ty)
        if d < hw + vr + sp.CLEARANCE:
            blockers.append("VIA at (%.2f,%.2f) r%.2f gap %.3f need %.3f"
                            % (vx, vy, vr, d, hw + vr + sp.CLEARANCE))
    for hx, hy, hr, hsame in holes:
        if hsame:
            continue
        d = sp.seg_dist(hx, hy, px, py, tx, ty)
        if d < hw + hr + sp.CLEARANCE:
            blockers.append("hole at (%.2f,%.2f) gap %.3f" % (hx, hy, d))
    print("   blockers: %d" % len(blockers))
    for b in blockers:
        print("      " + b)
