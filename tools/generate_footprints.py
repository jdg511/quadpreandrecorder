#!/usr/bin/env python3
"""Generate project-local mechanical/module footprints with KiCad pcbnew."""

from pathlib import Path
import pcbnew


ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
LIBRARY = HARDWARE / "QuadPreRecorder.pretty"
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def pos(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def add_line(fp: pcbnew.FOOTPRINT, x1: float, y1: float, x2: float, y2: float, layer: int, width: float = 0.25) -> None:
    line = pcbnew.PCB_SHAPE(fp)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(pos(x1, y1))
    line.SetEnd(pos(x2, y2))
    line.SetLayer(layer)
    line.SetWidth(mm(width))
    fp.Add(line)


def add_th_pad(fp: pcbnew.FOOTPRINT, number: str, x: float, y: float, *, square: bool = False) -> None:
    pad = pcbnew.PAD(fp)
    pad.SetNumber(number)
    pad.SetPosition(pos(x, y))
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT if square else pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mm(1.80), mm(1.80)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(1.00), mm(1.00)))
    pad.SetLayerSet(pad.PTHMask())
    fp.Add(pad)


def teensy41_socket() -> pcbnew.FOOTPRINT:
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPIDAsString("QuadPreRecorder:Teensy41_Socket")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetLibDescription("PJRC Teensy 4.1 carrier footprint, two 1x24 2.54 mm socket rows; USB at y=-1.27, microSD at y=59.69")
    fp.SetKeywords("Teensy 4.1 PJRC module SDIO")

    left = ["GND1", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "3V3A", "24", "25", "26", "27", "28", "29", "30", "31", "32"]
    right = ["VIN", "GND2", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13", "41", "40", "39", "38", "37", "36", "35", "34", "33", "GND3", "3V3B"]
    for index, number in enumerate(left):
        add_th_pad(fp, number, 0.0, index * 2.54, square=(index == 0))
    for index, number in enumerate(right):
        add_th_pad(fp, number, 17.78, index * 2.54)

    # Nominal 61.0 x 17.8 mm module body and connector-end references.
    for x1, y1, x2, y2 in ((-1.27, -1.27, 19.05, -1.27), (19.05, -1.27, 19.05, 59.69),
                            (19.05, 59.69, -1.27, 59.69), (-1.27, 59.69, -1.27, -1.27)):
        add_line(fp, x1, y1, x2, y2, pcbnew.F_Fab, 0.20)
        add_line(fp, x1, y1, x2, y2, pcbnew.F_SilkS, 0.20)
    add_line(fp, -1.27, 2.0, 19.05, 2.0, pcbnew.F_SilkS, 0.20)
    add_line(fp, -1.27, 56.5, 19.05, 56.5, pcbnew.F_SilkS, 0.20)

    fp.Reference().SetText("REF**")
    fp.Reference().SetPosition(pos(8.89, 28.0))
    fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetText("Teensy41_Socket")
    fp.Value().SetPosition(pos(8.89, 31.0))
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


def rk097_no_edge_guide() -> pcbnew.FOOTPRINT:
    """Project copy of RK097 without the stock open board-edge guide."""

    fp = pcbnew.FootprintLoad(
        str(FP_ROOT / "Potentiometer_THT.pretty"),
        "Potentiometer_Alps_RK097_Dual_Horizontal",
    )
    if fp is None:
        raise FileNotFoundError("Potentiometer_Alps_RK097_Dual_Horizontal")
    for graphic in list(fp.GraphicalItems()):
        if graphic.GetLayer() == pcbnew.Edge_Cuts:
            fp.Remove(graphic)
    fp.SetFPIDAsString("QuadPreRecorder:RK097_Dual_Horizontal_NoEdgeGuide")
    fp.SetLibDescription(
        "Alps RK097 dual horizontal potentiometer; board-edge guide removed because the project owns the closed outline"
    )
    return fp


def eswitch_100sp_m7() -> pcbnew.FOOTPRINT:
    """E-Switch 100SP1T1B1M7 right-angle toggle, bushing toward -X at 0 deg.

    Geometry from the E-Switch 100-series catalog and per-part 2D drawing
    (100SP1T1B1M7QE): bracket prong holes at (0, +/-2.54); terminals in a line
    behind the body at x = 12.70 (pin 1), 16.51 (pin 2, common), 20.32 (pin 3);
    all holes recommended 1.85 mm. Body 12.70 long x 6.86 tall lying on its
    side; 1/4-40 bushing 8.89 mm long extends past x = 0 through the wall.
    Centerline ~6.35 mm above the board.
    """

    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPIDAsString("QuadPreRecorder:SW_Toggle_ESwitch_100SP_M7")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetLibDescription(
        "E-Switch 100SP1T1B1M7 SPDT right-angle PCB toggle; 1/4-40 x 8.89mm "
        "threaded bushing pointing -X for through-wall mounting"
    )
    fp.SetKeywords("toggle SPDT right-angle bushing E-Switch 100SP")

    def th(number: str, x: float, y: float) -> None:
        pad = pcbnew.PAD(fp)
        pad.SetNumber(number)
        pad.SetPosition(pos(x, y))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(mm(2.80), mm(2.80)))
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(1.85), mm(1.85)))
        pad.SetLayerSet(pad.PTHMask())
        fp.Add(pad)

    th("1", 12.70, 0.0)
    th("2", 16.51, 0.0)
    th("3", 20.32, 0.0)
    th("MP", 0.0, -2.54)
    th("MP", 0.0, 2.54)

    for layer in (pcbnew.F_Fab, pcbnew.F_SilkS):
        # Body on its side behind the bracket plate.
        for x1, y1, x2, y2 in (
            (0.0, -3.43, 12.70, -3.43), (12.70, -3.43, 12.70, 3.43),
            (12.70, 3.43, 0.0, 3.43), (0.0, 3.43, 0.0, -3.43),
            # Bracket plate.
            (0.0, -6.35, 0.0, 6.35),
            # Threaded bushing extending toward the board edge / wall.
            (0.0, -3.18, -8.89, -3.18), (-8.89, -3.18, -8.89, 3.18),
            (-8.89, 3.18, 0.0, 3.18),
        ):
            add_line(fp, x1, y1, x2, y2, layer, 0.15 if layer == pcbnew.F_Fab else 0.20)

    crt = pcbnew.PCB_SHAPE(fp)
    crt.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    crt.SetStart(pos(-9.40, -6.90))
    crt.SetEnd(pos(21.80, 6.90))
    crt.SetLayer(pcbnew.F_CrtYd)
    crt.SetWidth(mm(0.05))
    fp.Add(crt)

    fp.Reference().SetText("REF**")
    fp.Reference().SetPosition(pos(10.0, -5.2))
    fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetText("SW_Toggle_ESwitch_100SP_M7")
    fp.Value().SetPosition(pos(10.0, 5.2))
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


