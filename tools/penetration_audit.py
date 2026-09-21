"""Report the real board geometry of every part that goes through the enclosure.

The enclosure study carries hand-entered X positions, some of which predate
later moves (J4 went from x=22 to x=26 in Rev C2). Read the placed board
instead so every number traces to the file that will be manufactured.

Prints, per part: anchor, rotation, side, courtyard and pad extents, and the
distance from each board edge - which is what a wall cutout is measured from.
"""
import math

import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
BOARD_W, BOARD_H = 138.0, 114.0

# Everything that penetrates a wall or the lid, and which wall it serves.
WALL = {
    "J1": "REAR  (y=0)    9V barrel",
    "J9": "REAR  (y=0)    USB-C",
    "U8": "REAR  (y=0)    Teensy microSD slot",
    "J2": "LEFT  (x=0)    RJ45 mic in",
    "J5": "RIGHT (x=138)  3.5mm headphones",
    "J4": "FRONT (y=114)  1/4in line out",
    "SW2": "LID           record button",
    "SW3": "LID           gain encoder",
    "SW4": "LID           5-way nav encoder",
    "J3": "LID           TFT module socket",
    "D4": "LID/FRONT     LED",
    "D5": "LID/FRONT     LED",
}


def mm(v):
    return pcbnew.ToMM(v)


def rot(x, y, deg):
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a),
            -x * math.sin(a) + y * math.cos(a))


board = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in board.Footprints()}

print("board %.1f x %.1f mm\n" % (BOARD_W, BOARD_H))
for ref in WALL:
    fp = fps.get(ref)
    if fp is None:
        print("%-4s NOT ON THE BOARD" % ref)
        continue
    pos = fp.GetPosition()
    ax, ay = mm(pos.x), mm(pos.y)
    ang = fp.GetOrientationDegrees()
    side = "BOTTOM" if fp.IsFlipped() else "TOP"

    # courtyard extent, falling back to the fab layer
    xs, ys = [], []
    for layername in ("F.CrtYd", "B.CrtYd", "F.Fab", "B.Fab"):
        lay = board.GetLayerID(layername)
        for item in fp.GraphicalItems():
            if item.GetLayer() != lay:
                continue
            for p in (item.GetStart(), item.GetEnd()):
                xs.append(mm(p.x))
                ys.append(mm(p.y))
        if xs:
            break

    pxs, pys = [], []
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        pxs += [mm(bb.GetLeft()), mm(bb.GetRight())]
        pys += [mm(bb.GetTop()), mm(bb.GetBottom())]

    allx = (xs or []) + pxs
    ally = (ys or []) + pys
    x0, x1 = min(allx), max(allx)
    y0, y1 = min(ally), max(ally)

    print("%-4s %-30s  anchor (%7.2f, %7.2f)  rot %5.1f  %s"
          % (ref, WALL[ref], ax, ay, ang, side))
    print("      extent  x %7.2f .. %7.2f   y %7.2f .. %7.2f  (%.2f x %.2f mm)"
          % (x0, x1, y0, y1, x1 - x0, y1 - y0))
    print("      to edges: rear %6.2f  front %6.2f  left %6.2f  right %6.2f"
          % (y0, BOARD_H - y1, x0, BOARD_W - x1))
    print()
