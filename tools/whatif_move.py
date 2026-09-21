"""Test proposed mechanical moves without touching the board file.

For each proposed (ref, dx, dy) this reports what the footprint's courtyard
would then overlap on the same side, and whether its pads stay on the board.
Read-only: the board is loaded and thrown away.
"""
import math

import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
BOARD_W, BOARD_H = 138.0, 114.0
EDGE_KEEP = 0.3

# ref, dx, dy, why
MOVES = [
    ("J9", 0.0, -4.15, "USB-C face flush with the outer wall face"),
    ("J5", 2.40, 0.0, "3.5mm jack nose flush with the outer wall face"),
    ("J9", 0.0, -3.10, "USB-C face flush with the INNER wall face"),
]


def mm(v):
    return pcbnew.ToMM(v)


def extent(fp):
    xs, ys = [], []
    for layername in ("F.CrtYd", "B.CrtYd"):
        lay = board.GetLayerID(layername)
        for item in fp.GraphicalItems():
            if item.GetLayer() == lay:
                for p in (item.GetStart(), item.GetEnd()):
                    xs.append(mm(p.x))
                    ys.append(mm(p.y))
        if xs:
            break
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        xs += [mm(bb.GetLeft()), mm(bb.GetRight())]
        ys += [mm(bb.GetTop()), mm(bb.GetBottom())]
    return min(xs), max(xs), min(ys), max(ys)


board = pcbnew.LoadBoard(PCB)
fps = list(board.Footprints())
byref = {f.GetReference(): f for f in fps}

for ref, dx, dy, why in MOVES:
    fp = byref.get(ref)
    if fp is None:
        print("%s not on the board\n" % ref)
        continue
    x0, x1, y0, y1 = extent(fp)
    nx0, nx1, ny0, ny1 = x0 + dx, x1 + dx, y0 + dy, y1 + dy
    side = "B" if fp.IsFlipped() else "F"
    print("=== %s  move (%+.2f, %+.2f)  %s" % (ref, dx, dy, why))
    print("    courtyard now  x %7.2f..%7.2f  y %7.2f..%7.2f" % (x0, x1, y0, y1))
    print("    courtyard then x %7.2f..%7.2f  y %7.2f..%7.2f"
          % (nx0, nx1, ny0, ny1))

    # pads on board?
    off = []
    for pad in fp.Pads():
        p = pad.GetPosition()
        px, py = mm(p.x) + dx, mm(p.y) + dy
        if not (EDGE_KEEP <= px <= BOARD_W - EDGE_KEEP
                and EDGE_KEEP <= py <= BOARD_H - EDGE_KEEP):
            off.append("%s at (%.2f, %.2f)" % (pad.GetNumber(), px, py))
    print("    pads off the board: %s" % (", ".join(off) if off else "none"))

    hits = []
    for other in fps:
        if other is fp:
            continue
        if ("B" if other.IsFlipped() else "F") != side:
            continue
        ox0, ox1, oy0, oy1 = extent(other)
        if nx0 < ox1 and ox0 < nx1 and ny0 < oy1 and oy0 < ny1:
            ovx = min(nx1, ox1) - max(nx0, ox0)
            ovy = min(ny1, oy1) - max(ny0, oy0)
            hits.append("%s (%s) overlap %.2f x %.2f mm"
                        % (other.GetReference(), other.GetValue()[:16], ovx, ovy))
    print("    same-side collisions: %s"
          % ("; ".join(hits) if hits else "none"))

    # what copper is in the way of the shifted pads
    near = 0
    for t in board.GetTracks():
        p = t.GetPosition()
        tx, ty = mm(p.x), mm(p.y)
        if nx0 - 1 <= tx <= nx1 + 1 and ny0 - 1 <= ty <= ny1 + 1:
            near += 1
    print("    tracks/vias inside the new footprint area: %d (these re-route)"
          % near)
    print()
