r"""Third stitching pass: rescue GND pads that KiCad says are not grounded.

Pass 2 tries to drop a via INSIDE an isolated pour island, which fails whenever
the island is a narrow sliver hemmed in by other-net copper - it reported 16
such islands, and 12 GND pads were left floating, including U2 (the 3V3 LDO)
and U9 (the DAC). A board like that is dead on arrival.

This pass does not depend on the island at all. For each orphaned GND pad it
finds the nearest legal spot for a through via and runs a short track from the
pad to it. In1.Cu is a solid GND plane, so the via alone ties that pad into the
whole ground system.

Two things make it succeed where pass 2 could not:
  * real pad geometry. Pass 2 approximated every pad as a circle of radius
    max(w,h)/2, which for a 0603 pad or a fine-pitch QFN lead overstates the
    obstacle badly and hides legal spots.
  * it searches outward from the pad rather than only within the island.

Run after import_route/cleanup_board, then re-check with gnd_cluster_check.py.
"""
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"

VIA_SIZES = ((0.80, 0.40), (0.60, 0.30))   # board minimum is 0.60/0.30
CLEARANCE = 0.18        # netclass minimum is 0.15; keep a little margin
TRACK_W = 0.30
EDGE_KEEP = 0.60        # from the board outline
MAX_REACH = 6.0         # how far from the pad we are willing to go
GND_NAMES = ("GND", "/GND")


def to_mm(v):
    return pcbnew.ToMM(v)


def mm(v):
    return pcbnew.FromMM(v)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _side(ax, ay, bx, by, px, py):
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def segs_cross(a, b, c, d):
    """True if segments ab and cd properly intersect."""
    d1 = _side(c[0], c[1], d[0], d[1], a[0], a[1])
    d2 = _side(c[0], c[1], d[0], d[1], b[0], b[1])
    d3 = _side(a[0], a[1], b[0], b[1], c[0], c[1])
    d4 = _side(a[0], a[1], b[0], b[1], d[0], d[1])
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def seg_seg_dist(a, b, c, d):
    """Minimum distance between segments ab and cd.

    The endpoint-only version of this is WRONG for crossing segments: two
    tracks can meet in an X with all four endpoints far from the other line.
    That bug put GND tracks straight through I2C_SDA and VBUS_SENSE, so test
    for intersection first.
    """
    if segs_cross(a, b, c, d):
        return 0.0
    return min(seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]),
               seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]),
               seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))


def rect_dist(px, py, cx, cy, hw, hh):
    """Distance from a point to an axis-aligned rectangle, 0 if inside."""
    dx = max(abs(px - cx) - hw, 0.0)
    dy = max(abs(py - cy) - hh, 0.0)
    return math.hypot(dx, dy)


def orphan_pads(board):
    """GND pads KiCad's connectivity does not join to the main GND cluster."""
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    gndcode = board.FindNet("GND").GetNetCode()

    pads = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetNetCode() == gndcode:
                pads.append((fp.GetReference() + "." + p.GetNumber(), p))

    parent = {name: name for name, _ in pads}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    index = {p.m_Uuid.AsString(): name for name, p in pads}
    for name, p in pads:
        for item in conn.GetConnectedItems(p, 0):
            other = index.get(item.m_Uuid.AsString())
            if other is not None:
                a, b = find(name), find(other)
                if a != b:
                    parent[a] = b

    groups = {}
    for name, p in pads:
        groups.setdefault(find(name), []).append((name, p))
    ordered = sorted(groups.values(), key=len, reverse=True)
    return [entry for g in ordered[1:] for entry in g]


