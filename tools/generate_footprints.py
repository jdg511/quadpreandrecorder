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


def main() -> None:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    plugin = pcbnew.PCB_IO_KICAD_SEXPR()
    plugin.FootprintSave(str(LIBRARY), teensy41_socket())
    plugin.FootprintSave(str(LIBRARY), rk097_no_edge_guide())
    (HARDWARE / "fp-lib-table").write_text(
        '(fp_lib_table\n  (lib (name "QuadPreRecorder")(type "KiCad")(uri "${KIPRJMOD}/QuadPreRecorder.pretty")(options "")(descr "Project-local module footprints"))\n)\n',
        encoding="utf-8",
    )
    print(LIBRARY / "Teensy41_Socket.kicad_mod")


if __name__ == "__main__":
    main()
