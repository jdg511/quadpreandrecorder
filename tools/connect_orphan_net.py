r"""Route the last stragglers on any net, not just GND.

The fanout re-route left exactly one connection unmade: U7 pad 23 (I2C_SDA on
the PCM1864) never reached the rest of its net. One missing signal is not
something to hand over, and it is the same problem stitch_pass3/4 already
solve for ground, so this reuses their geometry checks with the net name made
a parameter.

Unlike the GND passes this may need to change layers, so it will drop a via
mid-route and finish on the other side.

    python tools/connect_orphan_net.py I2C_SDA
"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

NET = sys.argv[1] if len(sys.argv) > 1 else "I2C_SDA"
BOARD_PATH = sp.BOARD_PATH
# U7.23 is a 0.30 mm-tall pin with neighbours 0.5 mm away on both sides, so
# the escape has to be thin and the via has to clear the whole fanout field.
TRACK_W = 0.20          # netclass minimum for signal
VIA = (0.60, 0.30)
MAX_RUN = 16.0
VIA_SEARCH = 8.0        # how far out to look for a layer-change via
# 2 degrees, not 5: U10.12 is a 0.25 mm-tall WQFN pad with 0.5 mm pitch
# neighbours and only TWO legal escape bearings, so a coarse sweep steps
# straight over the gap.
ANGLE_STEP = 2


def clusters(board, netcode):
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    items = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetNetCode() == netcode:
                items.append((fp.GetReference() + "." + p.GetNumber(), p))
    for t in board.GetTracks():
        if t.GetNetCode() == netcode:
            items.append(("track", t))

    parent = {}
    index = {}
    for name, it in items:
        u = it.m_Uuid.AsString()
        parent[u] = u
        index[u] = (name, it)

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for name, it in items:
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
    ordered = sorted(groups.values(), key=len, reverse=True)
    return ordered, index


def points_of(index, uuids, layer):
    out = []
    for u in uuids:
        name, it = index[u]
        if it.Type() == pcbnew.PCB_VIA_T:
            p = it.GetPosition()
            out.append((sp.to_mm(p.x), sp.to_mm(p.y), "via"))
        elif it.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T):
            if it.GetLayer() != layer:
                continue
            for p in (it.GetStart(), it.GetEnd()):
                out.append((sp.to_mm(p.x), sp.to_mm(p.y), "track end"))
        else:
            if not it.IsOnLayer(layer):
                continue
            p = it.GetPosition()
            out.append((sp.to_mm(p.x), sp.to_mm(p.y), name))
    return out


def add_track(board, netcode, layer, a, b):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(sp.mm(a[0]), sp.mm(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(sp.mm(b[0]), sp.mm(b[1])))
    t.SetWidth(sp.mm(TRACK_W))
    t.SetLayer(layer)
    t.SetNetCode(netcode)
    board.Add(t)


def add_via(board, netcode, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y)))
    v.SetWidth(sp.mm(VIA[0]))
    v.SetDrill(sp.mm(VIA[1]))
    v.SetNetCode(netcode)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)


def try_paths(px, py, tx, ty, layer, obs, skip):
    for pts in ([(px, py), (tx, ty)],
                [(px, py), (tx, py), (tx, ty)],
                [(px, py), (px, ty), (tx, ty)]):
        if all(sp.track_is_legal(pts[i][0], pts[i][1], pts[i + 1][0],
                                 pts[i + 1][1], layer, obs, skip,
                                 new_via=(tx, ty))
               for i in range(len(pts) - 1)):
            return pts
    return None


def try_paths_wide(px, py, tx, ty, layer, obs, skip):
    """try_paths plus a fan of single-waypoint detours.

    An 8 mm run across a dense bottom layer almost never happens to be clear
    in a straight line or one axis-aligned bend, but a dogleg through the
    right gap usually is.
    """
    direct = try_paths(px, py, tx, ty, layer, obs, skip)
    if direct:
        return direct
    mx, my = (px + tx) / 2.0, (py + ty) / 2.0
    for off in (0.8, 1.5, 2.5, 3.5, 5.0):
        for deg in range(0, 360, 15):
            a = math.radians(deg)
            wx, wy = mx + off * math.cos(a), my + off * math.sin(a)
            pts = [(px, py), (wx, wy), (tx, ty)]
            if all(sp.track_is_legal(pts[i][0], pts[i][1], pts[i + 1][0],
                                     pts[i + 1][1], layer, obs, skip,
                                     new_via=(tx, ty))
                   for i in range(len(pts) - 1)):
                return pts
    return None


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    net = board.FindNet(NET)
    if net is None:
        raise SystemExit("no net named %s" % NET)
    netcode = net.GetNetCode()

    # the geometry checks treat "same net" as free; point them at THIS net
    sp.GND_NAMES = (NET,)
    sp.TRACK_W = TRACK_W
    sp.CLEARANCE = 0.16     # board minimum is 0.15

    groups, index = clusters(board, netcode)
    print("%s: %d cluster(s); sizes %s"
          % (NET, len(groups), [len(g) for g in groups[:6]]))
    if len(groups) < 2:
        print("already fully connected - nothing to do")
        return

    obs = sp.build_obstacles(board)
    fixed = 0
    for orphan in groups[1:]:
        names = [index[u][0] for u in orphan if index[u][0] != "track"]
        label = ", ".join(names) or "track fragment"
        anchor = index[orphan[0]][1]
        pos = anchor.GetPosition()
        px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
        skip = anchor.m_Uuid.AsString()
        layers = (sp.pad_layers(anchor)
                  if anchor.Type() == pcbnew.PCB_PAD_T
                  else [anchor.GetLayer()])

        done = False
        # 1) same layer, straight or one bend
        for layer in layers:
            cands = points_of(index, groups[0], layer)
            cands.sort(key=lambda c: math.hypot(c[0] - px, c[1] - py))
            for tx, ty, kind in cands:
                if math.hypot(tx - px, ty - py) > MAX_RUN:
                    break
                pts = try_paths(px, py, tx, ty, layer, obs, skip)
                if pts:
                    for i in range(len(pts) - 1):
                        add_track(board, netcode, layer, pts[i], pts[i + 1])
                    print("  fixed %s -> %s on %s, %.2f mm"
                          % (label, kind, board.GetLayerName(layer),
                             math.hypot(tx - px, ty - py)))
                    done = True
                    break
            if done:
                break

        # 2) change layers: short hop, a via, then finish on the other side
        if not done:
            others = [pcbnew.B_Cu, pcbnew.F_Cu]   # Rev C3: In2.Cu is a plane now
            for layer, other in ((l, o) for l in layers for o in others
                                 if o != l):
                cands = points_of(index, groups[0], other)
                cands.sort(key=lambda c: math.hypot(c[0] - px, c[1] - py))
                if not cands:
                    continue
                r = 0.9
                while r <= VIA_SEARCH and not done:
                    for deg in range(0, 360, ANGLE_STEP):
                        a = math.radians(deg)
                        vx, vy = px + r * math.cos(a), py + r * math.sin(a)
                        if not sp.via_is_legal(vx, vy, VIA[0], obs, skip):
                            continue
                        first = try_paths_wide(px, py, vx, vy, layer, obs, skip)
                        if not first:
                            continue
                        for tx, ty, kind in cands[:12]:
                            if math.hypot(tx - vx, ty - vy) > MAX_RUN:
                                break
                            second = try_paths_wide(vx, vy, tx, ty, other,
                                                    obs, skip)
                            if not second:
                                continue
                            for i in range(len(first) - 1):
                                add_track(board, netcode, layer,
                                          first[i], first[i + 1])
                            add_via(board, netcode, vx, vy)
                            for i in range(len(second) - 1):
                                add_track(board, netcode, other,
                                          second[i], second[i + 1])
                            print("  fixed %s -> via at (%.2f, %.2f) -> %s on %s"
                                  % (label, vx, vy, kind,
                                     board.GetLayerName(other)))
                            done = True
                            break
                        if done:
                            break
                    r += 0.1
                if done:
                    break

        if done:
            fixed += 1
            obs = sp.build_obstacles(board)
        else:
            print("  FAILED %s - no legal path" % label)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print("connected %d of %d orphan group(s)" % (fixed, len(groups) - 1))
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
