"""Rev C3 (2026-09-15): correct the Teensy 4.1 socket (U8) in the routed board.

The custom footprint had its two rows 17.78 mm apart (real module: 15.24 mm)
and the right row's pad order shifted by one. This moves every U8 pad to the
correct place, fixes the outline, then deletes the copper that the move
invalidates (old escape stubs of the right-row nets inside the socket
corridor, plus anything of another net now inside a moved pad's clearance).
The gaps are closed afterwards by tools/astar_route.py from the DRC report.
"""
import math, shutil, sys
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
BACKUP = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb.revc3final-preteensyfix-20260915"
if not BACKUP.exists():
    shutil.copy2(BOARD, BACKUP)
    print("backup ->", BACKUP.name)

mm, to_mm = pcbnew.FromMM, pcbnew.ToMM
board = pcbnew.LoadBoard(str(BOARD))
u8 = board.FindFootprintByReference("U8")
assert u8 is not None
fx, fy = to_mm(u8.GetPosition().x), to_mm(u8.GetPosition().y)
print("U8 at", fx, fy, "flipped:", u8.IsFlipped(), "orient:", u8.GetOrientationDegrees())

left = ["GND1", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "3V3A", "24", "25", "26", "27", "28", "29", "30", "31", "32"]
right = ["VIN", "GND2", "3V3B", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13", "GND3", "41", "40", "39", "38", "37", "36", "35", "34", "33"]
design = {n: (0.0, i * 2.54) for i, n in enumerate(left)}
design.update({n: (15.24, i * 2.54) for i, n in enumerate(right)})
ysign = -1.0 if u8.IsFlipped() else 1.0

old_pos = {}
new_pads = []
for pad in u8.Pads():
    n = pad.GetNumber()
    p = pad.GetPosition()
    old_pos[n] = (to_mm(p.x), to_mm(p.y))
    x, y = design[n]
    pad.SetFPRelativePosition(pcbnew.VECTOR2I(mm(x), mm(ysign * y)))
    q = pad.GetPosition()
    new_pads.append((n, pad.GetNetname(), to_mm(q.x), to_mm(q.y), to_mm(pad.GetSize().x) / 2.0))
for n, net, x, y, r in new_pads:
    if old_pos[n] != (x, y):
        print("  pad %-5s %-12s (%.2f,%.2f) -> (%.2f,%.2f)" % (n, net, old_pos[n][0], old_pos[n][1], x, y))

# outline graphics: every vertex at local x = 19.05 moves to 16.51 (stored frame)
moved = 0
for g in u8.GraphicalItems():
    if g.Type() != pcbnew.PCB_SHAPE_T:
        continue
    for getter, setter in ((g.GetStart, g.SetStart), (g.GetEnd, g.SetEnd)):
        pt = getter()
        lx = to_mm(pt.x) - fx
        if abs(lx - 19.05) < 0.01:
            setter(pcbnew.VECTOR2I(pt.x - mm(2.54), pt.y))
            moved += 1
print("outline vertices moved:", moved)
for txt in (u8.Reference(), u8.Value()):
    pt = txt.GetPosition()
    if abs(to_mm(pt.x) - fx - 8.89) < 0.01:
        txt.SetPosition(pcbnew.VECTOR2I(pt.x - mm(1.27), pt.y))

# ---- copper that the move invalidates -------------------------------------
right_nets = {net for n, net, x, y, r in new_pads if n in right and net not in ("GND", "/GND")}
CLR = 0.15
def seg_pt_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    if L < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

# corridor around the old and new right rows
X0, X1, Y0, Y1 = 72.7, 80.5, 2.5, 64.5
old_centres = [(old_pos[n], u8.FindPadByNumber(n).GetNetname()) for n in right]
kill = []
for t in board.GetTracks():
    net = t.GetNetname()
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); x, y = to_mm(p.x), to_mm(p.y)
        try: vr = to_mm(t.GetWidth(pcbnew.F_Cu)) / 2.0
        except Exception: vr = 0.4
        why = None
        if net in right_nets and X0 <= x <= X1 and Y0 <= y <= Y1:
            why = "right-row escape via in corridor"
        else:
            for n, pnet, px, py, r in new_pads:
                if pnet != net and math.hypot(x - px, y - py) < r + vr + CLR:
                    why = "collides with new pad %s" % n; break
        if why: kill.append((t, "via %s (%.2f,%.2f) %s" % (net, x, y, why)))
        continue
    s, e = t.GetStart(), t.GetEnd()
    ax, ay, bx, by = to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y)
    hw = to_mm(t.GetWidth()) / 2.0
    why = None
    if net in right_nets:
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if X0 <= mx <= X1 and Y0 <= my <= Y1:
            why = "right-row escape stub in corridor"
        else:
            for (ox, oy), onet in old_centres:
                if onet == net and (math.hypot(ax - ox, ay - oy) < 0.05 or math.hypot(bx - ox, by - oy) < 0.05):
                    why = "ends on old pad centre"; break
    if why is None:
        for n, pnet, px, py, r in new_pads:
            if pnet != net and seg_pt_dist(px, py, ax, ay, bx, by) < r + hw + CLR:
                why = "collides with new pad %s" % n; break
    if why: kill.append((t, "seg %s %s (%.2f,%.2f)-(%.2f,%.2f) %s" % (net, board.GetLayerName(t.GetLayer()), ax, ay, bx, by, why)))

for t, msg in kill:
    print("  remove", msg)
for t, msg in kill:
    board.Remove(t)
print("removed", len(kill), "items")
pcbnew.SaveBoard(str(BOARD), board)
print("STAGE A SAVED")
