"""How far can a wall connector be pushed toward its board edge?

The limit is its own pads: a through-hole tab needs annular ring plus edge
clearance, an SMD pad just needs to stay on copper. Report the binding pad
and the resulting mating-face position for each wall connector.
"""
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
BOARD_W, BOARD_H = 138.0, 114.0
EDGE_COPPER = 0.30      # copper to board edge, per the design rules

# ref, which edge it faces, current mating-face position in board coords
TARGETS = [
    ("J9", "rear",  0.55),
    ("J5", "right", 139.20),
    ("J1", "rear", -5.50),
    ("J2", "left",  -4.25),
    ("J4", "front", 122.90),
]


def mm(v):
    return pcbnew.ToMM(v)


board = pcbnew.LoadBoard(PCB)
byref = {f.GetReference(): f for f in board.Footprints()}

# board edge -> outer wall face, at the chosen board height
GAP_TO_WALL = 1.0
WALL = 2.6
print("board edge to inner wall face %.2f mm, to outer wall face %.2f mm\n"
      % (GAP_TO_WALL, GAP_TO_WALL + WALL))

for ref, edge, face in TARGETS:
    fp = byref.get(ref)
    if fp is None:
        continue
    print("=== %s  (%s wall)" % (ref, edge))
    limit = None
    binding = None
    for pad in fp.Pads():
        p = pad.GetPosition()
        px, py = mm(p.x), mm(p.y)
        bb = pad.GetBoundingBox()
        half_x = (mm(bb.GetRight()) - mm(bb.GetLeft())) / 2.0
        half_y = (mm(bb.GetBottom()) - mm(bb.GetTop())) / 2.0
        if edge == "rear":
            room = py - half_y - EDGE_COPPER            # can move -y by this
        elif edge == "front":
            room = (BOARD_H - (py + half_y)) - EDGE_COPPER
        elif edge == "left":
            room = px - half_x - EDGE_COPPER
        else:
            room = (BOARD_W - (px + half_x)) - EDGE_COPPER
        if limit is None or room < limit:
            limit = room
            binding = "%s at (%.2f, %.2f) size %.2f x %.2f, drill %.2f" % (
                pad.GetNumber(), px, py, half_x * 2, half_y * 2,
                mm(pad.GetDrillSizeX()))
    print("    binding pad: %s" % binding)
    print("    max outward move: %.2f mm" % limit)

    # where the mating face ends up
    if edge == "rear":
        newface = face - limit
        out = -(newface) + GAP_TO_WALL + WALL
    elif edge == "front":
        newface = face + limit
        out = (newface - BOARD_H) - (GAP_TO_WALL + WALL)
        out = -out
    elif edge == "left":
        newface = face - limit
        out = -(newface) + GAP_TO_WALL + WALL
    else:
        newface = face + limit
        out = (BOARD_W - newface) + GAP_TO_WALL + WALL
    print("    mating face would move to %.2f, leaving it %.2f mm behind the "
          "outer wall face" % (newface, out))
    print()
