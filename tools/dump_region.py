"""Dump every copper item (pads, tracks, vias) inside a box.
usage: dump_region.py x0 y0 x1 y1 [netfilter]
"""
import sys
from pathlib import Path
import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

x0, y0, x1, y1 = [float(v) for v in sys.argv[1:5]]
flt = sys.argv[5] if len(sys.argv) > 5 else None
board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
mm = lambda v: v / 1e6

def inside(x, y):
    return x0 <= x <= x1 and y0 <= y <= y1

print("--- pads ---")
for fp in board.Footprints():
    for p in fp.Pads():
        px, py = mm(p.GetPosition().x), mm(p.GetPosition().y)
        if not inside(px, py):
            continue
        net = p.GetNetname()
        if flt and flt not in net:
            continue
        sz = p.GetSize()
        layers = [board.GetLayerName(l) for l in sp.pad_layers(p)]
        print("  %-8s %-3s %-14s (%.3f,%.3f) %.2fx%.2f %s"
              % (fp.GetReference(), p.GetNumber(), net, px, py,
                 mm(sz.x), mm(sz.y), "/".join(layers)))
print("--- tracks ---")
for t in board.Tracks():
    net = t.GetNetname()
    if flt and flt not in net:
        continue
    if t.GetClass() == "PCB_VIA":
        vx, vy = mm(t.GetPosition().x), mm(t.GetPosition().y)
        if inside(vx, vy):
            print("  VIA  %-14s (%.3f,%.3f) d%.2f" % (net, vx, vy, mm(t.GetWidth(pcbnew.F_Cu))))
        continue
    sx, sy = mm(t.GetStart().x), mm(t.GetStart().y)
    ex, ey = mm(t.GetEnd().x), mm(t.GetEnd().y)
    bx0, bx1 = min(sx, ex), max(sx, ex)
    by0, by1 = min(sy, ey), max(sy, ey)
    if bx1 >= x0 and bx0 <= x1 and by1 >= y0 and by0 <= y1:
        print("  %-5s %-14s (%.3f,%.3f)-(%.3f,%.3f) w%.2f"
              % (board.GetLayerName(t.GetLayer()), net, sx, sy, ex, ey,
                 mm(t.GetWidth())))
