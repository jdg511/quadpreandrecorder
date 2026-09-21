"""Test: drop the F.Cu/B.Cu GND pours, keep In1 plane + In2 pour, refill.

Those outer pours were inherited from the 2-layer design, where they WERE the
ground system. With a solid In1 reference plane they mostly just fragment into
islands around the dense outer-layer routing.
"""
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"

board = pcbnew.LoadBoard(str(BOARD))
drop = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() == "GND plane"]
for z in drop:
    board.Remove(z)
print(f"removed {len(drop)} outer-layer GND pours")

for z in board.Zones():
    if not z.GetIsRuleArea():
        z.SetMinThickness(pcbnew.FromMM(0.20))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
tot = 0
for z in board.Zones():
    if z.GetIsRuleArea():
        continue
    for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        if z.IsOnLayer(ly):
            n = z.GetFilledPolysList(ly).OutlineCount()
            if n:
                print(f"  {board.GetLayerName(ly)}: {n} island(s)")
            tot += n
print(f"total islands: {tot}")
pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
