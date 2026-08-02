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

# Rev B (2026-07-25): Hammond 1590XX, pedal-style. Board = Hammond's max PCB
# 138 x 114; y=0 edge faces the REAR wall (SD/USB), y=114 the FRONT wall
# (line out + 9V), x=0 the LEFT wall (RJ45 mic + pad toggle), x=138 the
# RIGHT wall (volume + phones). Corners are chamfered 9mm for the lid-screw
# posts. Display: LCDWiki MSP3520 3.5in (module 98.3 x 56.34).
BOARD_W = 138.0
BOARD_H = 114.0
CORNER = 9.0
TFT_LEFT = 23.0
TFT_TOP = 8.0
TFT_W = 98.3
TFT_H = 56.34


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
    """Return pin-to-net mapping from the same source model as the schematic.

    KiCad's CLI netlist exporter is useful as an independent audit, but the PCB
    generator should not depend on a possibly stale exported netlist.  The
    schematic generator already carries every explicit pin assignment, so use it
    directly here and let the later schematic-parity/DRC checks audit the result.
    """

    mapping: dict[tuple[str, str], str] = {}
    for ref, item in load_design_parts().items():
        for pin, netname in item.pins.items():
            if netname is not None:
                mapping[(ref, pin)] = netname
    if not mapping:
        raise RuntimeError("No schematic pin nets available from design model")
    return mapping