def alps_skqucaa010() -> pcbnew.FOOTPRINT:
    """ALPS SKQUCAA010 4-direction + center-push nav switch, snap-in THT.

    Geometry from the ALPS SKQU catalog drawing No.3 (snap-in, with center
    push): 10 mm square body, stem to 10 mm above the PCB; two terminal
    columns 6.5 mm apart, outer (corner) pins at +/-5.15 mm needing 1.2 mm
    holes (0.9 mm snap-in legs), middle pins 0.7 mm wide needing 1.0 mm holes
    and offset ~0.45 mm from center. The middle-pin holes are slotted here so
    either catalog keying direction fits - VERIFY against the physical part.
    Pin map per catalog circuit: 1=A(up) 2=B(left) 3=C(down) 4=Common
    5=D(right) 6=Center. Direction pins are firmware-remappable, but 4/6 are
    corner pins: populate with the silk arrow (A) toward board north - a
    180-degree insertion swaps Common onto pin 1 and is NOT recoverable.
    Stem rotation center is ~1.23 mm off the pattern center per the drawing.
    """

    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPIDAsString("QuadPreRecorder:SW_Nav_ALPS_SKQUCAA010")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetLibDescription(
        "ALPS SKQUCAA010 4-directional + center push TACT switch, snap-in; "
        "1=A/up 2=B/left 3=C/down 4=common 5=D/right 6=center"
    )
    fp.SetKeywords("ALPS SKQU 5-way navigation joystick tact center push")

    def th(number: str, x: float, y: float, drill: float, slotted: bool = False) -> None:
        pad = pcbnew.PAD(fp)
        pad.SetNumber(number)
        pad.SetPosition(pos(x, y))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        if slotted:
            pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
            pad.SetSize(pcbnew.VECTOR2I(mm(1.80), mm(2.70)))
            pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(1.90)))
        else:
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(mm(drill + 0.85), mm(drill + 0.85)))
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
        pad.SetLayerSet(pad.PTHMask())
        fp.Add(pad)

    th("1", -3.25, -5.15, 1.20)
    th("2", -3.25, 0.0, 1.00, slotted=True)
    th("3", -3.25, 5.15, 1.20)
    th("4", 3.25, 5.15, 1.20)
    th("5", 3.25, 0.0, 1.00, slotted=True)
    th("6", 3.25, -5.15, 1.20)

    for layer in (pcbnew.F_Fab, pcbnew.F_SilkS):
        w = 0.15 if layer == pcbnew.F_Fab else 0.20
        # 10 mm square body.
        for x1, y1, x2, y2 in ((-5.0, -5.0, 5.0, -5.0), (5.0, -5.0, 5.0, 5.0),
                               (5.0, 5.0, -5.0, 5.0), (-5.0, 5.0, -5.0, -5.0),
                               # 3.2 mm square stem.
                               (-1.6, -1.6, 1.6, -1.6), (1.6, -1.6, 1.6, 1.6),
                               (1.6, 1.6, -1.6, 1.6), (-1.6, 1.6, -1.6, -1.6),
                               # orientation arrow: A / up (board north).
                               (0.0, -2.4, 0.0, -4.2), (-0.7, -3.5, 0.0, -4.2),
                               (0.7, -3.5, 0.0, -4.2)):
            add_line(fp, x1, y1, x2, y2, layer, w)

    crt = pcbnew.PCB_SHAPE(fp)
    crt.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    crt.SetStart(pos(-5.60, -6.50))
    crt.SetEnd(pos(5.60, 6.50))
    crt.SetLayer(pcbnew.F_CrtYd)
    crt.SetWidth(mm(0.05))
    fp.Add(crt)

    fp.Reference().SetText("REF**")
    fp.Reference().SetPosition(pos(0.0, -7.6))
    fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetText("SW_Nav_ALPS_SKQUCAA010")
    fp.Value().SetPosition(pos(0.0, 7.6))
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


def main() -> None:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    plugin = pcbnew.PCB_IO_KICAD_SEXPR()
    plugin.FootprintSave(str(LIBRARY), teensy41_socket())
    plugin.FootprintSave(str(LIBRARY), rk097_no_edge_guide())
    plugin.FootprintSave(str(LIBRARY), eswitch_100sp_m7())
    plugin.FootprintSave(str(LIBRARY), alps_skqucaa010())
    (HARDWARE / "fp-lib-table").write_text(
        '(fp_lib_table\n  (lib (name "QuadPreRecorder")(type "KiCad")(uri "${KIPRJMOD}/QuadPreRecorder.pretty")(options "")(descr "Project-local module footprints"))\n)\n',
        encoding="utf-8",
    )
    print(LIBRARY / "Teensy41_Socket.kicad_mod")


if __name__ == "__main__":
    main()
