"""Apply final board-annotation visibility and refill zones.

Run with KiCad's bundled Python after any route import or field update.
"""

from pathlib import Path

import pcbnew

from generate_pcb import BOARD_H, BOARD_W


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
# 2026-07-25: vendor STEP overrides removed. They were merged with wrong
# rotations, which made the exported board STEP show connectors facing the
# wrong way (copper was fine for J1/J5/SW2; J4/RV1 copper is now fixed in
# generate_pcb.py). The stock KiCad library models are correctly aligned;
# keep the vendor STEPs in vendor_assets/ for standalone CAD work only.
LOCAL_3D_MODELS: dict[str, str] = {}


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def add_missing_fiducials(board: pcbnew.BOARD) -> None:
    existing = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    desired = [
        ("FID1", 10.0, 8.0, False),
        ("FID2", 130.0, 60.0, False),
        ("FID3", 50.0, 110.0, False),
        ("FID4", 12.0, 8.0, True),
        ("FID5", 126.0, 66.0, True),
        ("FID6", 60.0, 110.0, True),
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


def set_point_x(point: pcbnew.VECTOR2I, x_mm: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x_mm), point.y)


def move_board_edges(board: pcbnew.BOARD) -> None:
    """Keep the generated Hammond 1590F-fit outline unchanged."""

    return


def restore_left_chassis_route(board: pcbnew.BOARD) -> None:
    """Undo an over-eager DE-9 chassis move from earlier cleanup trials."""

    for track in board.GetTracks():
        if track.GetNetname() != "CHASSIS" or not hasattr(track, "GetStart"):
            continue
        start = track.GetStart()
        end = track.GetEnd()
        if abs(pcbnew.ToMM(start.x) - 0.75) < 0.02 and 43.0 <= pcbnew.ToMM(start.y) <= 48.0:
            track.SetStart(set_point_x(start, 0.5816))
        if abs(pcbnew.ToMM(end.x) - 0.75) < 0.02 and 43.0 <= pcbnew.ToMM(end.y) <= 48.0:
            track.SetEnd(set_point_x(end, 0.5816))


def move_connected_endpoint(track: pcbnew.PCB_TRACK, old: pcbnew.VECTOR2I, new: pcbnew.VECTOR2I) -> None:
    for getter, setter in ((track.GetStart, track.SetStart), (track.GetEnd, track.SetEnd)):
        point = getter()
        if abs(point.x - old.x) <= mm(0.02) and abs(point.y - old.y) <= mm(0.02):
            setter(new)


def restore_power_via(board: pcbnew.BOARD) -> None:
    """Return the +3V3_D via to the autorouter position before rerouting SPI."""

    old_points = [
        pcbnew.VECTOR2I(mm(84.7364), mm(64.5593)),
        pcbnew.VECTOR2I(mm(83.60), mm(63.60)),
    ]
    new = pcbnew.VECTOR2I(mm(84.7364), mm(64.5593))
    for track in board.GetTracks():
        if track.GetNetname() == "+3V3_D" and hasattr(track, "GetPosition"):
            point = track.GetPosition()
            if any(abs(point.x - old.x) <= mm(0.08) and abs(point.y - old.y) <= mm(0.08) for old in old_points):
                track.SetPosition(new)
        if track.GetNetname() == "+3V3_D" and hasattr(track, "GetStart"):
            for old in old_points:
                move_connected_endpoint(track, old, new)


def point_near(point: pcbnew.VECTOR2I, x: float, y: float, tol: float = 0.04) -> bool:
    return abs(pcbnew.ToMM(point.x) - x) <= tol and abs(pcbnew.ToMM(point.y) - y) <= tol


def set_track_points(track: pcbnew.PCB_TRACK, start: tuple[float, float], end: tuple[float, float]) -> None:
    track.SetStart(pcbnew.VECTOR2I(mm(start[0]), mm(start[1])))
    track.SetEnd(pcbnew.VECTOR2I(mm(end[0]), mm(end[1])))


def add_track(
    board: pcbnew.BOARD,
    netname: str,
    start: tuple[float, float],
    end: tuple[float, float],
    layer: int = pcbnew.F_Cu,
    width: float = 0.20,
) -> None:
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(mm(start[0]), mm(start[1])))
    track.SetEnd(pcbnew.VECTOR2I(mm(end[0]), mm(end[1])))
    track.SetLayer(layer)
    track.SetWidth(mm(width))
    net = board.FindNet(netname)
    if net is None:
        raise KeyError(netname)
    track.SetNet(net)
    board.Add(track)


def add_via(board: pcbnew.BOARD, netname: str, point: tuple[float, float], size: float = 0.80, drill: float = 0.40) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(mm(point[0]), mm(point[1])))
    via.SetWidth(mm(size))
    via.SetDrill(mm(drill))
    net = board.FindNet(netname)
    if net is None:
        raise KeyError(netname)
    via.SetNet(net)
    board.Add(via)


def track_exists(board: pcbnew.BOARD, netname: str, start: tuple[float, float], end: tuple[float, float]) -> bool:
    for track in board.GetTracks():
        if track.GetNetname() != netname or not hasattr(track, "GetStart"):
            continue
        points = ((track.GetStart(), track.GetEnd()), (track.GetEnd(), track.GetStart()))
        for point_start, point_end in points:
            if point_near(point_start, start[0], start[1]) and point_near(point_end, end[0], end[1]):
                return True
    return False


