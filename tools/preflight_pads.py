"""Catch pads that foul the board edge or a rule area BEFORE routing.

A routing cycle is 8 minutes, so it is worth 2 seconds to check that no pad
clips the 0.65 mm edge keepout or the 0.50 mm copper-to-edge rule. Both bit
the 2026-09-11 wall-connector moves, because the obvious limit (0.30 mm
copper to edge) is not the binding one.

Run after generate_pcb.py, before the DSN goes to Freerouting.
"""
import sys

import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
BOARD_W, BOARD_H = 138.0, 114.0
EDGE_RULE = 0.50        # board setup: copper to edge
KEEPOUT = 0.65          # add_edge_keepouts() strip width


def mm(v):
    return pcbnew.ToMM(v)


board = pcbnew.LoadBoard(PCB)
bad = []

for fp in board.Footprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        x0, x1 = mm(bb.GetLeft()), mm(bb.GetRight())
        y0, y1 = mm(bb.GetTop()), mm(bb.GetBottom())
        gaps = {
            "left": x0,
            "right": BOARD_W - x1,
            "rear": y0,
            "front": BOARD_H - y1,
        }
        worst_edge, worst = min(gaps.items(), key=lambda kv: kv[1])
        ref = "%s.%s" % (fp.GetReference(), pad.GetNumber())
        if worst < EDGE_RULE:
            bad.append(("EDGE RULE", ref, worst_edge, worst, EDGE_RULE))
        elif worst < KEEPOUT:
            bad.append(("KEEPOUT ", ref, worst_edge, worst, KEEPOUT))

print("pads checked: %d"
      % sum(len(list(f.Pads())) for f in board.Footprints()))
if not bad:
    print("OK: every pad clears the %.2f mm edge keepout" % KEEPOUT)
    sys.exit(0)

print("\n%d pad(s) too close to a board edge:" % len(bad))
for kind, ref, edge, gap, need in sorted(bad, key=lambda r: r[3]):
    print("   %s %-10s %-5s edge  gap %.3f mm, needs %.2f" %
          (kind, ref, edge, gap, need))
sys.exit(1)
