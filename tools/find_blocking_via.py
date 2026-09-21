"""List GND vias sitting in U10.12's escape corridor."""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
gndcode = board.FindNet("GND").GetNetCode()

PX, PY = 113.963, 56.500          # U10.12
for t in board.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T or t.GetNetCode() != gndcode:
        continue
    p = t.GetPosition()
    x, y = sp.to_mm(p.x), sp.to_mm(p.y)
    d = math.hypot(x - PX, y - PY)
    if d <= 3.0:
        try:
            w = sp.to_mm(t.GetWidth(pcbnew.F_Cu))
        except Exception:
            w = sp.to_mm(t.GetWidth())
        ang = math.degrees(math.atan2(y - PY, x - PX)) % 360
        print("GND via at (%.3f, %.3f)  dia %.2f  %.2f mm away, bearing %.0f deg"
              % (x, y, w, d, ang))
