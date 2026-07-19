"""Apply final board-annotation visibility and refill zones.

Run with KiCad's bundled Python after any route import or field update.
"""

from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def add_missing_fiducials(board: pcbnew.BOARD) -> None:
    existing = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    desired = [
        ("FID1", 80.0, 5.0, False),
        ("FID2", 106.0, 34.0, False),
        ("FID3", 98.0, 50.0, False),
        ("FID4", 80.0, 5.0, True),
        ("FID5", 10.0, 78.0, True),
        ("FID6", 96.0, 80.0, True),
    ]
    for ref, x, y, bottom in desired:
        if ref in existing:
            footprint = existing[ref]
        else:
            footprint = pcbnew.FootprintLoad(str(FP_ROOT / "Fiducial.pretty"), "Fiducial_1mm_Mask2mm")
            if footprint is None:
                raise FileNotFoundError("Fiducial:Fiducial_1mm_Mask2mm")
            footprint.SetFPIDAsString("Fiducial:Fiducial_1mm_Mask2mm")
            footprint.SetReference(ref)
            footprint.SetValue("Fiducial 1mm")
            footprint.SetBoardOnly(True)
            footprint.SetExcludedFromBOM(True)
            footprint.SetExcludedFromPosFiles(True)
            board.Add(footprint)
        footprint.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        is_bottom = footprint.GetLayer() == pcbnew.B_Cu
        if bottom != is_bottom:
            footprint.Flip(footprint.GetPosition(), False)


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    add_missing_fiducials(board)
    for footprint in board.GetFootprints():
        is_fiducial = footprint.GetReference().startswith("FID")
        footprint.Reference().SetVisible(not is_fiducial)
        footprint.Value().SetVisible(False)
        for field_name in ("Manufacturer", "MPN", "Datasheet", "Description", "KiLib_Generator"):
            if footprint.HasField(field_name):
                footprint.GetField(field_name).SetVisible(False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
