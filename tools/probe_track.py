"""Say exactly which check rejects each candidate escape track for one pad."""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
import stitch_pass4 as p4

REF = sys.argv[1] if len(sys.argv) > 1 else "C41.2"

board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
gndcode = board.FindNet("GND").GetNetCode()
obs = sp.build_obstacles(board)
pads_o, segs, vias, edges, holes, rule_areas = obs
main_set, uuids = p4.main_cluster_items(board, gndcode)

pad = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() + "." + p.GetNumber() == REF:
            pad = p
pos = pad.GetPosition()
px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
skip = pad.m_Uuid.AsString()
layer = sp.pad_layers(pad)[0]
print("%s at (%.3f, %.3f) escaping on %s"
      % (REF, px, py, board.GetLayerName(layer)))

cands = p4.pour_targets(board, main_set, uuids, layer, px, py, gndcode, 8.0)
cands.sort(key=lambda c: math.hypot(c[0] - px, c[1] - py))
print("pour targets: %d, nearest %.2f mm"
      % (len(cands), math.hypot(cands[0][0] - px, cands[0][1] - py)
         if cands else -1))

hw = sp.TRACK_W / 2.0


def explain(ax, ay, bx, by):
    a, b = (ax, ay), (bx, by)
    worst = []
    for cx, cy, phw, phh, same, uuid, on in pads_o:
        if uuid == skip or same or layer not in on:
            continue
        steps = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
        m = min(sp.rect_dist(ax + (bx - ax) * i / steps,
                             ay + (by - ay) * i / steps, cx, cy, phw, phh)
                for i in range(steps + 1))
        if m < hw + sp.CLEARANCE:
            worst.append(("pad @(%.2f,%.2f) gap %.3f" % (cx, cy, m)))
    for sx, sy, ex, ey, shw, slayer in segs:
        if slayer != layer:
            continue
        d = sp.seg_seg_dist(a, b, (sx, sy), (ex, ey))
        if d < hw + shw + sp.CLEARANCE:
            worst.append("track @(%.2f,%.2f) gap %.3f" % (sx, sy, d))
    for vx, vy, vr, vsame in vias:
        if vsame:
            continue
        d = sp.seg_dist(vx, vy, ax, ay, bx, by)
        if d < hw + vr + sp.CLEARANCE:
            worst.append("via @(%.2f,%.2f) gap %.3f" % (vx, vy, d))
    for hx, hy, hr, hsame in holes:
        if hsame:
            continue
        d = sp.seg_dist(hx, hy, ax, ay, bx, by)
        if d < hw + hr + sp.CLEARANCE:
            worst.append("hole @(%.2f,%.2f) gap %.3f" % (hx, hy, d))
    for ax2, ay2, bx2, by2 in edges:
        d = sp.seg_seg_dist(a, b, (ax2, ay2), (bx2, by2))
        if d < hw + sp.EDGE_KEEP:
            worst.append("edge gap %.3f" % d)
    return worst


for tx, ty, kind in cands[:8]:
    d = math.hypot(tx - px, ty - py)
    print("\n target %s (%.3f, %.3f) at %.2f mm" % (kind, tx, ty, d))
    for label, pts in (("straight", [(px, py), (tx, ty)]),
                       ("bend-x", [(px, py), (tx, py), (tx, ty)]),
                       ("bend-y", [(px, py), (px, ty), (tx, ty)])):
        reasons = []
        for i in range(len(pts) - 1):
            reasons += explain(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        if reasons:
            print("   %-8s blocked by %d: %s"
                  % (label, len(reasons), "; ".join(reasons[:3])))
        else:
            print("   %-8s LEGAL" % label)
