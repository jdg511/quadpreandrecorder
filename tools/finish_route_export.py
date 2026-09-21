r"""Rev B helper (2026-09-06): export the partially routed board to a Specctra
DSN so Freerouting can finish the remaining connections.

Freerouting 2.2.4 reports the board fully routed but its .ses omits the wires
of ~10 nets (109 of 119 nets exported), so the first import_route.py pass lands
with a couple of dozen unconnected pads.  Re-exporting the imported board (with
its existing tracks as fixed wiring, zones stripped) and routing again finishes
only the missing connections.

Run with KiCad's bundled Python:
    python.exe tools/finish_route_export.py
Then:
    java -jar tools/cache/freerouting-2.2.4.jar -de hardware/review_outputs/QuadPreRecorder-partial.dsn \
        -do hardware/review_outputs/QuadPreRecorder-partial.ses --gui.enabled=false -mp 200 -mt 12 -da
    copy partial.kicad_pcb -> hardware/QuadPreRecorder.kicad_pcb, partial.ses -> QuadPreRecorder-routed.ses
    python.exe tools/import_route.py ; python.exe tools/cleanup_board.py ; kicad-cli pcb drc ...
"""
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
BOARD = HARDWARE / "QuadPreRecorder.kicad_pcb"
PARTIAL = HARDWARE / "review_outputs" / "QuadPreRecorder-partial.kicad_pcb"
DSN = HARDWARE / "review_outputs" / "QuadPreRecorder-partial.dsn"


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD))
    zones = list(board.Zones())
    for zone in zones:
        # keep rule areas (edge keepouts); drop copper pours
        if zone.GetIsRuleArea():
            continue
        board.Delete(zone)
    n_tracks = len(list(board.GetTracks()))
    pcbnew.SaveBoard(str(PARTIAL), board)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise RuntimeError("DSN export failed")
    print(f"saved {PARTIAL} ({n_tracks} tracks/vias, {board.GetAreaCount()} zones kept)")
    print(f"exported {DSN}")


if __name__ == "__main__":
    main()
