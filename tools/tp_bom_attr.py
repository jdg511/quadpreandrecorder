"""Mark TP1/TP2 footprints 'exclude from BOM' so they match the schematic (in_bom no)."""
from pathlib import Path
import pcbnew
BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(str(BOARD))
for fp in board.GetFootprints():
    if fp.GetReference() in ("TP1", "TP2"):
        fp.SetExcludedFromBOM(True)
        print("excluded from BOM:", fp.GetReference())
pcbnew.SaveBoard(str(BOARD), board)
print("saved")
