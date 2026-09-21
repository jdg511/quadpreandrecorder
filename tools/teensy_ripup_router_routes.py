"""Before the Freerouting finishing pass: drop every track/via the A* helper added
(anything not in the pre-fix backup), except BRU_PRE's straight re-route, so
Freerouting routes the Teensy-side nets properly with the rest protected."""
import shutil, tempfile
from pathlib import Path
import pcbnew
ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
BACKUP = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb.revc3final-preteensyfix-20260915"
KEEP_NETS = {"BRU_PRE"}
to_mm = pcbnew.ToMM
def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); return ("via", round(to_mm(p.x), 3), round(to_mm(p.y), 3))
    s, e = t.GetStart(), t.GetEnd()
    return ("seg", t.GetLayer(), round(to_mm(s.x), 3), round(to_mm(s.y), 3), round(to_mm(e.x), 3), round(to_mm(e.y), 3))
tmp = Path(tempfile.gettempdir()) / "preteensyfix.kicad_pcb"
shutil.copy2(BACKUP, tmp)
bak = pcbnew.LoadBoard(str(tmp))
orig = {key(t) for t in bak.GetTracks()}
board = pcbnew.LoadBoard(str(BOARD))
shutil.copy2(BOARD, ROOT / "hardware" / "QuadPreRecorder.kicad_pcb.teensyfix-astar-20260915")
n = 0; nets = set()
for t in list(board.GetTracks()):
    if t.GetNetname() in KEEP_NETS: continue
    if key(t) not in orig:
        nets.add(t.GetNetname()); board.Remove(t); n += 1
pcbnew.SaveBoard(str(BOARD), board)
print("removed", n, "helper items on", sorted(nets))