def placements_rev_a() -> dict[str, tuple[float, float, float, bool]]:
    """Rev A (1590F) table, kept for reference. Superseded by placements()."""

    place: dict[str, tuple[float, float, float, bool]] = {
        # Board-mounted enclosure interfaces.
        # Reworked 2026-07-25: J1 moved to the bottom wall away from the mic
        # input; SW1 (now a right-angle wall toggle) takes J1's left-wall spot;
        # J4 and RV1 rotated so bushing/shaft actually exit their walls.
        # Run tools/check_panel_orientation.py after regeneration to confirm.
        "J2": (5.2, 60.0, 270.0, False),
        "J1": (22.0, 165.8, 0.0, False),
        # J4 flipped-side rotation corrected 270 (was 90: body pointed north,
        # bushing 9.6mm short of the south wall). SW1 shifted 1mm inboard so
        # its bracket-pin pads clear the 0.5mm board-edge rule; SW2 up 0.5mm
        # to clear TFT hole H5's courtyard.
        "J4": (125.0, 157.05, 270.0, True),
        "J5": (4.5, 124.0, 90.0, False),
        "SW1": (2.2, 96.0, 0.0, False),
        # Control row moved below the TFT (Jason, 2026-07-25): record button,
        # gain encoder, and the new SW4 5-way nav sit in a row south of the J3
        # display header. Actuator centers (plunger/shaft/stem, NOT anchors)
        # all line up at board Y 88.5: SW2 plunger = anchor+(6.25, 2.5),
        # SW3 shaft = anchor+(7.5, 2.5), SW4 stem = its pattern center.
        "SW2": (50.0, 86.0, 0.0, False),
        "SW3": (68.0, 86.0, 0.0, False),
        "SW4": (107.0, 88.5, 0.0, False),
        "RV1": (6.0, 155.0, 0.0, False),
        "J3": (87.0, 76.0, 270.0, False),
        "J6": (167.7, 26.0, 90.0, False),
        "J7": (167.7, 116.0, 90.0, False),
        # Teensy is socketed on the bottom so the TFT can occupy the lid side.
        "U8": (39.0, 144.0, 270.0, True),

        # Power entry and conversion. The input chain follows J1 down the
        # left side of the bottom-wall power entry.
        "F1": (22.0, 158.0, 90.0, False),
        "D1": (22.0, 151.0, 90.0, False),
        "D2": (22.0, 143.5, 90.0, False),
        # Buck converter cluster moved 27mm south (2026-07-25, Jason's noise
        # concern): the switcher now sits ~49mm from the mic input
        # conditioning row (was ~22mm), closer to the power entry chain and
        # the Teensy +5V feed. Internal move only - no wall/template impact.
        # Feedback row also stays clear of SW1's catalog-sized courtyard.
        "C1": (55.0, 120.0, 0.0, False),
        "C2": (35.0, 115.5, 0.0, False),
        "C3": (42.0, 115.5, 0.0, False),
        "U1": (21.0, 112.5, 0.0, False),
        "L1": (27.5, 112.5, 0.0, False),
        "R1": (26.0, 116.5, 0.0, False),
        "R2": (30.0, 116.5, 0.0, False),
        "C4": (30.0, 118.5, 0.0, False),
        "C5": (33.0, 112.5, 0.0, False),
        "C6": (38.0, 112.5, 0.0, False),
        "R3": (33.5, 118.5, 0.0, False),
        # Filtered electret-bias rail (near the mic input conditioning).
        "R67": (28.0, 68.0, 0.0, False),
        "C66": (36.0, 68.0, 0.0, False),

        # Bias reference and quiet analog regulator. Moved west 2026-07-25 to
        # clear the relocated control row under the TFT.
        "U3": (32.0, 79.0, 0.0, False),
        "C9": (29.5, 83.5, 0.0, False),
        "C10": (34.0, 83.5, 0.0, False),
        "C11": (38.5, 83.5, 0.0, False),
        "U2": (83.0, 69.0, 0.0, False),
        "C7": (79.5, 72.0, 0.0, False),
        "C8": (85.5, 72.0, 0.0, False),

        # Chassis coupling and four input ESD parts beside the DE-9.
        "R4": (24.0, 63.5, 90.0, False),
        "C12": (27.0, 63.5, 90.0, False),
        "R5": (30.0, 63.5, 90.0, False),
        "D6": (23.5, 34.0, 90.0, False),
        "D7": (23.5, 40.0, 90.0, False),
        "D8": (23.5, 46.0, 90.0, False),
        "D9": (23.5, 52.0, 90.0, False),

        # Shared pad mux, JFET preamp, and ADC.
        "U4": (67.0, 42.5, 0.0, False),
        "U5": (67.0, 54.5, 0.0, False),
        "U6": (76.0, 48.5, 0.0, False),
        "U7": (112.0, 48.5, 0.0, False),
        "C34": (67.0, 38.5, 0.0, True),
        "C35": (67.0, 59.0, 0.0, True),
        "C36": (74.0, 41.5, 0.0, True),
        "C37": (78.0, 41.5, 0.0, True),

        # Pad sense filtering plus the J7 debug series protection.
        "R42": (140.0, 87.5, 0.0, False),
        "R43": (144.0, 87.5, 0.0, False),
        "C33": (148.0, 87.5, 0.0, False),
        "R68": (152.0, 87.5, 0.0, False),

        # ADC decoupling and clock/control damping.
        "C38": (102.0, 35.0, 0.0, True),
        "C39": (102.0, 39.0, 0.0, True),
        "C40": (102.0, 43.0, 0.0, True),
        "C41": (118.0, 37.0, 0.0, True),
        "C42": (118.0, 41.0, 0.0, True),
        "C43": (118.0, 49.0, 0.0, True),
        "C44": (118.0, 53.0, 0.0, True),
        "C45": (118.0, 57.0, 0.0, True),
        "C62": (122.0, 51.0, 0.0, True),
        "C63": (122.0, 57.0, 0.0, True),
        "R44": (102.0, 31.0, 0.0, True),
        "R45": (105.8, 31.0, 0.0, True),
        "R46": (109.6, 31.0, 0.0, True),
        "R47": (113.4, 31.0, 0.0, True),
        "R48": (117.2, 31.0, 0.0, True),
        "R49": (121.0, 31.0, 0.0, True),
        "R69": (124.8, 31.0, 0.0, True),

        # Teensy power feed and recorder/user-interface conditioning.
        "D3": (45.0, 136.0, 0.0, False),
        "C46": (52.0, 136.0, 0.0, False),
        "R50": (44.0, 21.0, 0.0, True),
        # C47 moved 1.5mm south: its pad broke into TFT mounting hole H5.
        "C47": (48.0, 19.5, 0.0, True),
        "R51": (64.0, 22.0, 0.0, True),
        "R52": (64.0, 26.0, 0.0, True),
        "R53": (64.0, 30.0, 0.0, True),
        "C48": (70.0, 22.0, 0.0, True),
        "C49": (70.0, 26.0, 0.0, True),
        "C50": (70.0, 30.0, 0.0, True),
        "D4": (93.0, 11.0, 0.0, False),
        "R54": (97.0, 11.0, 0.0, False),
        "D5": (102.0, 11.0, 0.0, False),
        "R55": (106.0, 11.0, 0.0, False),
        "R56": (106.0, 76.0, 0.0, False),
        # SW4 nav-switch pullups and debounce caps, bottom side under the row.
        "R70": (96.0, 97.0, 0.0, True),
        "R71": (100.0, 97.0, 0.0, True),
        "R72": (104.0, 97.0, 0.0, True),
        "R73": (108.0, 97.0, 0.0, True),
        "R74": (112.0, 97.0, 0.0, True),
        "C69": (96.0, 100.5, 0.0, True),
        "C70": (100.0, 100.5, 0.0, True),
        "C71": (104.0, 100.5, 0.0, True),
        "C72": (108.0, 100.5, 0.0, True),
        "C73": (112.0, 100.5, 0.0, True),

        # DAC and headphone circuitry above the right-edge jacks.
        "U9": (82.0, 109.0, 0.0, False),
        "C51": (76.0, 103.0, 0.0, False),
        "C52": (79.5, 102.0, 0.0, False),
        "C53": (83.0, 102.0, 0.0, False),
        "C54": (86.5, 102.0, 0.0, False),
        "C55": (90.5, 102.0, 0.0, False),
        "C56": (76.0, 113.5, 0.0, False),
        "C64": (80.0, 113.5, 0.0, False),
        "R57": (84.0, 114.0, 0.0, True),
        "R58": (88.0, 114.0, 0.0, True),
        "R59": (92.0, 114.0, 0.0, True),
        "R60": (96.0, 114.0, 0.0, True),
        "R61": (100.0, 114.0, 0.0, True),
        "R62": (104.0, 114.0, 0.0, True),
        "R63": (104.0, 113.0, 0.0, False),
        "C67": (96.0, 110.0, 0.0, True),
        "C68": (100.0, 110.0, 0.0, True),
        "C57": (112.5, 123.5, 0.0, False),
        "C58": (111.0, 126.5, 0.0, False),
        "U10": (117.0, 129.5, 0.0, False),
        "C59": (124.0, 129.5, 270.0, False),
        "C60": (110.0, 136.0, 90.0, False),
        "C61": (124.0, 124.5, 90.0, False),
        "C65": (124.0, 134.5, 90.0, False),
        "R64": (109.0, 122.5, 0.0, False),
        "R65": (115.0, 138.0, 0.0, False),
        "R66": (121.0, 138.0, 0.0, False),
    }

    # Four matched signal rows.  Values are kept in identical X positions to
    # make the physical channel symmetry visible and reviewable.
    channel_rows = (34.0, 40.0, 46.0, 52.0)
    for index, y in enumerate(channel_rows):
        channel = index + 1
        input_refs = (
            (f"R{5 + channel}", 32.0),
            (f"R{9 + channel}", 35.0),
            (f"C{12 + channel}", 38.0),
            (f"C{16 + channel}", 42.0),
            (f"R{13 + channel}", 46.0),
            (f"R{18 + 2 * index}", 50.0),
            (f"R{19 + 2 * index}", 54.0),
        )
        output_refs = (
            (f"R{26 + index}", 71.5),
            (f"R{30 + index}", 81.5),
            (f"C{21 + index}", 84.5),
            (f"C{25 + index}", 88.0),
            (f"R{34 + index}", 92.0),
            (f"C{29 + index}", 95.0),
            (f"R{38 + index}", 98.0),
        )
        for ref, x in input_refs + output_refs:
            bottom = bool(re.fullmatch(r"R(?:2[6-9]|3[0-3]|3[8-9]|4[0-1])|C2[1-4]", ref))
            place[ref] = (x, y, 90.0, bottom)
    place["R38"] = (95.0, 47.5, 90.0, True)
    place["C25"] = (88.0, 41.5, 90.0, True)
    return place


