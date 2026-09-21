"""Explain, check by check, why stitch_pass3 rejects every spot around a pad."""
import math
import sys

import pcbnew
sys.path.insert(0, "tools")
import stitch_pass3 as sp

REF = sys.argv[1] if len(sys.argv) > 1 else "C41.2"

board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
obs = sp.build_obstacles(board)
pads_o, segs, vias, edges, holes, rule_areas = obs
print("obstacles: %d pads, %d track segs, %d vias, %d edge shapes, %d holes, "
      "%d via-keepout rule areas"
      % (len(pads_o), len(segs), len(vias), len(edges), len(holes),
         len(rule_areas)))

target = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() + "." + p.GetNumber() == REF:
            target = p
if target is None:
    raise SystemExit("pad %s not found" % REF)

pos = target.GetPosition()
px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
skip = target.m_Uuid.AsString()
print("%s at (%.3f, %.3f), layers %s"
      % (REF, px, py,
         [board.GetLayerName(l) for l in sp.pad_layers(target)]))

dia = 0.60
r = dia / 2.0
reasons = {}
best = []
for step in range(6, 40):
    rad = step * 0.1
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        x, y = px + rad * math.cos(a), py + rad * math.sin(a)
        why = None
        for cx, cy, hw, hh, same, uuid in pads_o:
            if uuid == skip:
                continue
            need = (r + sp.CLEARANCE) if not same else (r + 0.05)
            if sp.rect_dist(x, y, cx, cy, hw, hh) < need:
                why = "pad"
                break
        if why is None:
            for ax, ay, bx, by, hw, _l in segs:
                if sp.seg_dist(x, y, ax, ay, bx, by) < r + hw + sp.CLEARANCE:
                    why = "track"
                    break
        if why is None:
            for vx, vy, vr in vias:
                if math.hypot(x - vx, y - vy) < r + vr + 0.10:
                    why = "via"
                    break
        if why is None:
            for ax, ay, bx, by in edges:
                if sp.seg_dist(x, y, ax, ay, bx, by) < r + sp.EDGE_KEEP:
                    why = "edge shape"
                    break
        if why is None:
            for hx, hy, hr, same in holes:
                if math.hypot(x - hx, y - hy) < r + hr + (0.05 if same else sp.CLEARANCE):
                    why = "hole"
                    break
        if why is None:
            pt = pcbnew.VECTOR2I(sp.mm(x), sp.mm(y))
            for z in rule_areas:
                if z.Outline().Contains(pt):
                    why = "rule area"
                    break
        if why is None:
            best.append((rad, deg, x, y))
        reasons[why or "LEGAL"] = reasons.get(why or "LEGAL", 0) + 1

print("\nvia-spot verdicts over %d candidate points:" % sum(reasons.values()))
for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
    print("   %-12s %d" % (k, v))

if best:
    print("\nfirst 5 LEGAL via spots (0.60 mm):")
    for rad, deg, x, y in best[:5]:
        print("   r=%.2f deg=%3d  (%.3f, %.3f)" % (rad, deg, x, y))
    for layer in sp.pad_layers(target):
        ok = [b for b in best
              if sp.track_is_legal(px, py, b[2], b[3], layer, obs, skip,
                                   new_via=(b[2], b[3]))]
        print("   on %-5s: %d of %d reachable by a straight track"
              % (board.GetLayerName(layer), len(ok), len(best)))
else:
    print("\nno legal via spot at any radius - genuinely walled in")
