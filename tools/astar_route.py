"""Close 'Missing connection' items from a kicad-cli DRC JSON report with a
grid A* router (F.Cu / B.Cu, 0.20 mm tracks, 0.6/0.3 vias), every step
checked with stitch_pass3's geometry rules (the same checker poly_route.py
uses), so nothing illegal is ever written.

    python tools/astar_route.py hardware/fabrication/drc.json [--only NET,...] [--dry]
"""
import heapq, json, math, sys, time
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
GRID = 0.127          # 2.54/20: lines up with the socket pad rows so the 0.74 mm gaps between pins are on the grid
ALIGN = (75.24, 62.5) # a socket pad centre; the grid passes through it
W = 0.20
VIA_COST = 80.0   # grid steps (0.127 mm): a via costs about 10 mm of track
MARGINS = (5.0, 9.0, 14.0, 20.0)
RASTER_CLR = 0.16      # DRC minimum is 0.15; stitch_pass3 default 0.18 is too shy for a re-route in a routed board
LAST_FAIL = None
END_FREE = 0.6         # mm around each endpoint that is always passable (verified afterwards)
F, B = pcbnew.F_Cu, pcbnew.B_Cu

args = sys.argv[1:]
report = Path(args[0])
only = None
if "--only" in args:
    only = set(args[args.index("--only") + 1].split(","))
dry = "--dry" in args

board = pcbnew.LoadBoard(str(BOARD))
sp.TRACK_W = W
sp.CLEARANCE = RASTER_CLR
mm, to_mm = sp.mm, sp.to_mm
by_uuid = {}
for fp in board.Footprints():
    for p in fp.Pads():
        by_uuid[p.m_Uuid.AsString()] = p
for t in board.GetTracks():
    by_uuid[t.m_Uuid.AsString()] = t

def item_anchor(item, other_xy):
    """(x, y, layers) for an item; for a track pick the end nearer the other item."""
    if item.Type() == pcbnew.PCB_PAD_T:
        p = item.GetPosition()
        layers = tuple(l for l in (F, B) if item.IsOnLayer(l))
        return to_mm(p.x), to_mm(p.y), layers
    if item.Type() == pcbnew.PCB_VIA_T:
        p = item.GetPosition()
        return to_mm(p.x), to_mm(p.y), (F, B)
    s, e = item.GetStart(), item.GetEnd()
    cands = [(to_mm(s.x), to_mm(s.y)), (to_mm(e.x), to_mm(e.y))]
    if other_xy is not None:
        cands.sort(key=lambda c: math.hypot(c[0] - other_xy[0], c[1] - other_xy[1]))
    return cands[0][0], cands[0][1], (item.GetLayer(),)

def subset(obs, x0, y0, x1, y1):
    pads, segs, vias, edges, holes, rule_areas = obs
    m = 3.0
    inb = lambda x, y: x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m
    pads2 = [p for p in pads if inb(p[0], p[1])]
    segs2 = [s for s in segs if not (max(s[0], s[2]) < x0 - m or min(s[0], s[2]) > x1 + m or max(s[1], s[3]) < y0 - m or min(s[1], s[3]) > y1 + m)]
    vias2 = [v for v in vias if inb(v[0], v[1])]
    holes2 = [h for h in holes if inb(h[0], h[1])]
    return pads2, segs2, vias2, edges, holes2, rule_areas

