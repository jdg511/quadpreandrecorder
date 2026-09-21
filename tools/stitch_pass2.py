r"""Second stitching pass: give every remaining isolated GND island a via.

Pass 1 (add_gnd_stitching.py) only places a via where the GND fill overlaps on
F, In2 and B at once, which is safe but cannot reach islands that sit alone on
one layer. This pass works island by island and checks clearance directly
against real copper, so it can serve those.

In1.Cu is a solid GND plane, so ANY via landing on a piece of GND copper ties
that piece back into the whole ground system. One via per island is enough.
"""

from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"

VIA_DIA = 0.80
VIA_DRILL = 0.40
CLEARANCE = 0.25
STEP = 0.25
CELL = 6.0
GND_NAMES = ("GND", "/GND")


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    gnd = board.FindNet("GND") or board.FindNet("/GND")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    # ---- obstacles: anything a through via must stay away from
    obstacles = []          # (x, y, required_centre_distance)
    for track in board.GetTracks():
        net = track.GetNetname()
        if track.Type() == pcbnew.PCB_VIA_T:
            p = track.GetPosition()
            obstacles.append((to_mm(p.x), to_mm(p.y), VIA_DIA + CLEARANCE, None, None))
            continue
        if net in GND_NAMES:
            continue
        s, e = track.GetStart(), track.GetEnd()
        need = VIA_DIA / 2.0 + to_mm(track.GetWidth()) / 2.0 + CLEARANCE
        obstacles.append((to_mm(s.x), to_mm(s.y), need, to_mm(e.x), to_mm(e.y)))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            cx, cy = to_mm(bb.GetCenter().x), to_mm(bb.GetCenter().y)
            r = max(to_mm(bb.GetWidth()), to_mm(bb.GetHeight())) / 2.0
            obstacles.append((cx, cy, r + VIA_DIA / 2.0 + CLEARANCE, None, None))

    grid = {}
    for ob in obstacles:
        x, y = ob[0], ob[1]
        xs = [x] if ob[3] is None else [x, ob[3]]
        ys = [y] if ob[4] is None else [y, ob[4]]
        for gx in range(int(min(xs) // CELL) - 1, int(max(xs) // CELL) + 2):
            for gy in range(int(min(ys) // CELL) - 1, int(max(ys) // CELL) + 2):
                grid.setdefault((gx, gy), []).append(ob)

    rule_areas = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]

    def clear(x, y):
        for gx in (int(x // CELL) - 1, int(x // CELL), int(x // CELL) + 1):
            for gy in (int(y // CELL) - 1, int(y // CELL), int(y // CELL) + 1):
                for ob in grid.get((gx, gy), ()):
                    if ob[3] is None:
                        if ((x - ob[0]) ** 2 + (y - ob[1]) ** 2) ** 0.5 < ob[2]:
                            return False
                    elif seg_dist(x, y, ob[0], ob[1], ob[3], ob[4]) < ob[2]:
                        return False
        for z in rule_areas:
            if z.Outline().Contains(pcbnew.VECTOR2I(mm(x), mm(y))):
                return False
        return True

    existing = [(to_mm(t.GetPosition().x), to_mm(t.GetPosition().y))
                for t in board.GetTracks()
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() in GND_NAMES]

    added = 0
    served = 0
    skipped = 0
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu):
        for zone in board.Zones():
            if zone.GetIsRuleArea() or not zone.IsOnLayer(layer):
                continue
            polys = zone.GetFilledPolysList(layer)
            for i in range(polys.OutlineCount()):
                island = pcbnew.SHAPE_POLY_SET()
                island.AddOutline(polys.Outline(i))
                if any(island.Contains(pcbnew.VECTOR2I(mm(vx), mm(vy))) for vx, vy in existing):
                    served += 1
                    continue
                bb = island.BBox()
                x0, y0 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
                x1, y1 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
                spot = None
                dia = VIA_DIA
                for try_dia in (VIA_DIA, 0.60):
                    margin = try_dia / 2.0 + 0.05
                    x = x0
                    while x <= x1 and spot is None:
                        y = y0
                        while y <= y1:
                            if island.Contains(pcbnew.VECTOR2I(mm(x), mm(y))) and clear(x, y):
                                ok = all(island.Contains(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
                                         for dx, dy in ((margin, 0), (-margin, 0),
                                                        (0, margin), (0, -margin)))
                                if ok:
                                    spot = (x, y)
                                    dia = try_dia
                                    break
                            y += STEP
                        x += STEP
                    if spot is not None:
                        break
                if spot is None:
                    skipped += 1
                    continue
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(mm(spot[0]), mm(spot[1])))
                via.SetWidth(mm(dia))
                via.SetDrill(mm(VIA_DRILL if dia >= 0.8 else 0.30))
                via.SetNet(gnd)
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                board.Add(via)
                existing.append(spot)
                added += 1

    print(f"  islands already served: {served}")
    print(f"  pass-2 vias added     : {added}")
    print(f"  islands with no room  : {skipped}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
