"""Check every proposed mechanical fix against the real board. Read-only.

Each proposal is either a MOVE of an existing footprint or a SWAP to a
different footprint at a given anchor. For both we ask the same two
questions: does anything on the same side collide, and do the pads stay on
the board with edge clearance.
"""
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
FP_LIBS = [
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints\Button_Switch_THT.pretty",
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints\LED_THT.pretty",
]
BOARD_W, BOARD_H = 138.0, 114.0
EDGE_COPPER = 0.30

MOVES = [
    ("J4", 0.00, 1.00, "bushing shoulder onto the inner wall face, so the "
                       "nut clamps 2.6mm not 3.6mm"),
    ("J9", 0.00, -2.05, "USB-C as far out as its shield tabs allow"),
    ("J5", 2.40, 0.00, "3.5mm nose flush with the outer wall face"),
]

SWAPS = [
    # ref, new library footprint, anchor x, y, rot, why
    # SW_PUSH_6mm's origin is pad 1, not the plunger: the 4 pads sit on a
    # 6.5 x 4.5 grid, so the plunger is at anchor + (3.25, 2.25). To land the
    # plunger on the control row at (47, 73.5) the anchor goes to (43.75, 71.25).
    ("SW2", "SW_PUSH_6mm", 43.75, 71.25, 0.0,
     "6x6 tall-stem tact, plunger on the control-row line at (47, 73.5)"),
    ("D4", "LED_D3.0mm", 66.00, 106.00, 0.0, "3mm THT LED, moved 2mm rearward"),
    ("D5", "LED_D3.0mm", 76.00, 106.00, 0.0, "3mm THT LED, moved clear of C28"),
]


def mm(v):
    return pcbnew.ToMM(v)


board = pcbnew.LoadBoard(PCB)
fps = list(board.Footprints())
byref = {f.GetReference(): f for f in fps}


def extent(fp, dx=0.0, dy=0.0):
    xs, ys = [], []
    for name in ("F.CrtYd", "B.CrtYd"):
        lay = board.GetLayerID(name)
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
    return min(xs) + dx, max(xs) + dx, min(ys) + dy, max(ys) + dy


def collisions(x0, x1, y0, y1, side, skip_refs):
    out = []
    for other in fps:
        if other.GetReference() in skip_refs:
            continue
        if ("B" if other.IsFlipped() else "F") != side:
            continue
        ox0, ox1, oy0, oy1 = extent(other)
        if x0 < ox1 and ox0 < x1 and y0 < oy1 and oy0 < y1:
            out.append("%s (%s) by %.2f x %.2f mm"
                       % (other.GetReference(), other.GetValue()[:18],
                          min(x1, ox1) - max(x0, ox0),
                          min(y1, oy1) - max(y0, oy0)))
    return out


print("### PROPOSED MOVES\n")
for ref, dx, dy, why in MOVES:
    fp = byref.get(ref)
    if fp is None:
        continue
    side = "B" if fp.IsFlipped() else "F"
    x0, x1, y0, y1 = extent(fp, dx, dy)
    off = []
    for pad in fp.Pads():
        p = pad.GetPosition()
        bb = pad.GetBoundingBox()
        hx = (mm(bb.GetRight()) - mm(bb.GetLeft())) / 2.0
        hy = (mm(bb.GetBottom()) - mm(bb.GetTop())) / 2.0
        px, py = mm(p.x) + dx, mm(p.y) + dy
        if (px - hx < EDGE_COPPER or px + hx > BOARD_W - EDGE_COPPER
                or py - hy < EDGE_COPPER or py + hy > BOARD_H - EDGE_COPPER):
            off.append("%s(%.2f,%.2f)" % (pad.GetNumber(), px, py))
    hits = collisions(x0, x1, y0, y1, side, {ref})
    print("%-4s move (%+.2f, %+.2f)  -- %s" % (ref, dx, dy, why))
    print("     collides with : %s" % (", ".join(hits) if hits else "NOTHING"))
    print("     pads off board: %s" % (", ".join(off) if off else "none"))
    print()

print("\n### PROPOSED FOOTPRINT SWAPS\n")
for ref, fpname, ax, ay, rot, why in SWAPS:
    new = None
    for lib in FP_LIBS:
        try:
            new = pcbnew.FootprintLoad(lib, fpname)
        except Exception:
            new = None
        if new is not None:
            break
    if new is None:
        print("%-4s -> %s : FOOTPRINT NOT FOUND in the stock libraries\n"
              % (ref, fpname))
        continue
    old = byref.get(ref)
    side = "B" if (old is not None and old.IsFlipped()) else "F"
    new.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(ax), pcbnew.FromMM(ay)))
    x0, x1, y0, y1 = extent(new)
    hits = collisions(x0, x1, y0, y1, side, {ref})
    pads = [(p.GetNumber(), mm(p.GetPosition().x), mm(p.GetPosition().y),
             mm(p.GetDrillSizeX())) for p in new.Pads()]
    print("%-4s -> %s at (%.2f, %.2f)  -- %s" % (ref, fpname, ax, ay, why))
    print("     new extent    : x %.2f..%.2f  y %.2f..%.2f (%.2f x %.2f mm)"
          % (x0, x1, y0, y1, x1 - x0, y1 - y0))
    print("     pads          : %s"
          % ", ".join("%s(%.2f,%.2f d%.2f)" % p for p in pads))
    print("     collides with : %s" % (", ".join(hits) if hits else "NOTHING"))
    print()