def add_headphone_amp_finish_routes(board: pcbnew.BOARD) -> None:
    """Finish small local connections Freerouting can leave open."""

    via_points: list[tuple[str, tuple[float, float]]] = []
    routes: list[tuple[str, int, list[tuple[float, float]]]] = []
    for netname, point in via_points:
        if not any(
            track.GetNetname() == netname
            and hasattr(track, "GetPosition")
            and point_near(track.GetPosition(), point[0], point[1])
            for track in board.GetTracks()
        ):
            add_via(board, netname, point)
    for netname, layer, points in routes:
        for start, end in zip(points, points[1:]):
            if not track_exists(board, netname, start, end):
                add_track(board, netname, start, end, layer=layer)


def remove_line_l_autoroute_spike(board: pcbnew.BOARD) -> None:
    """Remove Freerouting's LINE_L spike that shorts into GND near (93.6, 161.4).

    The autorouter deterministically emits a ~0.9 mm U-turn detour in LINE_L
    (five segments, one of them 0.0001 mm long) whose tip crosses a GND trace.
    Delete every LINE_L F.Cu segment fully inside the spike box and, if any
    were removed, bridge the two remaining path ends with one direct segment.
    Idempotent: on a clean board nothing matches and nothing is added.
    """

    box = (93.50, 161.30, 93.78, 162.30)
    removed = []
    for track in list(board.GetTracks()):
        if track.GetNetname() != "LINE_L" or not hasattr(track, "GetStart"):
            continue
        if track.GetLayer() != pcbnew.F_Cu:
            continue
        inside = True
        for point in (track.GetStart(), track.GetEnd()):
            x, y = pcbnew.ToMM(point.x), pcbnew.ToMM(point.y)
            if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
                inside = False
        if inside:
            removed.append(track)
    for track in removed:
        board.Delete(track)
    if removed and not track_exists(board, "LINE_L", (93.5330, 162.2164), (93.7283, 162.2570)):
        add_track(board, "LINE_L", (93.5330, 162.2164), (93.7283, 162.2570), layer=pcbnew.F_Cu)
    if removed:
        print(f"LINE_L spike: removed {len(removed)} segment(s), rebridged")


def apply_local_3d_models(board: pcbnew.BOARD) -> None:
    for ref, model_path in LOCAL_3D_MODELS.items():
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            continue
        models = footprint.Models()
        if len(models) == 0:
            model = pcbnew.FP_3DMODEL()
            model.m_Filename = model_path
            models.append(model)
        else:
            models[0].m_Filename = model_path


def reroute_spi_mosi_around_power_via(board: pcbnew.BOARD) -> None:
    """Shift the SPI_MOSI jog right of the +3V3_D via to clear the short."""

    edits: list[tuple[pcbnew.PCB_TRACK, tuple[float, float], tuple[float, float]]] = []
    for track in board.GetTracks():
        if track.GetNetname() != "SPI_MOSI" or not hasattr(track, "GetStart"):
            continue
        start = track.GetStart()
        end = track.GetEnd()
        if (
            point_near(start, 86.1295, 61.1483)
            and (point_near(end, 84.8983, 62.3795) or point_near(end, 85.85, 61.43))
        ):
            edits.append((track, (86.1295, 61.1483), (89.20, 61.1483)))
        elif (
            (point_near(start, 84.8983, 62.3795) and point_near(end, 84.8983, 64.1205))
            or (point_near(start, 85.85, 61.43) and point_near(end, 85.85, 65.2111))
        ):
            edits.append((track, (89.20, 61.1483), (89.20, 65.2111)))
        elif (
            (point_near(start, 84.8983, 64.1205) and point_near(end, 85.3925, 64.6147))
            or (point_near(start, 85.85, 65.2111) and point_near(end, 85.0347, 65.2111))
        ):
            edits.append((track, (89.20, 65.2111), (85.0347, 65.2111)))
        elif (
            point_near(start, 85.3925, 64.6147)
            or point_near(end, 85.3925, 64.8533)
            or point_near(start, 85.10, 65.2111)
            or point_near(end, 85.10, 65.2111)
        ):
            edits.append((track, (85.0347, 65.2111), (85.0347, 65.2111)))
        elif point_near(start, 85.0347, 65.2111):
            track.SetStart(pcbnew.VECTOR2I(mm(85.0347), mm(65.2111)))
        elif point_near(end, 85.0347, 65.2111):
            track.SetEnd(pcbnew.VECTOR2I(mm(85.0347), mm(65.2111)))
    for track, start, end in edits:
        set_track_points(track, start, end)


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    add_missing_fiducials(board)
    move_board_edges(board)
    # Rev B: the Rev A coordinate-specific route fixups (chassis route,
    # power via, SPI_MOSI jog, LINE_L spike) target 1590F-board coordinates
    # and must not fire on the 138x114 Rev B board.
    add_headphone_amp_finish_routes(board)
    apply_local_3d_models(board)
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
