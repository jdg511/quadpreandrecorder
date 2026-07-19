r"""Import a Specctra SES route and add/fill the board ground pours.

Run with KiCad's bundled Python:
    C:\Program Files\KiCad\10.0\bin\python.exe tools/import_route.py
"""

from pathlib import Path
import shutil

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
UNROUTED = HARDWARE / "QuadPreRecorder.kicad_pcb"
SESSION = HARDWARE / "review_outputs" / "QuadPreRecorder-routed.ses"
UNROUTED_ARCHIVE = HARDWARE / "review_outputs" / "QuadPreRecorder-unrouted.kicad_pcb"
ROUTED = HARDWARE / "QuadPreRecorder.kicad_pcb"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def add_ground_zone(board: pcbnew.BOARD, layer: int, priority: int) -> pcbnew.ZONE:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(board.FindNet("/GND"))
    zone.SetZoneName("GND plane")
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(mm(0.20))
    zone.SetMinThickness(mm(0.20))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(mm(0.25))
    zone.SetThermalReliefSpokeWidth(mm(0.25))

    outline = zone.Outline()
    contour = outline.NewOutline()
    for x, y in ((0.5, 0.5), (109.5, 0.5), (109.5, 84.0), (0.5, 84.0)):
        outline.Append(mm(x), mm(y), contour)
    board.Add(zone)
    return zone


def main() -> None:
    if not SESSION.exists():
        raise FileNotFoundError(SESSION)

    shutil.copy2(UNROUTED, UNROUTED_ARCHIVE)
    board = pcbnew.LoadBoard(str(UNROUTED))
    if not pcbnew.ImportSpecctraSES(board, str(SESSION)):
        raise RuntimeError("Specctra SES import failed")

    add_ground_zone(board, pcbnew.B_Cu, 0)
    # A top pour provides short return paths around the codec and DAC while the
    # predominantly continuous bottom pour remains the primary ground plane.
    add_ground_zone(board, pcbnew.F_Cu, 0)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    pcbnew.SaveBoard(str(ROUTED), board)
    print(ROUTED)
    print(f"Tracks/vias: {len(list(board.GetTracks()))}; zones: {board.GetAreaCount()}")


if __name__ == "__main__":
    main()
