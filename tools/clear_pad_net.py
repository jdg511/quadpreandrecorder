"""python clear_pad_net.py REF PAD : detach a pad from its net (schematic pin is now NC)."""
import sys
from pathlib import Path
import pcbnew
ref, num = sys.argv[1], sys.argv[2]
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
fp = board.FindFootprintByReference(ref)
pad = fp.FindPadByNumber(num)
print(ref, num, "was", pad.GetNetname())
pad.SetNetCode(0)
pcbnew.SaveBoard(str(BOARD), board)
print("now", repr(pad.GetNetname()), "saved")