def build_obstacles(board):
    """Everything a GND via or GND track must keep away from.

    Same-net (GND) copper is deliberately NOT an obstacle - touching it is the
    whole point - except other vias, which must not physically collide.
    """
    pads, segs, vias, edges = [], [], [], []
    for fp in board.Footprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            cx = to_mm(bb.GetCenter().x)
            cy = to_mm(bb.GetCenter().y)
            hw = to_mm(bb.GetWidth()) / 2.0
            hh = to_mm(bb.GetHeight()) / 2.0
            same = p.GetNetname() in GND_NAMES
            on = tuple(l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l))
            pads.append((cx, cy, hw, hh, same, p.m_Uuid.AsString(), on))
    for t in board.GetTracks():
        same = t.GetNetname() in GND_NAMES
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            # KiCad 10 vias carry a per-layer width, so GetWidth() needs a
            # layer; older signatures do not accept one.
            try:
                w = t.GetWidth(pcbnew.F_Cu)
            except Exception:
                w = t.GetWidth()
            vias.append((to_mm(pos.x), to_mm(pos.y), to_mm(w) / 2.0, same))
            continue
        if same:
            continue
        s, e = t.GetStart(), t.GetEnd()
        segs.append((to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y),
                     to_mm(t.GetWidth()) / 2.0, t.GetLayer()))
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        try:
            s, e = d.GetStart(), d.GetEnd()
        except Exception:
            continue
        edges.append((to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y)))
    holes = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetDrillSizeX() > 0:
                pos = p.GetPosition()
                holes.append((to_mm(pos.x), to_mm(pos.y),
                              to_mm(p.GetDrillSizeX()) / 2.0,
                              p.GetNetname() in GND_NAMES))
    rule_areas = [z for z in board.Zones()
                  if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    return pads, segs, vias, edges, holes, rule_areas


def via_is_legal(x, y, dia, obs, skip_uuid):
    pads, segs, vias, edges, holes, rule_areas = obs
    r = dia / 2.0
    # a through via passes every layer, so pads on BOTH sides matter here
    for cx, cy, hw, hh, same, uuid, _on in pads:
        if uuid == skip_uuid:
            continue
        need = r + CLEARANCE if not same else r + 0.05
        if rect_dist(x, y, cx, cy, hw, hh) < need:
            return False
    for ax, ay, bx, by, hw, _layer in segs:
        if seg_dist(x, y, ax, ay, bx, by) < r + hw + CLEARANCE:
            return False
    for vx, vy, vr, _same in vias:
        # even a same-net via still needs physical separation
        if math.hypot(x - vx, y - vy) < r + vr + 0.16:   # DRC via-via clearance is 0.15
            return False
    for ax, ay, bx, by in edges:
        if seg_dist(x, y, ax, ay, bx, by) < r + EDGE_KEEP:
            return False
    for hx, hy, hr, same in holes:
        if math.hypot(x - hx, y - hy) < r + hr + (0.05 if same else CLEARANCE):
            return False
    pt = pcbnew.VECTOR2I(mm(x), mm(y))
    for z in rule_areas:
        if z.Outline().Contains(pt):
            return False
    return True


def track_is_legal(ax, ay, bx, by, layer, obs, skip_uuid, new_via=None):
    pads, segs, vias, edges, holes, rule_areas = obs
    hw = TRACK_W / 2.0
    a, b = (ax, ay), (bx, by)
    # A track only shares copper with pads ON ITS OWN LAYER. Checking against
    # every pad on the board made bottom-side parts block top-side tracks and
    # vice versa, which on a two-sided board rejects nearly every path.
    for cx, cy, phw, phh, same, uuid, on in pads:
        if uuid == skip_uuid or same or layer not in on:
            continue
        # sample the segment against the pad rectangle
        steps = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
        for i in range(steps + 1):
            t = i / steps
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            if rect_dist(px, py, cx, cy, phw, phh) < hw + CLEARANCE:
                return False
    for sx, sy, ex, ey, shw, slayer in segs:
        if slayer != layer:
            continue
        if seg_seg_dist(a, b, (sx, sy), (ex, ey)) < hw + shw + CLEARANCE:
            return False
    # Vias are through-hole, so an other-net via blocks a track on every
    # layer. A GND via does NOT: this is a GND track, and running over one is
    # a connection, not a violation. Treating all 200-odd GND stitching vias
    # as obstacles is what made every candidate path look blocked.
    for vx, vy, vr, same in vias:
        if same:
            continue
        if new_via and abs(vx - new_via[0]) < 1e-6 and abs(vy - new_via[1]) < 1e-6:
            continue
        if seg_dist(vx, vy, ax, ay, bx, by) < hw + vr + CLEARANCE:
            return False
    for hx, hy, hr, same in holes:
        if same:
            continue
        if seg_dist(hx, hy, ax, ay, bx, by) < hw + hr + CLEARANCE:
            return False
    for ax2, ay2, bx2, by2 in edges:
        if seg_seg_dist(a, b, (ax2, ay2), (bx2, by2)) < hw + EDGE_KEEP:
            return False
    return True


def pad_layers(pad):
    """Copper layers this pad can be routed away from, best first.

    Getting this wrong is what broke the first attempt: an SMD pad on a
    bottom-side part must be escaped on B.Cu, and a track drawn on F.Cu
    instead simply does not touch it.
    """
    out = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(l)]
    if not out:
        out = [pcbnew.F_Cu]
    # An SMD pad yields exactly one layer, which settles it. A through pad
    # yields both, and either is legal, so start on the pad's primary layer -
    # the side its footprint is mounted on.
    primary = pad.GetLayer()
    out.sort(key=lambda l: 0 if l == primary else 1)
    return out