def raster(obs, x0, y0, nx, ny, ox, oy, clr, extra):
    """Per-layer boolean grids: True where a track centre may sit."""
    pads, segs, vias, edges, holes, rule_areas = obs
    need = W / 2 + clr + extra   # extra: grid-point test stands in for the segment test
    free = {F: [[True] * ny for _ in range(nx)], B: [[True] * ny for _ in range(nx)]}
    def cells(bx0, by0, bx1, by1):
        i0 = max(0, int((bx0 - ox) / GRID) - 1); i1 = min(nx - 1, int((bx1 - ox) / GRID) + 1)
        j0 = max(0, int((by0 - oy) / GRID) - 1); j1 = min(ny - 1, int((by1 - oy) / GRID) + 1)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                yield i, j, ox + i * GRID, oy + j * GRID
    for cx, cy, hw, hh, same, uuid, on in pads:
        if same: continue
        for L in on:
            for i, j, x, y in cells(cx - hw - need, cy - hh - need, cx + hw + need, cy + hh + need):
                if sp.rect_dist(x, y, cx, cy, hw, hh) < need: free[L][i][j] = False
    for ax, ay, bx, by, shw, L in segs:
        if L not in (F, B): continue
        r = shw + need
        for i, j, x, y in cells(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r):
            if sp.seg_dist(x, y, ax, ay, bx, by) < r: free[L][i][j] = False
    for vx, vy, vr, same in vias:
        if same: continue
        r = vr + need
        for i, j, x, y in cells(vx - r, vy - r, vx + r, vy + r):
            if math.hypot(x - vx, y - vy) < r: free[F][i][j] = False; free[B][i][j] = False
    for hx, hy, hr, same in holes:
        if same: continue
        r = hr + need
        for i, j, x, y in cells(hx - r, hy - r, hx + r, hy + r):
            if math.hypot(x - hx, y - hy) < r: free[F][i][j] = False; free[B][i][j] = False
    for ax, ay, bx, by in edges:
        r = W / 2 + sp.EDGE_KEEP + extra
        for i, j, x, y in cells(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r):
            if sp.seg_dist(x, y, ax, ay, bx, by) < r: free[F][i][j] = False; free[B][i][j] = False
    return free

def astar(obs, sx, sy, slayers, gx, gy, glayers, margin, clr=0.16, extra=0.05):
    x0, y0 = max(1.0, min(sx, gx) - margin), max(1.0, min(sy, gy) - margin)
    x1, y1 = min(137.0, max(sx, gx) + margin), min(113.0, max(sy, gy) + margin)
    obs = subset(obs, x0, y0, x1, y1)
    ox = ALIGN[0] - round((ALIGN[0] - x0) / GRID) * GRID
    oy = ALIGN[1] - round((ALIGN[1] - y0) / GRID) * GRID
    nx, ny = int((x1 - ox) / GRID) + 1, int((y1 - oy) / GRID) + 1
    if nx * ny > 400000:
        return None                          # too big for a pure-Python A*; the caller tries other targets
    free = raster(obs, x0, y0, nx, ny, ox, oy, clr, extra)
    def w(ix, iy): return ox + ix * GRID, oy + iy * GRID
    def g(x, y): return round((x - ox) / GRID), round((y - oy) / GRID)
    gix, giy = g(gx, gy); six, siy = g(sx, sy)
    # the two end cells are always allowed (they sit on same-net copper)
    for (i, j, Ls) in ((six, siy, slayers), (gix, giy, glayers)):
        rr = int(END_FREE / GRID) + 1
        for di in range(-rr, rr + 1):
            for dj in range(-rr, rr + 1):
                if math.hypot(di, dj) * GRID <= END_FREE and 0 <= i + di < nx and 0 <= j + dj < ny:
                    for L in Ls: free[L][i + di][j + dj] = True
    via_cache = {}
    def via_ok(ix, iy):
        if (ix, iy) not in via_cache:
            x, y = w(ix, iy)
            via_cache[(ix, iy)] = free[F][ix][iy] and free[B][ix][iy] and sp.via_is_legal(x, y, 0.6, obs, None)
        return via_cache[(ix, iy)]
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    best = None
    for sl in slayers:
        start = (six, siy, sl)
        openq = [(0.0, start)]; gsc = {start: 0.0}; came = {}; seen = set()
        found = None
        while openq:
            _, cur = heapq.heappop(openq)
            if cur in seen: continue
            seen.add(cur)
            cx, cy, cl = cur
            if (cx, cy) == (gix, giy):
                if cl in glayers:
                    found = cur; break
                if via_ok(cx, cy):
                    nxt = (cx, cy, glayers[0]); ng = gsc[cur] + VIA_COST
                    if ng < gsc.get(nxt, 1e18):
                        gsc[nxt] = ng; came[nxt] = cur; heapq.heappush(openq, (ng, nxt))
                continue
            for dx, dy in moves:
                nix, niy = cx + dx, cy + dy
                if not (0 <= nix < nx and 0 <= niy < ny): continue
                if not free[cl][nix][niy]: continue
                if dx and dy and not (free[cl][cx + dx][cy] or free[cl][cx][cy + dy]): continue
                nxt = (nix, niy, cl); ng = gsc[cur] + math.hypot(dx, dy)
                if ng < gsc.get(nxt, 1e18):
                    gsc[nxt] = ng; came[nxt] = cur
                    heapq.heappush(openq, (ng + math.hypot(gix - nix, giy - niy), nxt))
            ol = B if cl == F else F
            if free[ol][cx][cy] and via_ok(cx, cy):
                nxt = (cx, cy, ol); ng = gsc[cur] + VIA_COST
                if ng < gsc.get(nxt, 1e18):
                    gsc[nxt] = ng; came[nxt] = cur
                    heapq.heappush(openq, (ng + math.hypot(gix - cx, giy - cy), nxt))
        if found is not None and (best is None or gsc[found] < best[0]):
            path = []; node = found
            while node in came:
                path.append(node); node = came[node]
            path.append(start); path.reverse()
            pts = [(w(ix, iy)[0], w(ix, iy)[1], l) for ix, iy, l in path]
            if math.hypot(pts[0][0] - sx, pts[0][1] - sy) > 1e-6:
                pts.insert(0, (sx, sy, pts[0][2]))     # exact start point (sub-grid hop)
            best = (gsc[found], pts)
    if best is None:
        return None
    # final exact check of the simplified path with the real geometry rules
    sp.CLEARANCE = 0.151                     # DRC minimum is 0.150; the exact checker is the arbiter from here on
    path = pull(simplify(best[1]), obs)
    n = len(path) - 1
    for k, ((ax, ay, al), (bx, by, bl)) in enumerate(zip(path, path[1:])):
        ok = al != bl or sp.track_is_legal(ax, ay, bx, by, al, obs, None)
        if al != bl and not sp.via_is_legal(ax, ay, 0.6, obs, None):
            ok = False
        if not ok:
            sp.CLEARANCE = RASTER_CLR
            print("   (verify failed on segment %d/%d at (%.2f,%.2f))" % (k + 1, n, ax, ay))
            global LAST_FAIL
            LAST_FAIL = (ax, ay)
            return None
    sp.CLEARANCE = RASTER_CLR
    return path

