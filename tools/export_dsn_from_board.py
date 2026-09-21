"""Export a Specctra DSN from the board as it stands, wiring and all.

Used for a finishing pass: everything already routed gets marked protected by
protect_fanout.py, so Freerouting only has the leftovers to solve.
"""
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
DSN = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / "hardware" / "review_outputs" / "QuadPreRecorder-finish.dsn")

board = pcbnew.LoadBoard(str(BOARD))
tracks = len(list(board.GetTracks()))
if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
    raise SystemExit("Specctra DSN export failed")
print("exported %d tracks/vias" % tracks)
print(DSN)
