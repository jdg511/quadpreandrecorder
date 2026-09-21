"""python add_via_and_hop.py NET vx vy px py : via at (vx,vy) + F.Cu track to (px,py)."""
import sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
NET = sys.argv[1]; vx, vy, px, py = map(float, sys.argv[2:6])
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
net = board.FindNet(NET)
sp.GND_NAMES = (NET,); sp.TRACK_W = 0.20
obs = sp.build_obstacles(board)
if not sp.via_is_legal(vx, vy, 0.6, obs, None):
    raise SystemExit("via at (%.2f,%.2f) not legal" % (vx, vy))
if not sp.track_is_legal(vx, vy, px, py, pcbnew.F_Cu, obs, None, new_via=(vx, vy)):
    raise SystemExit("F.Cu hop not legal")
v = pcbnew.PCB_VIA(board)
v.SetPosition(pcbnew.VECTOR2I(sp.mm(vx), sp.mm(vy))); v.SetWidth(sp.mm(0.6)); v.SetDrill(sp.mm(0.3))
v.SetNetCode(net.GetNetCode()); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
board.Add(v)
t = pcbnew.PCB_TRACK(board)
t.SetStart(pcbnew.VECTOR2I(sp.mm(vx), sp.mm(vy))); t.SetEnd(pcbnew.VECTOR2I(sp.mm(px), sp.mm(py)))
t.SetWidth(sp.mm(0.20)); t.SetLayer(pcbnew.F_Cu); t.SetNetCode(net.GetNetCode())
board.Add(t)
pcbnew.SaveBoard(str(BOARD), board)
print("%s via (%.2f,%.2f) + F.Cu hop to (%.2f,%.2f)" % (NET, vx, vy, px, py))
