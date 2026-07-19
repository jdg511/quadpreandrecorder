#!/usr/bin/env python3
"""Generate the compact two-layer QuadPreRecorder PCB placement.

Run with KiCad's bundled Python interpreter:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools/generate_pcb.py

Routing is intentionally a separate reproducible step.  This script writes the
placed board and a Specctra DSN used by ``tools/route_pcb.ps1``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
OUT = HARDWARE / "QuadPreRecorder.kicad_pcb"
DSN = HARDWARE / "review_outputs" / "QuadPreRecorder-unrouted.dsn"
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
LOCAL_FP_ROOT = HARDWARE / "QuadPreRecorder.pretty"

BOARD_W = 110.0
BOARD_H = 84.5
TFT_LEFT = 5.0
TFT_TOP = 17.25
TFT_W = 86.0
TFT_H = 50.0


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def pos(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def load_design_parts():
    sys.path.insert(0, str(ROOT / "tools"))
    import generate_schematic as schematic  # pylint: disable=import-outside-toplevel

    merged = {}
    for item in schematic.build_parts():
        if not item.on_board:
            continue
        if item.ref in merged:
            prior = merged[item.ref]
            pins = dict(prior.pins)
            pins.update(item.pins)
            merged[item.ref] = replace(prior, pins=pins)
        else:
            merged[item.ref] = item
    return merged


def schematic_paths() -> dict[str, str]:
    """Return the first root-sheet symbol UUID for each production reference."""

    text = (HARDWARE / "QuadPreRecorder.kicad_sch").read_text(encoding="utf-8")
    pattern = re.compile(
        r'\(symbol\s+\(lib_id "[^"]+"\).*?\(uuid "([^"]+)"\).*?'
        r'\(property "Reference" "([^"]+)"',
        re.DOTALL,
    )
    result: dict[str, str] = {}
    for uuid, reference in pattern.findall(text):
        if not reference.startswith("#"):
            result.setdefault(reference, uuid)
    return result


def schematic_pad_nets() -> dict[tuple[str, str], str]:
    """Read KiCad's exported netlist as the board's pin-to-net authority."""

    netlist_path = HARDWARE / "review_outputs" / "QuadPreRecorder.net"
    text = netlist_path.read_text(encoding="utf-8")
    mapping: dict[tuple[str, str], str] = {}
    cursor = text.find("\n\t(nets")
    while True:
        start = text.find("\n\t\t(net", cursor)
        if start < 0:
            break
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index in range(start + 1, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise RuntimeError("Unbalanced netlist net block")
        block = text[start + 1:end]
        name_match = re.search(r'\(name "([^"]+)"\)', block)
        if name_match:
            netname = name_match.group(1)
            for reference, pin in re.findall(
                r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)',
                block,
                re.DOTALL,
            ):
                mapping[(reference, pin)] = netname
        cursor = end
    if not mapping:
        raise RuntimeError("No pin nets parsed from exported KiCad netlist")
    return mapping


def placements() -> dict[str, tuple[float, float, float, bool]]:
    """Return reference -> x, y, rotation, bottom-side placement."""

    place: dict[str, tuple[float, float, float, bool]] = {
        # Board-mounted enclosure interfaces.
        "J2": (1.8, 37.4, 90.0, False),
        "J1": (108.0, 77.0, 270.0, False),
        "J4": (83.5, 56.5, 0.0, True),
        "J5": (104.2, 66.5, 270.0, False),
        "SW1": (12.0, 8.0, 0.0, False),
        "SW2": (27.0, 7.0, 0.0, False),
        "SW3": (46.0, 7.0, 0.0, False),
        "RV1": (102.0, 5.0, 90.0, False),
        "J3": (75.0, 19.0, 270.0, False),
        # Teensy is socketed on the bottom so the TFT can occupy the lid side.
        "U8": (24.0, 63.0, 270.0, True),

        # Power entry and conversion, kept in the lower-left power region.
        "F1": (7.0, 78.0, 0.0, False),
        "D1": (14.0, 78.0, 0.0, False),
        "D2": (21.5, 78.0, 0.0, False),
        "C1": (34.0, 76.0, 0.0, False),
        "C2": (20.5, 73.5, 0.0, False),
        "C3": (26.0, 72.5, 0.0, False),
        "U1": (8.0, 68.5, 0.0, False),
        "L1": (14.5, 68.5, 0.0, False),
        "R1": (7.0, 73.0, 0.0, False),
        "R2": (10.0, 73.0, 0.0, False),
        "C4": (13.0, 73.0, 0.0, False),
        "C5": (20.0, 68.5, 0.0, False),
        "C6": (25.0, 68.5, 0.0, False),
        "R3": (16.5, 73.0, 0.0, False),

        # Bias reference and quiet analog regulator.
        "U3": (35.0, 51.0, 0.0, False),
        "C9": (32.5, 56.0, 0.0, False),
        "C10": (37.0, 56.0, 0.0, False),
        "C11": (41.5, 56.0, 0.0, False),
        "U2": (70.0, 52.0, 0.0, False),
        "C7": (66.5, 55.0, 0.0, False),
        "C8": (72.5, 55.0, 0.0, False),

        # Chassis coupling and four input ESD parts beside the DE-9.
        "R4": (24.0, 52.0, 90.0, False),
        "C12": (27.0, 52.0, 90.0, False),
        "R5": (30.0, 52.0, 90.0, False),
        "D6": (23.5, 22.5, 90.0, False),
        "D7": (23.5, 28.5, 90.0, False),
        "D8": (23.5, 34.5, 90.0, False),
        "D9": (23.5, 40.5, 90.0, False),

        # Shared pad mux, JFET preamp, and ADC.
        "U4": (54.0, 25.5, 0.0, False),
        "U5": (54.0, 37.5, 0.0, False),
        "U6": (63.0, 31.5, 0.0, False),
        "U7": (90.0, 31.5, 0.0, False),
        "C34": (54.0, 21.5, 0.0, True),
        "C35": (54.0, 42.0, 0.0, True),
        "C36": (61.0, 24.5, 0.0, True),
        "C37": (65.0, 24.5, 0.0, True),

        # Pad sense near its panel switch.
        "R42": (17.0, 17.0, 0.0, False),
        "R43": (20.0, 17.0, 0.0, False),
        "C33": (23.0, 17.0, 0.0, False),

        # ADC decoupling and clock/control damping.
        "C38": (80.0, 18.0, 0.0, True),
        "C39": (80.0, 22.0, 0.0, True),
        "C40": (80.0, 26.0, 0.0, True),
        "C41": (96.0, 20.0, 0.0, True),
        "C42": (96.0, 24.0, 0.0, True),
        "C43": (96.0, 32.0, 0.0, True),
        "C44": (96.0, 36.0, 0.0, True),
        "C45": (96.0, 40.0, 0.0, True),
        "C62": (100.0, 34.0, 0.0, True),
        "C63": (100.0, 40.0, 0.0, True),
        "R44": (80.5, 14.0, 0.0, True),
        "R45": (83.5, 14.0, 0.0, True),
        "R46": (86.5, 14.0, 0.0, True),
        "R47": (89.5, 14.0, 0.0, True),
        "R48": (92.5, 14.0, 0.0, True),
        "R49": (95.5, 14.0, 0.0, True),

        # Teensy power feed and recorder/user-interface conditioning.
        "D3": (32.0, 68.0, 0.0, False),
        "C46": (39.0, 68.0, 0.0, False),
        "R50": (28.0, 18.0, 0.0, True),
        "C47": (31.0, 18.0, 0.0, True),
        "R51": (45.0, 26.0, 0.0, True),
        "R52": (48.0, 26.0, 0.0, True),
        "R53": (51.0, 26.0, 0.0, True),
        "C48": (45.0, 30.0, 0.0, True),
        "C49": (48.0, 30.0, 0.0, True),
        "C50": (51.0, 30.0, 0.0, True),
        "D4": (66.0, 8.0, 0.0, False),
        "R54": (69.0, 8.0, 0.0, False),
        "D5": (73.0, 8.0, 0.0, False),
        "R55": (76.0, 8.0, 0.0, False),
        "R56": (79.0, 16.0, 0.0, False),

        # DAC and headphone circuitry above the right-edge jacks.
        "U9": (53.0, 55.0, 0.0, False),
        "C51": (47.0, 49.0, 0.0, False),
        "C52": (50.5, 48.0, 0.0, False),
        "C53": (54.0, 48.0, 0.0, False),
        "C54": (57.5, 48.0, 0.0, False),
        "C55": (61.5, 48.0, 0.0, False),
        "C56": (47.0, 59.5, 0.0, False),
        "C64": (51.0, 59.5, 0.0, False),
        "R57": (57.0, 60.0, 0.0, True),
        "R58": (60.0, 60.0, 0.0, True),
        "R59": (63.0, 60.0, 0.0, True),
        "R60": (66.0, 60.0, 0.0, True),
        "R61": (69.0, 60.0, 0.0, True),
        "R62": (72.0, 60.0, 0.0, True),
        "R63": (75.0, 58.5, 0.0, False),
        "C57": (83.5, 69.0, 0.0, False),
        "C58": (87.0, 69.0, 0.0, False),
        "U10": (88.0, 75.0, 0.0, False),
        "C59": (83.5, 73.0, 90.0, False),
        "C60": (83.5, 77.0, 90.0, False),
        "C61": (92.0, 73.0, 90.0, False),
        "C65": (92.0, 77.0, 90.0, False),
        "R64": (80.0, 68.0, 0.0, False),
        "R65": (87.5, 80.0, 0.0, False),
        "R66": (91.0, 80.0, 0.0, False),
    }

    # Four matched signal rows.  Values are kept in identical X positions to
    # make the physical channel symmetry visible and reviewable.
    channel_rows = (22.5, 28.5, 34.5, 40.5)
    for index, y in enumerate(channel_rows):
        channel = index + 1
        input_refs = (
            (f"R{5 + channel}", 27.0),
            (f"R{9 + channel}", 30.0),
            (f"C{12 + channel}", 33.0),
            (f"C{16 + channel}", 37.0),
            (f"R{13 + channel}", 41.0),
            (f"R{18 + 2 * index}", 45.0),
            (f"R{19 + 2 * index}", 49.0),
        )
        output_refs = (
            (f"R{26 + index}", 58.5),
            (f"R{30 + index}", 68.5),
            (f"C{21 + index}", 71.5),
            (f"C{25 + index}", 75.0),
            (f"R{34 + index}", 79.0),
            (f"C{29 + index}", 82.0),
            (f"R{38 + index}", 85.0),
        )
        for ref, x in input_refs + output_refs:
            bottom = bool(re.fullmatch(r"R(?:2[6-9]|3[0-3]|3[8-9]|4[0-1])|C2[1-4]", ref))
            place[ref] = (x, y, 90.0, bottom)
    place["R38"] = (82.0, 30.0, 90.0, True)
    place["C25"] = (75.0, 24.0, 90.0, True)
    return place


def add_segment(board: pcbnew.BOARD, layer: int, start: tuple[float, float], end: tuple[float, float], width: float = 0.15) -> None:
    line = pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(pos(*start))
    line.SetEnd(pos(*end))
    line.SetLayer(layer)
    line.SetWidth(mm(width))
    board.Add(line)


def add_rect(board: pcbnew.BOARD, layer: int, left: float, top: float, right: float, bottom: float, width: float = 0.15) -> None:
    points = ((left, top), (right, top), (right, bottom), (left, bottom))
    for start, end in zip(points, points[1:] + points[:1]):
        add_segment(board, layer, start, end, width)


def add_text(board: pcbnew.BOARD, value: str, x: float, y: float, size: float = 1.0, layer: int = pcbnew.F_SilkS) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(pos(x, y))
    item.SetLayer(layer)
    size = max(size, 0.8)
    item.SetTextSize(pos(size, size))
    item.SetTextThickness(mm(0.15))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    if layer == pcbnew.B_SilkS:
        item.SetMirrored(True)
    board.Add(item)


def footprint_library_path(library: str) -> Path:
    if library == "QuadPreRecorder":
        return LOCAL_FP_ROOT
    return FP_ROOT / f"{library}.pretty"


def add_mounting_hole(board: pcbnew.BOARD, ref: str, x: float, y: float, value: str) -> None:
    fp = pcbnew.FootprintLoad(str(FP_ROOT / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
    if fp is None:
        raise FileNotFoundError("MountingHole:MountingHole_3.2mm_M3")
    fp.SetFPIDAsString("MountingHole:MountingHole_3.2mm_M3")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pos(x, y))
    fp.SetBoardOnly(True)
    fp.SetExcludedFromBOM(True)
    fp.SetExcludedFromPosFiles(True)
    board.Add(fp)


def add_fiducial(board: pcbnew.BOARD, ref: str, x: float, y: float, bottom: bool) -> None:
    fp = pcbnew.FootprintLoad(str(FP_ROOT / "Fiducial.pretty"), "Fiducial_1mm_Mask2mm")
    if fp is None:
        raise FileNotFoundError("Fiducial:Fiducial_1mm_Mask2mm")
    fp.SetFPIDAsString("Fiducial:Fiducial_1mm_Mask2mm")
    fp.SetReference(ref)
    fp.SetValue("Fiducial 1mm")
    fp.SetPosition(pos(x, y))
    fp.SetBoardOnly(True)
    fp.SetExcludedFromBOM(True)
    fp.SetExcludedFromPosFiles(True)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    board.Add(fp)
    if bottom:
        fp.Flip(fp.GetPosition(), False)


def build_board() -> pcbnew.BOARD:
    parts = load_design_parts()
    paths = schematic_paths()
    pad_nets = schematic_pad_nets()
    place = placements()
    missing = sorted(set(parts) - set(place))
    extra = sorted(set(place) - set(parts))
    if missing or extra:
        raise RuntimeError(f"placement mismatch; missing={missing}, extra={extra}")

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    title = board.GetTitleBlock()
    title.SetTitle("Quad Preamp and 4-Channel Ambisonic Recorder")
    title.SetCompany("jdg511")
    title.SetComment(0, "https://github.com/jdg511/quadpreandrecorder")
    title.SetComment(1, "Hammond 1590BB2 / two copper layers / Rev A prototype")
    title.SetRevision("A")
    title.SetDate("2026-07-19")

    settings = board.GetDesignSettings()
    settings.m_MinClearance = mm(0.15)
    settings.m_TrackMinWidth = mm(0.20)
    settings.m_ViasMinSize = mm(0.80)
    settings.SetCustomTrackWidth(mm(0.25))
    settings.SetCustomViaSize(mm(0.80))
    settings.SetCustomViaDrill(mm(0.40))
    default_class = settings.m_NetSettings.GetDefaultNetclass()
    default_class.SetClearance(mm(0.15))
    default_class.SetTrackWidth(mm(0.20))
    default_class.SetViaDiameter(mm(0.80))
    default_class.SetViaDrill(mm(0.40))

    add_rect(board, pcbnew.Edge_Cuts, 0.0, 0.0, BOARD_W, BOARD_H)
    add_rect(board, pcbnew.Dwgs_User, TFT_LEFT, TFT_TOP, TFT_LEFT + TFT_W, TFT_TOP + TFT_H, 0.20)
    add_text(board, "2.8in TFT MODULE ENVELOPE - VERIFY MODULE", 48.0, 65.0, 0.8, pcbnew.Dwgs_User)

    net_names = sorted({net for (ref, _), net in pad_nets.items() if ref in parts})
    nets = {}
    for netname in net_names:
        net = pcbnew.NETINFO_ITEM(board, netname)
        board.Add(net)
        nets[netname] = net

    for ref, item in parts.items():
        library, footprint_name = item.footprint.split(":", 1)
        fp = pcbnew.FootprintLoad(str(footprint_library_path(library)), footprint_name)
        if fp is None:
            raise FileNotFoundError(item.footprint)
        fp.SetFPIDAsString(item.footprint)
        fp.SetReference(ref)
        fp.SetValue(item.value)
        fp.SetField("Manufacturer", item.manufacturer)
        fp.SetField("MPN", item.mpn)
        fp.SetField("Datasheet", "" if item.datasheet == "~" else item.datasheet)
        fp.SetField("Description", item.description)
        for field_name in ("Manufacturer", "MPN", "Datasheet", "Description"):
            fp.GetField(field_name).SetVisible(False)
        x, y, rotation, bottom = place[ref]
        fp.SetPosition(pos(x, y))
        fp.SetSheetname("/")
        fp.SetSheetfile("QuadPreRecorder.kicad_sch")
        if ref not in paths:
            raise RuntimeError(f"No schematic UUID found for {ref}")
        fp.SetPath(pcbnew.KIID_PATH(paths[ref]))
        fp.Reference().SetVisible(True)
        fp.Value().SetVisible(False)
        if item.dnp:
            fp.SetDNP(True)
        board.Add(fp)
        if bottom:
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(rotation)
        for pad in fp.Pads():
            netname = pad_nets.get((ref, pad.GetNumber()))
            if netname is not None:
                pad.SetNet(nets[netname])

    # Main-PCB and generic 78 x 42 mm TFT mounting patterns.
    for ref, x, y in (
        ("H1", 4.0, 4.0), ("H2", 92.0, 4.0),
        ("H5", 9.0, 21.25), ("H6", 87.0, 21.25),
        ("H7", 9.0, 63.25), ("H8", 87.0, 63.25),
    ):
        add_mounting_hole(board, ref, x, y, "M3 PCB" if ref < "H5" else "M3 TFT 78x42")

    for index, (x, y) in enumerate(((80.0, 5.0), (106.0, 34.0), (98.0, 50.0)), start=1):
        add_fiducial(board, f"FID{index}", x, y, False)
    for index, (x, y) in enumerate(((80.0, 5.0), (10.0, 78.0), (96.0, 80.0)), start=4):
        add_fiducial(board, f"FID{index}", x, y, True)

    # Enclosure-facing labels and setup warnings.
    add_text(board, "PAD", 14.0, 13.0, 0.75)
    add_text(board, "REC", 33.0, 13.0, 0.75)
    add_text(board, "GAIN", 53.0, 13.0, 0.75)
    add_text(board, "PWR", 67.5, 11.0, 0.65)
    add_text(board, "REC", 74.5, 11.0, 0.65)
    add_text(board, "TFT 1..14", 60.0, 13.0, 0.65)
    add_text(board, "MIC DE-9", 8.0, 46.0, 0.75)
    add_text(board, "LINE", 105.0, 47.0, 0.70)
    add_text(board, "HP", 105.0, 61.0, 0.70)
    add_text(board, "9VDC", 104.0, 73.0, 0.70)
    add_text(board, "jdg511  QUAD PRE RECORDER  REV A", 55.0, 82.0, 0.75)
    add_text(board, "TEENSY 4.1 ON BOTTOM - CUT VIN/VUSB FOR DUAL POWER", 56.0, 76.0, 0.65, pcbnew.B_SilkS)

    board.BuildListOfNets()
    return board


def report_overlaps(board: pcbnew.BOARD) -> None:
    footprints = [fp for fp in board.GetFootprints() if not fp.GetReference().startswith("H")]
    overlaps = []
    for index, first in enumerate(footprints):
        a = first.GetBoundingBox(False, False)
        for second in footprints[index + 1:]:
            if first.GetLayer() != second.GetLayer():
                continue
            b = second.GetBoundingBox(False, False)
            if a.Intersects(b):
                overlaps.append((first.GetReference(), second.GetReference()))
    print(f"Same-side courtyard/bounding-box overlaps: {len(overlaps)}")
    if overlaps:
        print(" ".join(f"{a}-{b}" for a, b in overlaps[:80]))


def main() -> None:
    HARDWARE.mkdir(parents=True, exist_ok=True)
    DSN.parent.mkdir(parents=True, exist_ok=True)
    board = build_board()
    pcbnew.SaveBoard(str(OUT), board)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise RuntimeError("Specctra DSN export failed")
    report_overlaps(board)
    print(OUT)
    print(DSN)
    print(f"Board: {BOARD_W:.1f} x {BOARD_H:.1f} mm, footprints: {len(list(board.GetFootprints()))}")


if __name__ == "__main__":
    main()
