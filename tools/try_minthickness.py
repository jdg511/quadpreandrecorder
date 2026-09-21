"""Raise GND zone minimum fill width so the filler stops emitting thin slivers."""
import sys
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
WIDTH = float(sys.argv[1]) if len(sys.argv) > 1 else 0.30

board = pcbnew.LoadBoard(str(BOARD))
n = 0
for z in board.Zones():
    if z.GetIsRuleArea():
        continue
    z.SetMinThickness(pcbnew.FromMM(WIDTH))
    n += 1
print(f"min fill width set to {WIDTH} mm on {n} copper zones")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
tot = 0
for z in board.Zones():
    if z.GetIsRuleArea():
        continue
    for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        if z.IsOnLayer(ly):
            tot += z.GetFilledPolysList(ly).OutlineCount()
print(f"total fill islands now: {tot}")
pcbnew.SaveBoard(str(BOARD), board)
print(BOARD)
