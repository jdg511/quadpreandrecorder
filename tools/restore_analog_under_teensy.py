"""Drop the A* re-routes of the analog nets that ran under the Teensy (BRU_PRE, BRU_CFB):
everything of those nets that is not in the pre-fix backup is removed; hand routes follow (poly_route)."""
from pathlib import Path
import pcbnew
ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
BACKUP = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb.revc3final-preteensyfix-20260915"
NETS = ("BRU_PRE", "BRU_CFB")
to_mm = pcbnew.ToMM
def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); return ("via", round(to_mm(p.x), 3), round(to_mm(p.y), 3))
    s, e = t.GetStart(), t.GetEnd()
    return ("seg", t.GetLayer(), round(to_mm(s.x), 3), round(to_mm(s.y), 3), round(to_mm(e.x), 3), round(to_mm(e.y), 3))
orig = set()
import shutil, tempfile
tmp = Path(tempfile.gettempdir()) / "preteensyfix.kicad_pcb"
shutil.copy2(BACKUP, tmp)
bak = pcbnew.LoadBoard(str(tmp))
for t in bak.GetTracks():
    if t.GetNetname() in NETS: orig.add(key(t))
board = pcbnew.LoadBoard(str(BOARD))
n = 0
for t in list(board.GetTracks()):
    if t.GetNetname() in NETS and key(t) not in orig:
        board.Remove(t); n += 1
pcbnew.SaveBoard(str(BOARD), board)
print("removed", n, "router-added items of", NETS)
