"""Final-check cleanups: drop the 4 EP vias that sat on B.Cu tracks, the 2 stitching vias that
overlap SW2/SW3 pad holes, the 0.0065 mm HP_OUT_L sliver, and mark TP1/TP2 excluded from BOM."""
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
mm = pcbnew.ToMM
kill_vias = [(8.5, 33.45), (129.0, 17.0), (129.0, 16.0), (129.5, 16.5), (76.0, 70.5), (49.5, 76.0)]
n = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        if any(abs(mm(p.x) - x) < 0.01 and abs(mm(p.y) - y) < 0.01 for x, y in kill_vias):
            print("remove via", t.GetNetname(), mm(p.x), mm(p.y)); board.Remove(t); n += 1
    elif t.GetNetname() == "HP_OUT_L" and t.GetLength() < pcbnew.FromMM(0.02):
        print("remove sliver", mm(t.GetStart().x), mm(t.GetStart().y), t.GetLength()); board.Remove(t); n += 1
for fp in board.GetFootprints():
    if fp.GetReference() in ("TP1", "TP2"):
        fp.SetExcludedFromBOM(True); print("excluded from BOM:", fp.GetReference())
pcbnew.SaveBoard(str(BOARD), board)
print("removed", n, "items; saved")