def rescue(board, name, pad, obs, gndcode):
    """Place a via near this pad and run a short track to it."""
    pos = pad.GetPosition()
    px, py = to_mm(pos.x), to_mm(pos.y)
    skip = pad.m_Uuid.AsString()

    bb = pad.GetBoundingBox()
    start_r = max(to_mm(bb.GetWidth()), to_mm(bb.GetHeight())) / 2.0 + 0.25

    def paths(x, y):
        """Ways to get from the pad to (x, y): straight, then two dog-legs.

        A straight shot fails a lot in the congested bottom-side cluster
        around U2 and the C41-45 column, but a single bend usually slips
        between the same obstacles.
        """
        yield [(px, py), (x, y)]
        yield [(px, py), (x, py), (x, y)]
        yield [(px, py), (px, y), (x, y)]

    for layer in pad_layers(pad):
        r = start_r
        while r <= start_r + MAX_REACH:
            for deg in range(0, 360, 5):
                a = math.radians(deg)
                x, y = px + r * math.cos(a), py + r * math.sin(a)
                for dia, drill in VIA_SIZES:
                    if not via_is_legal(x, y, dia, obs, skip):
                        continue
                    route = None
                    for pts in paths(x, y):
                        if all(track_is_legal(pts[i][0], pts[i][1],
                                              pts[i + 1][0], pts[i + 1][1],
                                              layer, obs, skip, new_via=(x, y))
                               for i in range(len(pts) - 1)):
                            route = pts
                            break
                    if route is None:
                        continue

                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                    via.SetWidth(mm(dia))
                    via.SetDrill(mm(drill))
                    via.SetNetCode(gndcode)
                    via.SetViaType(pcbnew.VIATYPE_THROUGH)
                    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    board.Add(via)

                    for i in range(len(route) - 1):
                        trk = pcbnew.PCB_TRACK(board)
                        trk.SetStart(pcbnew.VECTOR2I(mm(route[i][0]),
                                                     mm(route[i][1])))
                        trk.SetEnd(pcbnew.VECTOR2I(mm(route[i + 1][0]),
                                                   mm(route[i + 1][1])))
                        trk.SetWidth(mm(TRACK_W))
                        trk.SetLayer(layer)
                        trk.SetNetCode(gndcode)
                        board.Add(trk)
                    return (x, y, dia, r, board.GetLayerName(layer),
                            len(route) - 1)
            r += 0.1
    return None


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    gndcode = board.FindNet("GND").GetNetCode()

    targets = orphan_pads(board)
    print("GND pads KiCad reports as not grounded: %d" % len(targets))
    for name, _p in targets:
        print("   %s" % name)

    if not targets:
        print("nothing to do")
        return

    obs = build_obstacles(board)
    fixed, failed = [], []
    for name, pad in targets:
        result = rescue(board, name, pad, obs, gndcode)
        if result is None:
            failed.append(name)
            print("  FAILED  %-10s no legal via spot within %.1f mm"
                  % (name, MAX_REACH))
        else:
            x, y, dia, r, lay, segn = result
            fixed.append(name)
            print("  fixed   %-10s via %.2f mm at (%.2f, %.2f), %.2f mm away "
                  "on %s (%d segment%s)"
                  % (name, dia, x, y, r, lay, segn, "" if segn == 1 else "s"))
        # rebuild obstacles so the next pad sees what we just added
        obs = build_obstacles(board)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print("\nfixed %d, failed %d" % (len(fixed), len(failed)))
    if failed:
        print("still floating: %s" % ", ".join(failed))
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
