"""python add_via.py NET x y : one 0.6/0.3 through via on NET at (x,y), legality-checked."""
import sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
NET = sys.argv[1]; vx, vy = map(float, sys.argv[2:4])
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
net = board.FindNet(NET)
sp.GND_NAMES = (NET,)
obs = sp.build_obstacles(board)
if not sp.via_is_legal(vx, vy, 0.6, obs, None):
    raise SystemExit("via %s at (%.2f,%.2f) not legal" % (NET, vx, vy))
v = pcbnew.PCB_VIA(board)
v.SetPosition(pcbnew.VECTOR2I(sp.mm(vx), sp.mm(vy))); v.SetWidth(sp.mm(0.6)); v.SetDrill(sp.mm(0.3))
v.SetNetCode(net.GetNetCode()); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
board.Add(v)
pcbnew.SaveBoard(str(BOARD), board)
print("%s via (%.2f,%.2f)" % (NET, vx, vy))
