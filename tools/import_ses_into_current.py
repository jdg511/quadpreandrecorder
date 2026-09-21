"""Replace the current board's wiring with a Specctra SES (all existing wiring was
exported protected, so the SES carries it back unchanged plus the new routes).
The old tracks are stripped from the file text first: removing 3000+ items through
pcbnew's board.Remove() in a loop has crashed the interpreter before."""
import re, sys
from pathlib import Path
import pcbnew
ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
SES = Path(sys.argv[1])
text = BOARD.read_text(encoding="utf-8")
stripped, n = re.subn(r"\n\t\((segment|via)\n(?:\t\t[^\n]*\n)+\t\)", "", text)
print("stripped", n, "segment/via blocks from the file")
BOARD.write_text(stripped, encoding="utf-8")
board = pcbnew.LoadBoard(str(BOARD))
before = len(list(board.GetTracks()))
if not pcbnew.ImportSpecctraSES(board, str(SES)):
    raise SystemExit("SES import failed")
after = len(list(board.GetTracks()))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(BOARD), board)
print("tracks/vias before %d, after import %d" % (before, after))