def pull(path, obs):
    """String-pulling: replace staircase runs by the longest legal straight segment (same layer)."""
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1:
            if all(p[2] == path[i][2] for p in path[i:j + 1]) and sp.track_is_legal(path[i][0], path[i][1], path[j][0], path[j][1], path[i][2], obs, None):
                break
            j -= 1
        out.append(path[j]); i = j
    return out

def simplify(path):
    out = [path[0]]
    for i in range(1, len(path) - 1):
        x0, y0, l0 = out[-1]; x1, y1, l1 = path[i]; x2, y2, l2 = path[i + 1]
        if l0 == l1 == l2 and abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) < 1e-6:
            continue
        out.append(path[i])
    out.append(path[-1])
    return out

def commit(net, path, gx, gy):
    path = simplify(path)
    # final exact hop from the last grid point to the true goal (sub-grid)
    if math.hypot(path[-1][0] - gx, path[-1][1] - gy) > 1e-6:
        path.append((gx, gy, path[-1][2]))
    nseg = nvia = 0
    for (ax, ay, al), (bx, by, bl) in zip(path, path[1:]):
        if al != bl:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(mm(ax), mm(ay))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
            v.SetNetCode(net.GetNetCode()); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B); board.Add(v); nvia += 1
        elif math.hypot(bx - ax, by - ay) > 1e-6:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(mm(ax), mm(ay))); t.SetEnd(pcbnew.VECTOR2I(mm(bx), mm(by)))
            t.SetWidth(mm(W)); t.SetLayer(al); t.SetNetCode(net.GetNetCode()); board.Add(t); nseg += 1
    return nseg, nvia


