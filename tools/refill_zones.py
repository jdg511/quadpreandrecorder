"""Refill every zone and save (poly_route & co. do not refill; DRC then sees the stale pour)."""
import sys
from pathlib import Path
import pcbnew
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp
board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(sp.BOARD_PATH), board)
print("zones refilled:", len(board.Zones()))
