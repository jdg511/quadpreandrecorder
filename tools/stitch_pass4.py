"""Fourth pass: connect a stranded GND pad to existing ground copper.

Pass 3 always wants a NEW through via, and a through via has to clear copper
on all four layers at once. On this board that is the binding constraint: a
probe around C41.2 found 1,749 of 2,448 candidate spots blocked by tracks on
some layer, leaving 2 legal spots, neither reachable.

But a stranded pad does not need a new via. It needs to touch ground, and
there is already ground copper nearby: 200-odd GND vias (through, so usable
from either side) and the GND tracks Freerouting laid down. Running a short
track to one of those only has to clear copper on ONE layer, which is a far
easier problem.

Run after stitch_pass3.py.
"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

BOARD_PATH = sp.BOARD_PATH
MAX_RUN = 8.0          # longest track we are willing to add, mm


def main_cluster_items(board, gndcode):
    """UUIDs of every GND item in the biggest connected group."""
    board.BuildConnectivity()
    conn = board.GetConnectivity()

    items = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetNetCode() == gndcode:
                items.append(p)
    for t in board.GetTracks():
        if t.GetNetCode() == gndcode:
            items.append(t)

    parent = {}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    uuids = {}
    for it in items:
        u = it.m_Uuid.AsString()
        uuids[u] = it
        parent[u] = u
    for it in items:
        u = it.m_Uuid.AsString()
        for other in conn.GetConnectedItems(it, 0):
            ou = other.m_Uuid.AsString()
            if ou in parent:
                a, b = find(u), find(ou)
                if a != b:
                    parent[a] = b

    groups = {}
    for u in parent:
        groups.setdefault(find(u), []).append(u)
    biggest = max(groups.values(), key=len)
    return set(biggest), uuids


def pour_targets(board, main, uuids, layer, px, py, gndcode, reach):
    """Points inside the main ground POUR on this layer, near (px, py).

    The pour is by far the biggest piece of ground copper and usually the
    closest, but it is a zone rather than a pad/via/track, so the first version
    of this pass never considered it and found almost nothing to aim at.
    """
    anchors = []
    for u in main:
        it = uuids[u]
        if it.Type() == pcbnew.PCB_VIA_T or it.IsOnLayer(layer):
            p = it.GetPosition()
            anchors.append(pcbnew.VECTOR2I(p.x, p.y))

    # Deflate each main polygon ONCE by the track half-width plus a margin,
    # so "is this point safely inside the pour" becomes a single Contains()
    # call. The first version probed four neighbours per grid point over an
    # 8 mm square and took minutes per pad.
    inset = int(sp.mm(sp.TRACK_W / 2.0 + 0.15))
    shrunk = []
    for zone in board.Zones():
        if zone.GetIsRuleArea() or zone.GetNetCode() != gndcode:
            continue
        if not zone.IsOnLayer(layer):
            continue
        try:
            pl = zone.GetFilledPolysList(layer)
        except Exception:
            continue
        for i in range(pl.OutlineCount()):
            shape = pcbnew.SHAPE_POLY_SET()
            shape.AddOutline(pl.Outline(i))
            bb = shape.BBox()
            if px < sp.to_mm(bb.GetLeft()) - reach:
                continue
            if px > sp.to_mm(bb.GetRight()) + reach:
                continue
            if py < sp.to_mm(bb.GetTop()) - reach:
                continue
            if py > sp.to_mm(bb.GetBottom()) + reach:
                continue
            if not any(shape.Collide(a) for a in anchors):
                continue        # this island is not the main ground
            small = pcbnew.SHAPE_POLY_SET(shape)
            # KiCad 10: Inflate(amount, cornerStrategy, maxError)
            small.Inflate(-inset, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,
                          int(sp.mm(0.005)))
            if small.OutlineCount():
                shrunk.append(small)

    out = []
    r = 0.4
    while r <= reach:
        for deg in range(0, 360, 10):
            a = math.radians(deg)
            gx, gy = px + r * math.cos(a), py + r * math.sin(a)
            pt = pcbnew.VECTOR2I(sp.mm(gx), sp.mm(gy))
            if any(s.Contains(pt) for s in shrunk):
                out.append((gx, gy, "pour"))
        if len(out) >= 40:
            break
        r += 0.25
    return out


def targets_for(board, main, uuids, layer):
    """Points on main-cluster ground copper that a track on `layer` can hit."""
    out = []
    for u in main:
        it = uuids[u]
        if it.Type() == pcbnew.PCB_VIA_T:
            p = it.GetPosition()
            out.append((sp.to_mm(p.x), sp.to_mm(p.y), "via"))
        elif it.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T):
            if it.GetLayer() != layer:
                continue
            for p in (it.GetStart(), it.GetEnd()):
                out.append((sp.to_mm(p.x), sp.to_mm(p.y), "track end"))
        else:   # pad
            if not it.IsOnLayer(layer):
                continue
            p = it.GetPosition()
            out.append((sp.to_mm(p.x), sp.to_mm(p.y), "pad"))
    return out


def connect(board, pad, obs, gndcode, main, uuids):
    pos = pad.GetPosition()
    px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
    skip = pad.m_Uuid.AsString()

    for layer in sp.pad_layers(pad):
        cands = targets_for(board, main, uuids, layer)
        cands += pour_targets(board, main, uuids, layer, px, py, gndcode,
                              MAX_RUN)
        cands.sort(key=lambda c: math.hypot(c[0] - px, c[1] - py))
        within = [c for c in cands
                  if math.hypot(c[0] - px, c[1] - py) <= MAX_RUN]
        print("      %s: %d main-cluster targets, %d within %.1f mm"
              % (board.GetLayerName(layer), len(cands), len(within), MAX_RUN))
        tried = 0
        for tx, ty, kind in cands:
            d = math.hypot(tx - px, ty - py)
            if d > MAX_RUN:
                print("      tried %d targets, all blocked" % tried)
                break
            tried += 1
            routes = ([(px, py), (tx, ty)],
                      [(px, py), (tx, py), (tx, ty)],
                      [(px, py), (px, ty), (tx, ty)])
            for pts in routes:
                if not all(sp.track_is_legal(pts[i][0], pts[i][1],
                                             pts[i + 1][0], pts[i + 1][1],
                                             layer, obs, skip,
                                             new_via=(tx, ty))
                           for i in range(len(pts) - 1)):
                    continue
                for i in range(len(pts) - 1):
                    trk = pcbnew.PCB_TRACK(board)
                    trk.SetStart(pcbnew.VECTOR2I(sp.mm(pts[i][0]),
                                                 sp.mm(pts[i][1])))
                    trk.SetEnd(pcbnew.VECTOR2I(sp.mm(pts[i + 1][0]),
                                               sp.mm(pts[i + 1][1])))
                    trk.SetWidth(sp.mm(sp.TRACK_W))
                    trk.SetLayer(layer)
                    trk.SetNetCode(gndcode)
                    board.Add(trk)
                return (tx, ty, kind, d, board.GetLayerName(layer),
                        len(pts) - 1)
    return None


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    gndcode = board.FindNet("GND").GetNetCode()

    targets = sp.orphan_pads(board)
    print("still-stranded GND pads: %d" % len(targets))
    if not targets:
        print("nothing to do")
        return

    obs = sp.build_obstacles(board)
    main_set, uuids = main_cluster_items(board, gndcode)
    print("main ground cluster holds %d copper items" % len(main_set))

    fixed, failed = [], []
    for name, pad in targets:
        res = connect(board, pad, obs, gndcode, main_set, uuids)
        if res is None:
            failed.append(name)
            print("  FAILED  %-8s nothing reachable within %.1f mm"
                  % (name, MAX_RUN))
        else:
            tx, ty, kind, d, lay, segn = res
            fixed.append(name)
            print("  fixed   %-8s -> GND %s at (%.2f, %.2f), %.2f mm on %s "
                  "(%d segment%s)"
                  % (name, kind, tx, ty, d, lay, segn,
                     "" if segn == 1 else "s"))
            obs = sp.build_obstacles(board)
            main_set, uuids = main_cluster_items(board, gndcode)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print("\nfixed %d, failed %d" % (len(fixed), len(failed)))
    if failed:
        print("still floating: %s" % ", ".join(failed))
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