# ------------------------------------------------------------------ clusters --
def net_items(net_name):
    out = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetNetname() == net_name: out.append(p)
    for t in board.GetTracks():
        if t.GetNetname() == net_name: out.append(t)
    return out

def clusters(net_name):
    items = net_items(net_name)
    parent = list(range(len(items)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(i, j): parent[find(i)] = find(j)
    def geom(it):
        if it.Type() == pcbnew.PCB_PAD_T:
            p = it.GetPosition(); bb = it.GetBoundingBox()
            r = max(to_mm(bb.GetWidth()), to_mm(bb.GetHeight())) / 2.0
            Ls = tuple(l for l in (F, B) if it.IsOnLayer(l))
            return ("pad", [(to_mm(p.x), to_mm(p.y))], r, Ls)
        if it.Type() == pcbnew.PCB_VIA_T:
            p = it.GetPosition()
            return ("via", [(to_mm(p.x), to_mm(p.y))], 0.3, (F, B))
        s_, e_ = it.GetStart(), it.GetEnd()
        return ("seg", [(to_mm(s_.x), to_mm(s_.y)), (to_mm(e_.x), to_mm(e_.y))], 0.0, (it.GetLayer(),))
    G = [geom(it) for it in items]
    for i in range(len(items)):
        ki, pi, ri, li = G[i]
        for j in range(i + 1, len(items)):
            kj, pj, rj, lj = G[j]
            if not set(li) & set(lj): continue
            tol = ri + rj + 0.02
            if any(math.hypot(a[0] - b[0], a[1] - b[1]) <= tol for a in pi for b in pj):
                union(i, j)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    return items, {it.m_Uuid.AsString(): find(i) for i, it in enumerate(items)}, groups

def shorten_or_remove(item, cur_xy):
    """Pull a jammed dangling track end back 1.5 mm (or drop a short stub). Returns new anchor (x, y, layers, item) or None."""
    if item.Type() != pcbnew.PCB_TRACE_T: return None
    s_, e_ = item.GetStart(), item.GetEnd()
    ends = [(to_mm(s_.x), to_mm(s_.y)), (to_mm(e_.x), to_mm(e_.y))]
    ends.sort(key=lambda c: math.hypot(c[0] - cur_xy[0], c[1] - cur_xy[1]))
    near, far = ends
    L = math.hypot(far[0] - near[0], far[1] - near[1])
    if L > 3.0:
        t = 1.5 / L
        nx_, ny_ = near[0] + (far[0] - near[0]) * t, near[1] + (far[1] - near[1]) * t
        if math.hypot(to_mm(s_.x) - near[0], to_mm(s_.y) - near[1]) < 0.01:
            item.SetStart(pcbnew.VECTOR2I(mm(nx_), mm(ny_)))
        else:
            item.SetEnd(pcbnew.VECTOR2I(mm(nx_), mm(ny_)))
        print("   (pulled %s end back 1.5 mm to (%.2f,%.2f))" % (item.GetNetname(), nx_, ny_))
        return nx_, ny_, (item.GetLayer(),), item
    nxt = None
    for t in board.GetTracks():
        if t is item or t.GetNetname() != item.GetNetname(): continue
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if any(math.hypot(to_mm(pt.x) - far[0], to_mm(pt.y) - far[1]) < 0.01 for pt in pts): nxt = t
    if nxt is None: return None
    print("   (dropped %.2f mm stub of %s at (%.2f,%.2f))" % (L, item.GetNetname(), near[0], near[1]))
    board.Remove(item)
    Ls = (F, B) if nxt.Type() == pcbnew.PCB_VIA_T else (nxt.GetLayer(),)
    return far[0], far[1], Ls, nxt

rep = json.loads(report.read_text(encoding="utf-8-sig"))
jobs = []
for u in rep.get("unconnected_items", []):
    items = u.get("items", [])
    if len(items) != 2: continue
    a, b = by_uuid.get(items[0]["uuid"]), by_uuid.get(items[1]["uuid"])
    if a is None or b is None:
        print("skip: unknown item", items[0]["description"], "|", items[1]["description"]); continue
    net = a.GetNetname()
    if only and net not in only: continue
    jobs.append((net, a, b, items[0]["description"], items[1]["description"]))
print(len(jobs), "connections to close")
ok = 0
for net_name, a, b, da, db in jobs:
    t0 = time.time()
    net = board.FindNet(net_name)
    sp.GND_NAMES = (net_name,)
    # prefer the smaller cluster as the source (a pad alone, a short stub)
    items, cid, groups = clusters(net_name)
    U = lambda it: it.m_Uuid.AsString()
    if U(a) not in cid or U(b) not in cid:
        print("[skip] %s: item vanished (already trimmed?)" % net_name); continue
    if cid[U(a)] == cid[U(b)]:
        print("[skip] %s: already connected" % net_name); ok += 1; continue
    if len(groups[cid[U(a)]]) > len(groups[cid[U(b)]]): a, b = b, a
    ax, ay, al = item_anchor(a, item_anchor(b, None)[:2])
    src_cluster = cid[U(a)]
    path = None; tries = 0
    while path is None and tries < 6:
        tries += 1
        # candidate targets: every item outside the source cluster, nearest first
        cands = []
        for it in items:
            if cid.get(U(it)) == src_cluster: continue
            x, y, Ls = item_anchor(it, (ax, ay))
            cands.append((math.hypot(x - ax, y - ay), x, y, Ls, it))
        cands.sort(key=lambda c: c[0])
        obs = sp.build_obstacles(board)
        fail_here = None
        best_alt = None
        for d, bx_, by_, bl_, bit in cands[:4]:
            for clr, extra in ((0.16, 0.05), (0.15, 0.0)):
                for margin in (MARGINS if extra else MARGINS[:2]):
                    LAST_FAIL = None
                    cand = astar(obs, ax, ay, al, bx_, by_, bl_, margin, clr, extra)
                    if cand:
                        nvia = sum(1 for p, q in zip(cand, cand[1:]) if p[2] != q[2])
                        if best_alt is None or nvia < best_alt[0]: best_alt = (nvia, cand, bx_, by_, margin)
                        break
                    if LAST_FAIL is not None: fail_here = LAST_FAIL
                if best_alt and best_alt[0] <= 1: break
            if best_alt and best_alt[0] <= 1: break
        if best_alt:
            nvia, path, bx, by, margin = best_alt
            break
        # nothing worked: free a jammed end and retry
        fixed = None
        if fail_here is not None and math.hypot(fail_here[0] - ax, fail_here[1] - ay) < 2.5:
            fixed = shorten_or_remove(a, (ax, ay))
            if fixed: ax, ay, al, a = fixed
        if fixed is None and fail_here is not None:
            # jam at the target side: pull the nearest candidate back
            for d, bx, by, bl, bit in cands[:4]:
                if math.hypot(fail_here[0] - bx, fail_here[1] - by) < 2.5:
                    fixed = shorten_or_remove(bit, (bx, by)); break
        if fixed is None:
            fixed = shorten_or_remove(a, (ax, ay))
            if fixed: ax, ay, al, a = fixed
        if fixed is None: break
        items, cid, groups = clusters(net_name)
        src_cluster = cid.get(U(a))
        if src_cluster is None: break
    if path is None:
        print("[FAIL] %-12s from (%.2f,%.2f)  %s | %s" % (net_name, ax, ay, da, db)); continue
    if not dry:
        ns, nv = commit(net, path, bx, by)
        pcbnew.SaveBoard(str(BOARD), board)   # crash insurance: keep every closed connection
    else:
        ns, nv = len(path) - 1, sum(1 for p, q in zip(path, path[1:]) if p[2] != q[2])
    ok += 1
    print("[ok]   %-12s (%.2f,%.2f)->(%.2f,%.2f) %d seg %d via, %.0fs, margin %.0f" % (net_name, ax, ay, bx, by, ns, nv, time.time() - t0, margin))
if not dry:
    pcbnew.SaveBoard(str(BOARD), board)
print("done %d/%d%s" % (ok, len(jobs), " (dry run, nothing saved)" if dry else ", board saved"))
