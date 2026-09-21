r"""Rev C3: tiny A* grid router for one net on one layer, obstacle-aware
through stitch_pass3's geometry checks. Used for the two TPS61175 control
nets Freerouting kept refusing once In2 was a plane.

    python tools/grid_route.py NET LAYER sx sy tx ty [step] [x0 y0 x1 y1]

Routes a 0.20 mm track on LAYER (F.Cu/B.Cu) from (sx,sy) to (tx,ty), 8-way
moves on a grid, every move checked with track_is_legal against everything
that is not on NET. Collinear runs are merged before the segments are added.
"""
import heapq, math, sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

NET, LAYER = sys.argv[1], sys.argv[2]
sx, sy, tx, ty = map(float, sys.argv[3:7])
STEP = float(sys.argv[7]) if len(sys.argv) > 7 else 0.4
WIN = tuple(map(float, sys.argv[8:12])) if len(sys.argv) > 11 else None
W = 0.20
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"

board = pcbnew.LoadBoard(str(BOARD))
layer = pcbnew.F_Cu if LAYER == "F.Cu" else pcbnew.B_Cu
net = board.FindNet(NET)
if net is None:
    raise SystemExit("no net " + NET)
sp.GND_NAMES = (NET,)          # only OUR net is 'same'; GND becomes an obstacle
sp.TRACK_W = W
obs = sp.build_obstacles(board)

# bounding window: explicit, or a margin around the start/target box
if WIN:
    x0, y0, x1, y1 = WIN
else:
    x0, x1 = min(sx, tx) - 8.0, max(sx, tx) + 8.0
    y0, y1 = min(sy, ty) - 8.0, max(sy, ty) + 8.0
# keep only obstacles that can matter inside the window (speed)
pads, segs, vias, edges, holes, rule_areas = obs
M = 3.0
pads = [t for t in pads if x0 - M <= t[0] <= x1 + M and y0 - M <= t[1] <= y1 + M]
segs = [t for t in segs if (x0 - M <= t[0] <= x1 + M and y0 - M <= t[1] <= y1 + M) or (x0 - M <= t[2] <= x1 + M and y0 - M <= t[3] <= y1 + M)]
vias = [t for t in vias if x0 - M <= t[0] <= x1 + M and y0 - M <= t[1] <= y1 + M]
holes = [t for t in holes if x0 - M <= t[0] <= x1 + M and y0 - M <= t[1] <= y1 + M]
obs = (pads, segs, vias, edges, holes, rule_areas)
print("window x %.1f..%.1f y %.1f..%.1f; obstacles: %d pads %d segs %d vias %d holes" % (x0, x1, y0, y1, len(pads), len(segs), len(vias), len(holes)))

def snap(v, o):
    return round((v - o) / STEP)

def pos(i, j):
    return (sx + i * STEP, sy + j * STEP)

goal = (snap(tx, sx), snap(ty, sy))
gx, gy = pos(*goal)
print("start (%.2f,%.2f) goal cell (%.2f,%.2f) [%.2f from %.2f,%.2f]" % (sx, sy, gx, gy, math.hypot(gx - tx, gy - ty), tx, ty))

moves = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
legal_cache = {}
def legal(a, b):
    key = (a, b)
    if key in legal_cache:
        return legal_cache[key]
    ax, ay = pos(*a); bx, by = pos(*b)
    ok = x0 <= bx <= x1 and y0 <= by <= y1 and sp.track_is_legal(ax, ay, bx, by, layer, obs, None)
    legal_cache[key] = ok
    return ok

start = (0, 0)
h = lambda c: math.hypot(c[0] - goal[0], c[1] - goal[1])
openq = [(h(start), 0.0, start)]
came, g = {start: None}, {start: 0.0}
found = False
expanded = 0
while openq:
    f, gc, cur = heapq.heappop(openq)
    if cur == goal:
        found = True
        break
    if gc > g.get(cur, 1e9):
        continue
    expanded += 1
    for dx, dy in moves:
        nxt = (cur[0] + dx, cur[1] + dy)
        cost = gc + math.hypot(dx, dy)
        if cost >= g.get(nxt, 1e9):
            continue
        if not legal(cur, nxt):
            continue
        g[nxt] = cost; came[nxt] = cur
        heapq.heappush(openq, (cost + h(nxt), cost, nxt))
print("expanded", expanded, "cells")
if not found:
    raise SystemExit("NO PATH for %s on %s" % (NET, LAYER))

path = []
c = goal
while c is not None:
    path.append(c); c = came[c]
path.reverse()
# merge collinear runs
pts = [pos(*path[0])]
d_prev = None
for a, b in zip(path, path[1:]):
    d = (b[0] - a[0], b[1] - a[1])
    if d != d_prev and d_prev is not None:
        pts.append(pos(*a))
    d_prev = d
pts.append(pos(*path[-1]))
# snap the ends exactly onto the requested points
pts[0] = (sx, sy); pts[-1] = (tx, ty)
# verify merged segments are still legal (they are unions of legal steps, but check)
for a, b in zip(pts, pts[1:]):
    if not sp.track_is_legal(a[0], a[1], b[0], b[1], layer, obs, None):
        print("WARNING merged segment (%.2f,%.2f)-(%.2f,%.2f) fails the check; adding anyway" % (a[0], a[1], b[0], b[1]))
total = 0.0
for a, b in zip(pts, pts[1:]):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(sp.mm(a[0]), sp.mm(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(sp.mm(b[0]), sp.mm(b[1])))
    t.SetWidth(sp.mm(W)); t.SetLayer(layer); t.SetNetCode(net.GetNetCode())
    board.Add(t)
    total += math.hypot(b[0] - a[0], b[1] - a[1])
print("%s on %s: %d segments, %.1f mm" % (NET, LAYER, len(pts) - 1, total))
for p in pts:
    print("   (%.2f, %.2f)" % p)
pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