def placements() -> dict[str, tuple[float, float, float, bool]]:
    """Rev B placement: 138 x 114 board in the Hammond 1590XX.

    Frame: y=0 REAR (SD), y=114 FRONT (line out + 9V), x=0 LEFT (RJ45 + pad
    toggle), x=138 RIGHT (volume + phones). MSP3520 module zone x 23..121.3,
    y 8..64.34: only low-profile (<10.6mm) SMD parts allowed under it.
    Control-row actuators (SW2 plunger / SW3 shaft / SW4 stem) line up at
    y=73.5, x = 47 / 69 / 91. Wall-part rotations verified by
    tools/check_panel_orientation.py after generation.
    """

    place: dict[str, tuple[float, float, float, bool]] = {
        # --- Enclosure interfaces ---
        "J2": (4.0, 74.0, 270.0, False),      # RJ45 mic in, LEFT wall (port ~flush)
        "SW1": (2.2, 40.0, 0.0, False),       # pad toggle, LEFT wall
        "RV1": (132.0, 82.0, 180.0, False),   # volume, RIGHT wall (shaft +x)
        "J5": (133.5, 41.0, 270.0, False),    # phones, RIGHT wall
        "J1": (108.0, 105.8, 0.0, False),     # 9V barrel, FRONT wall
        "J4": (22.0, 97.0, 270.0, False),     # 1/4in line out, FRONT wall, TOP side
        "U8": (60.0, 62.5, 0.0, True),        # Teensy BOTTOM rear-center (between the TFT holes), SD at REAR wall x~69
        # Control row under the display.
        "SW2": (40.75, 71.0, 0.0, False),     # record (plunger at 47, 73.5)
        "SW3": (61.5, 71.0, 0.0, False),      # gain encoder (shaft at 69, 73.5)
        "SW4": (91.0, 73.5, 0.0, False),      # 5-way nav (stem at 91, 73.5)
        # Display header along the module's front edge. NOTE: at rot 270 the
        # pin row runs WESTWARD from the anchor - anchor at the east end so
        # pins span x 79.98..113, clear of the Teensy pad columns (x 60 and
        # 77.78) and of TFT hole H8 (VERIFY vs module).
        "J3": (113.35, 63.0, 270.0, False),  # split the window between U8 VIN's pad (west) and H8 (east)
        # Internal test headers (replace the Rev A DB-25s): horizontal along
        # the rear edge east of the Teensy, clear of the NE corner chamfer.
        "J6": (82.0, 6.0, 90.0, False),
        "J7": (82.0, 12.5, 90.0, False),

        # --- Power entry chain (front-right, behind J1) + buck ---
        "F1": (96.0, 107.0, 90.0, False),
        "D1": (96.0, 100.0, 90.0, False),
        "D2": (96.0, 92.5, 90.0, False),
        "U1": (105.0, 88.0, 0.0, False),
        "L1": (111.5, 88.0, 0.0, False),
        "C5": (117.0, 88.0, 0.0, False),
        "C6": (123.0, 88.0, 0.0, False),
        "C2": (108.0, 92.5, 0.0, False),
        "C3": (114.0, 92.5, 0.0, False),
        "R1": (105.0, 84.0, 0.0, False),
        "R2": (109.0, 84.0, 0.0, False),
        "C4": (113.0, 84.0, 0.0, False),
        "R3": (117.0, 84.0, 0.0, False),
        "C1": (127.0, 96.0, 0.0, False),

        # --- Chassis coupling + input ESD + bias filter ---
        "R4": (6.0, 64.0, 0.0, False),
        "C12": (10.5, 64.0, 0.0, False),
        "R5": (15.0, 64.0, 0.0, False),
        "D6": (24.0, 68.0, 90.0, False),
        "D7": (24.0, 72.0, 90.0, False),
        "D8": (24.0, 76.0, 90.0, False),
        "D9": (24.0, 80.0, 90.0, False),
        "R67": (28.0, 80.0, 0.0, False),
        "C66": (34.0, 74.0, 0.0, True),

        # --- Pad sense + debug protection, by the toggle ---
        "R42": (6.0, 52.0, 0.0, False),
        "R43": (10.5, 52.0, 0.0, False),
        "C33": (15.0, 52.0, 0.0, False),
        "R68": (19.5, 52.0, 0.0, False),

        # --- Bias reference + analog LDO (low profile, under the module) ---
        "U3": (34.0, 26.0, 0.0, False),
        "C9": (30.0, 31.0, 0.0, False),
        "C10": (35.0, 31.0, 0.0, False),
        "C11": (39.5, 31.0, 0.0, False),
        # LDO + its caps live on the BOTTOM, east of the Teensy, tucked north
        # into the low-profile module zone to clear J3's courtyard band
        # (y 61.23..64.77) and stay well short of SW4's (y >= 67.0).
        "U2": (88.0, 55.0, 0.0, True),   # nudged north off C45's silkscreen/fab bbox corner
        "C7": (92.5, 55.0, 0.0, True),   # east flank, clear of the C41-45 column at x=84
        "C8": (92.5, 59.0, 0.0, True),

        # --- Mux + preamp + ADC (low profile, under the module) ---
        "U4": (40.0, 44.0, 0.0, False),
        "U5": (40.0, 56.0, 0.0, False),
        "U6": (52.0, 50.0, 0.0, False),
        "U7": (68.0, 50.0, 0.0, False),
        "C34": (40.0, 40.0, 0.0, True),
        "C35": (40.0, 60.5, 0.0, True),
        "C36": (47.0, 42.0, 0.0, True),
        "C37": (51.0, 42.0, 0.0, True),
        "C38": (56.0, 46.0, 0.0, True),
        "C39": (56.0, 50.0, 0.0, True),
        "C40": (56.0, 54.0, 0.0, True),
        "C41": (84.0, 44.0, 0.0, True),
        "C42": (84.0, 48.0, 0.0, True),
        "C43": (84.0, 52.0, 0.0, True),
        "C44": (84.0, 56.0, 0.0, True),
        "C45": (84.0, 60.0, 0.0, True),
        "C62": (93.0, 48.0, 0.0, True),
        "C63": (93.0, 52.0, 0.0, True),
        "R44": (96.0, 40.0, 0.0, True),
        "R45": (100.0, 40.0, 0.0, True),
        "R46": (104.0, 40.0, 0.0, True),
        "R47": (108.0, 40.0, 0.0, True),
        "R48": (112.0, 40.0, 0.0, True),
        "R49": (116.0, 40.0, 0.0, True),
        "R69": (120.0, 40.0, 0.0, True),

        # --- Teensy feed: BOTTOM side, next to the Teensy's VIN corner ---
        "D3": (48.0, 60.0, 0.0, True),
        "C46": (48.0, 56.0, 0.0, True),

        # --- Control-row pullups/debounce, BOTTOM under the module zone ---
        "R50": (102.0, 16.0, 0.0, True),
        "C47": (106.0, 16.0, 0.0, True),
        "R51": (102.0, 20.0, 0.0, True),
        "R52": (106.0, 20.0, 0.0, True),
        "R53": (110.0, 20.0, 0.0, True),
        "C48": (102.0, 24.0, 0.0, True),
        "C49": (106.0, 24.0, 0.0, True),
        "C50": (110.0, 24.0, 0.0, True),
        "R70": (102.0, 28.0, 0.0, True),
        "R71": (106.0, 28.0, 0.0, True),
        "R72": (110.0, 28.0, 0.0, True),
        "R73": (114.0, 28.0, 0.0, True),
        "R74": (118.0, 28.0, 0.0, True),
        "C69": (102.0, 32.0, 0.0, True),
        "C70": (106.0, 32.0, 0.0, True),
        "C71": (110.0, 32.0, 0.0, True),
        "C72": (114.0, 32.0, 0.0, True),
        "C73": (118.0, 32.0, 0.0, True),

        # --- LEDs on the front strip ---
        "D4": (66.0, 108.0, 0.0, False),
        "R54": (70.0, 108.0, 0.0, False),
        "D5": (74.0, 108.0, 0.0, False),
        "R55": (78.0, 108.0, 0.0, False),
        "R56": (88.0, 57.0, 0.0, False),

        # --- DAC + headphone amp (low profile, under the module edge) ---
        "U9": (100.0, 50.0, 0.0, False),
        "C51": (91.0, 46.0, 0.0, False),
        "C52": (95.0, 43.0, 0.0, False),
        "C53": (98.5, 43.0, 0.0, False),
        "C54": (102.0, 43.0, 0.0, False),
        "C55": (109.5, 43.0, 0.0, False),
        "C56": (91.0, 53.0, 0.0, False),
        "C64": (91.0, 49.5, 0.0, False),
        "R57": (86.0, 46.0, 0.0, True),
        "R58": (90.0, 46.0, 0.0, True),
        "R59": (94.0, 46.0, 0.0, True),
        "R60": (98.0, 46.0, 0.0, True),
        "R61": (102.0, 46.0, 0.0, True),
        # Line-out reconstruction filter lives by the DAC; LINE_L/R then run
        # to J4 (front-left) and RV1 (right wall).
        "R62": (95.0, 58.0, 0.0, False),
        "R63": (98.5, 58.0, 0.0, False),
        "C67": (95.0, 55.0, 0.0, False),
        "C68": (98.5, 55.0, 0.0, False),
        "U10": (112.0, 56.0, 0.0, False),
        "C57": (123.0, 76.0, 0.0, False),
        "C58": (123.0, 79.5, 0.0, False),
        "C59": (106.0, 52.0, 0.0, False),
        "C60": (106.0, 58.5, 0.0, False),
        "C61": (105.0, 67.5, 0.0, False),
        "C65": (117.0, 52.0, 0.0, False),
        "R64": (108.0, 48.0, 0.0, False),
        "R65": (125.0, 64.0, 0.0, False),
        "R66": (125.0, 67.5, 0.0, False),
    }

    # Four matched channel rows across the front-left field, y = 86..104.
    channel_rows = (86.0, 92.0, 98.0, 104.0)
    for index, y in enumerate(channel_rows):
        channel = index + 1
        input_refs = (
            (f"R{5 + channel}", 30.0),
            (f"R{9 + channel}", 34.0),
            (f"C{12 + channel}", 38.0),
            (f"C{16 + channel}", 42.0),
            (f"R{13 + channel}", 46.0),
            (f"R{18 + 2 * index}", 50.0),
            (f"R{19 + 2 * index}", 54.0),
        )
        output_refs = (
            (f"R{26 + index}", 60.0),
            (f"R{30 + index}", 66.0),
            (f"C{21 + index}", 70.0),
            (f"C{25 + index}", 74.0),
            (f"R{34 + index}", 78.0),
            (f"C{29 + index}", 82.0),
            (f"R{38 + index}", 86.0),
        )
        for ref, x in input_refs + output_refs:
            bottom = bool(re.fullmatch(r"R(?:2[6-9]|3[0-3]|3[8-9]|4[0-1])|C2[1-4]", ref))
            place[ref] = (x, y, 90.0, bottom)
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


