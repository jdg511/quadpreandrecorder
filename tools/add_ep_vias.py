"""python add_ep_vias.py NET x,y x,y ... : 0.6/0.3 through vias on NET with NO legality check
(for vias inside a same-net exposed pad, which stitch_pass3 refuses). Also types In1/In2 as power.
Run DRC afterwards."""
import sys
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
net = board.FindNet(sys.argv[1])
mm = pcbnew.FromMM
for tok in sys.argv[2:]:
    x, y = map(float, tok.split(","))
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
    v.SetNetCode(net.GetNetCode()); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    print("%s via (%.2f,%.2f)" % (sys.argv[1], x, y))
for lay in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    board.SetLayerType(lay, pcbnew.LT_POWER)
    print("layer %s -> power" % board.GetLayerName(lay))
pcbnew.SaveBoard(str(BOARD), board)
print("saved")