def add_edge_keepouts(board: pcbnew.BOARD) -> None:
    """Rule areas keeping tracks/vias 0.65mm off every board edge.

    Freerouting's internal edge clearance is looser than the 0.5mm KiCad
    rule, so without these it routes long tracks ~0.47mm from the outline.
    Four edge strips plus four corner triangles hugging the 9mm chamfers.
    """

    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    w, h, c = BOARD_W, BOARD_H, CORNER
    m = 0.65
    shapes: list[list[tuple[float, float]]] = [
        [(8.0, 0.0), (w - 8.0, 0.0), (w - 8.0, m), (8.0, m)],
        [(8.0, h - m), (w - 8.0, h - m), (w - 8.0, h), (8.0, h)],
        [(0.0, 8.0), (m, 8.0), (m, h - 8.0), (0.0, h - 8.0)],
        [(w - m, 8.0), (w, 8.0), (w, h - 8.0), (w - m, h - 8.0)],
        [(0.0, 0.0), (c + m, 0.0), (0.0, c + m)],
        [(w - c - m, 0.0), (w, 0.0), (w, c + m)],
        [(w, h - c - m), (w, h), (w - c - m, h)],
        [(0.0, h - c - m), (c + m, h), (0.0, h)],
    ]
    for points in shapes:
        zone = pcbnew.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowZoneFills(False)
        zone.SetLayerSet(layers)
        outline = zone.Outline()
        contour = outline.NewOutline()
        for x, y in points:
            outline.Append(mm(x), mm(y), contour)
        board.Add(zone)


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
    title.SetComment(1, "Hammond 1590XX / two copper layers / Rev B pedal-style build")
    title.SetRevision("B")
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

    # Rev B outline: rectangle with 9mm corner chamfers clearing the 1590XX
    # lid-screw posts (post centers 4.21mm in from the enclosure corners).
    c, w, h = CORNER, BOARD_W, BOARD_H
    outline = ((c, 0.0), (w - c, 0.0), (w, c), (w, h - c), (w - c, h), (c, h), (0.0, h - c), (0.0, c))
    for start, end in zip(outline, outline[1:] + outline[:1]):
        add_segment(board, pcbnew.Edge_Cuts, start, end)
    add_edge_keepouts(board)
    add_rect(board, pcbnew.Dwgs_User, TFT_LEFT, TFT_TOP, TFT_LEFT + TFT_W, TFT_TOP + TFT_H, 0.20)
    add_text(board, "3.5in MSP3520 MODULE ENVELOPE - VERIFY MODULE", 72.0, 36.0, 0.8, pcbnew.Dwgs_User)

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

    # MSP3520 module pattern center (module envelope center).
    tft_cx, tft_cy = TFT_LEFT + TFT_W / 2, TFT_TOP + TFT_H / 2
    # Rev B: no H1-H4 - the board is carried entirely by its wall hardware
    # (RJ45, toggle, pot, phone/line jacks, 9V). H5-H8 are the MSP3520
    # module standoffs at a PROVISIONAL corner pattern (holes inset 2.5mm
    # from the module outline) - the MSP3520 drawing does not publish them,
    # so VERIFY against the physical module before ordering.
    for ref, x, y in (
        ("H5", tft_cx - 46.65, tft_cy - 25.67),
        ("H6", tft_cx + 46.65, tft_cy - 25.67),
        ("H7", tft_cx - 46.65, tft_cy + 25.67),
        ("H8", tft_cx + 46.65, tft_cy + 25.67),
    ):
        add_mounting_hole(board, ref, x, y, "M3 TFT MSP3520 PROVISIONAL-VERIFY")

    # Rev B fiducials inside the 138 x 114 chamfered outline.
    for index, (x, y) in enumerate(((10.0, 8.0), (130.0, 60.0), (50.0, 110.0)), start=1):
        add_fiducial(board, f"FID{index}", x, y, False)
    for index, (x, y) in enumerate(((12.0, 8.0), (126.0, 66.0), (60.0, 110.0)), start=4):
        add_fiducial(board, f"FID{index}", x, y, True)

    # Enclosure-facing labels and setup warnings (Rev B frame).
    add_text(board, "PAD", 11.0, 47.0, 0.70)
    add_text(board, "REC", 47.0, 83.5, 0.70)
    add_text(board, "GAIN", 69.0, 83.5, 0.70)
    add_text(board, "NAV", 91.0, 83.5, 0.70)
    add_text(board, "PWR", 66.0, 111.5, 0.60)
    add_text(board, "REC", 74.0, 111.5, 0.60)
    add_text(board, "MSP3520 TFT 1..14", 97.0, 64.5, 0.60)
    add_text(board, "MIC RJ45", 11.0, 71.0, 0.70)
    add_text(board, "9VDC", 108.0, 101.5, 0.70)
    add_text(board, "HP", 128.0, 47.5, 0.70)
    add_text(board, "VOL", 128.0, 88.5, 0.70)
    add_text(board, "LINE", 27.0, 91.0, 0.70)
    add_text(board, "TP ANALOG", 119.0, 6.0, 0.55)
    add_text(board, "TP DIGITAL", 119.0, 12.5, 0.55)
    add_text(board, "jdg511  QUAD PRE RECORDER  REV B  HAMMOND 1590XX", 69.0, 3.5, 0.70)
    add_text(board, "TEENSY 4.1 ON BOTTOM - CUT VIN/VUSB FOR DUAL POWER", 72.0, 100.0, 0.65, pcbnew.B_SilkS)
    add_text(board, "SD CARD SLOT THIS EDGE", 30.0, 3.5, 0.60, pcbnew.B_SilkS)

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
