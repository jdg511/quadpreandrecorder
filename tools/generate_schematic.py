#!/usr/bin/env python3
"""Generate the native KiCad 10 Quad Preamp and Recorder schematic.

The generator intentionally connects symbols with net labels at their real pin
coordinates.  That keeps the large mixed-signal drawing readable while still
giving KiCad/ERC a normal geometric schematic connectivity model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from uuid import UUID, uuid5


ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
OUT = HARDWARE / "QuadPreRecorder.kicad_sch"
LOCAL_LIB_OUT = HARDWARE / "QuadPreRecorder.kicad_sym"
PROJECT = "QuadPreRecorder"
ROOT_UUID = UUID("ad984389-991b-4f10-bf10-bd77562cc42d")
NAMESPACE = UUID("4cc3aa18-bdf3-45b7-93d5-b74e5eb83aca")


def find_symbol_dir() -> Path:
    for candidate in (
        Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols"),
        Path(r"C:\Program Files\KiCad\9.0\share\kicad\symbols"),
    ):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("KiCad stock symbol directory was not found")


def extract_block(text: str, marker: str, start: int = 0) -> str:
    block_start = text.find(marker, start)
    if block_start < 0:
        raise ValueError(f"{marker!r} not found")
    depth = 0
    in_string = False
    escaped = False
    for index in range(block_start, len(text)):
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
                return text[block_start : index + 1]
    raise ValueError(f"Unbalanced S-expression at {marker!r}")


@dataclass(frozen=True)
class LibrarySymbol:
    library: str
    filename: str
    name: str
    lib_id: str | None = None

    @property
    def identifier(self) -> str:
        return self.lib_id or f"{self.library}:{self.name}"


class SymbolRegistry:
    def __init__(self) -> None:
        self.symbol_dir = find_symbol_dir()
        self.specs: dict[str, LibrarySymbol] = {}
        self.source_blocks: dict[tuple[str, str], str] = {}
        self.embedded: dict[str, str] = {}

    def source_block(self, filename: str, name: str) -> str:
        key = (filename, name)
        if key not in self.source_blocks:
            text = (self.symbol_dir / filename).read_text(encoding="utf-8")
            self.source_blocks[key] = extract_block(text, f'(symbol "{name}"')
        return self.source_blocks[key]

    def register(self, spec: LibrarySymbol) -> str:
        identifier = spec.identifier
        if identifier in self.specs:
            return identifier
        block = self.source_block(spec.filename, spec.name)
        parent_match = re.search(r'\(extends "([^"]+)"\)', block)
        if parent_match:
            parent_name = parent_match.group(1)
            parent = LibrarySymbol(spec.library, spec.filename, parent_name)
            parent_id = self.register(parent)
            block = block.replace(
                f'(extends "{parent_name}")', f'(extends "{parent_id}")', 1
            )
        block = block.replace(
            f'(symbol "{spec.name}"', f'(symbol "{identifier}"', 1
        )
        self.specs[identifier] = spec
        self.embedded[identifier] = block
        return identifier

    def resolved_block(self, identifier: str) -> str:
        spec = self.specs[identifier]
        block = self.source_block(spec.filename, spec.name)
        parent_match = re.search(r'\(extends "([^"]+)"\)', block)
        if not parent_match:
            return block
        parent_name = parent_match.group(1)
        parent_id = f"{spec.library}:{parent_name}"
        return self.resolved_block(parent_id)

    def pins(self, identifier: str, unit: int) -> dict[str, tuple[float, float, int]]:
        block = self.resolved_block(identifier)
        spec = self.specs[identifier]
        unit_markers = (
            f'(symbol "{spec.name}_0_0"',
            f'(symbol "{spec.name}_0_1"',
            f'(symbol "{spec.name}_{unit}_1"',
            f'(symbol "{spec.name}_{unit}_0"',
        )
        selected: list[str] = []
        for marker in unit_markers:
            start = block.find(marker)
            if start >= 0:
                selected.append(extract_block(block, marker, start))
        if not selected:
            selected = [block]
        pins: dict[str, tuple[float, float, int]] = {}
        for source in selected:
            cursor = 0
            while True:
                start = source.find("(pin ", cursor)
                if start < 0:
                    break
                pin_block = extract_block(source, "(pin ", start)
                number = re.search(r'\(number "([^"]+)"', pin_block)
                at = re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)', pin_block)
                if number and at:
                    pins[number.group(1)] = (
                        float(at.group(1)),
                        float(at.group(2)),
                        int(float(at.group(3))),
                    )
                cursor = start + len(pin_block)
        if not pins:
            raise ValueError(f"No pins found for {identifier} unit {unit}")
        return pins


def custom_teensy_symbol() -> str:
    left = [
        ("GND1", "GND"), ("0", "D0/RX1"), ("1", "D1/TX1"),
        ("2", "D2/OUT2"), ("3", "D3/LRCLK2"), ("4", "D4/BCLK2"),
        ("5", "D5"), ("6", "D6"), ("7", "D7/OUT1A"),
        ("8", "D8/IN1"), ("9", "D9"), ("10", "D10/CS"),
        ("11", "D11/MOSI"), ("12", "D12/MISO"),
        ("3V3A", "3V3"), ("24", "D24"), ("25", "D25"),
        ("26", "D26"), ("27", "D27"), ("28", "D28"),
        ("29", "D29"), ("30", "D30"), ("31", "D31"), ("32", "D32"),
    ]
    right = [
        ("VIN", "VIN"), ("GND2", "GND"), ("23", "D23/MCLK1"),
        ("22", "D22"), ("21", "D21/BCLK1"), ("20", "D20/LRCLK1"),
        ("19", "D19/SCL"), ("18", "D18/SDA"), ("17", "D17"),
        ("16", "D16"), ("15", "D15"), ("14", "D14"),
        ("13", "D13/SCK"), ("41", "D41"), ("40", "D40"),
        ("39", "D39"), ("38", "D38"), ("37", "D37"),
        ("36", "D36"), ("35", "D35"), ("34", "D34"),
        ("33", "D33"), ("GND3", "GND"), ("3V3B", "3V3"),
    ]
    lines = [
        '(symbol "QuadPreRecorder:Teensy41")',
    ]
    # Build with explicit indentation after fixing the opening line below.
    lines = [
        '(symbol "QuadPreRecorder:Teensy41"',
        '\t(exclude_from_sim no)', '\t(in_bom yes)', '\t(on_board yes)',
        '\t(in_pos_files yes)', '\t(duplicate_pin_numbers_are_jumpers no)',
        '\t(property "Reference" "U" (at -20.32 33.02 0) (effects (font (size 1.27 1.27))))',
        '\t(property "Value" "Teensy 4.1" (at 0 33.02 0) (effects (font (size 1.27 1.27))))',
        '\t(property "Footprint" "QuadPreRecorder:Teensy41_Socket" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(property "Datasheet" "https://www.pjrc.com/store/teensy41.html" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(property "Description" "PJRC Teensy 4.1 600 MHz Cortex-M7 module with native SDIO microSD" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(symbol "Teensy41_0_1"',
        '\t\t(rectangle (start -17.78 30.48) (end 17.78 -30.48) (stroke (width 0) (type default)) (fill (type background)))',
        '\t)',
        '\t(symbol "Teensy41_1_1"',
    ]
    for index, (number, name) in enumerate(left):
        y = 27.94 - index * 2.54
        electrical_type = "power_in" if number == "GND1" else ("power_out" if number == "3V3A" else "bidirectional")
        lines.extend([
            f'\t\t(pin {electrical_type} line (at -20.32 {y:.2f} 0) (length 2.54)',
            f'\t\t\t(name "{name}" (effects (font (size 1.0 1.0))))',
            f'\t\t\t(number "{number}" (effects (font (size 1.0 1.0))))',
            '\t\t)',
        ])
    for index, (number, name) in enumerate(right):
        y = 27.94 - index * 2.54
        electrical_type = "power_in" if number in {"VIN", "GND2", "GND3"} else ("passive" if number == "3V3B" else "bidirectional")
        lines.extend([
            f'\t\t(pin {electrical_type} line (at 20.32 {y:.2f} 180) (length 2.54)',
            f'\t\t\t(name "{name}" (effects (font (size 1.0 1.0))))',
            f'\t\t\t(number "{number}" (effects (font (size 1.0 1.0))))',
            '\t\t)',
        ])
    lines.extend(['\t)', ')'])
    return "\n".join(lines)


def custom_nav_symbol() -> str:
    """6-pin symbol for the ALPS SKQUCAA010 4-way + center push nav switch."""

    left = [("1", "A/UP"), ("2", "B/LEFT"), ("3", "C/DOWN")]
    right = [("6", "CENTER"), ("5", "D/RIGHT"), ("4", "COM")]
    lines = [
        '(symbol "QuadPreRecorder:SW_Nav5"',
        '\t(exclude_from_sim no)', '\t(in_bom yes)', '\t(on_board yes)',
        '\t(in_pos_files yes)', '\t(duplicate_pin_numbers_are_jumpers no)',
        '\t(property "Reference" "SW" (at -5.08 7.62 0) (effects (font (size 1.27 1.27))))',
        '\t(property "Value" "SKQUCAA010" (at 0 7.62 0) (effects (font (size 1.27 1.27))))',
        '\t(property "Footprint" "QuadPreRecorder:SW_Nav_ALPS_SKQUCAA010" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(property "Datasheet" "https://cdn-shop.adafruit.com/datasheets/SKQUCAA010-ALPS.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(property "Description" "ALPS 4-directional + center push TACT switch" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        '\t(symbol "SW_Nav5_0_1"',
        '\t\t(rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0) (type default)) (fill (type background)))',
        '\t)',
        '\t(symbol "SW_Nav5_1_1"',
    ]
    for index, (number, name) in enumerate(left):
        y = 2.54 - index * 2.54
        lines.extend([
            f'\t\t(pin passive line (at -7.62 {y:.2f} 0) (length 2.54)',
            f'\t\t\t(name "{name}" (effects (font (size 1.0 1.0))))',
            f'\t\t\t(number "{number}" (effects (font (size 1.0 1.0))))',
            '\t\t)',
        ])
    for index, (number, name) in enumerate(right):
        y = 2.54 - index * 2.54
        lines.extend([
            f'\t\t(pin passive line (at 7.62 {y:.2f} 180) (length 2.54)',
            f'\t\t\t(name "{name}" (effects (font (size 1.0 1.0))))',
            f'\t\t\t(number "{number}" (effects (font (size 1.0 1.0))))',
            '\t\t)',
        ])
    lines.extend(['\t)', ')'])
    return "\n".join(lines)


def nav_pins() -> dict[str, tuple[float, float, int]]:
    block = custom_nav_symbol()
    pins: dict[str, tuple[float, float, int]] = {}
    cursor = 0
    while True:
        start = block.find("(pin ", cursor)
        if start < 0:
            break
        pin_block = extract_block(block, "(pin ", start)
        number = re.search(r'\(number "([^"]+)"', pin_block)
        at = re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)', pin_block)
        if number and at:
            pins[number.group(1)] = (float(at.group(1)), float(at.group(2)), int(float(at.group(3))))
        cursor = start + len(pin_block)
    return pins


@dataclass
class Part:
    spec: LibrarySymbol | str
    ref: str
    value: str
    footprint: str
    pins: dict[str, str | None]
    x: float
    y: float
    unit: int = 1
    datasheet: str = "~"
    description: str = ""
    manufacturer: str = ""
    mpn: str = ""
    dnp: bool = False
    in_bom: bool = True
    on_board: bool = True
    hide_reference: bool = False
    hide_value: bool = False


class Schematic:
    def __init__(self, registry: SymbolRegistry) -> None:
        self.registry = registry
        self.items: list[str] = []
        self.counts: dict[str, int] = {}

    def uid(self, kind: str) -> str:
        count = self.counts.get(kind, 0) + 1
        self.counts[kind] = count
        return str(uuid5(NAMESPACE, f"{kind}:{count}"))

    def text(self, value: str, x: float, y: float, size: float = 1.27, bold: bool = False) -> None:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        font = f"(font (size {size:.2f} {size:.2f})" + (" (bold yes))" if bold else ")")
        self.items.append("\n".join([
            f'\t(text "{escaped}"', '\t\t(exclude_from_sim no)',
            f'\t\t(at {x:.2f} {y:.2f} 0)',
            f'\t\t(effects {font} (justify left))',
            f'\t\t(uuid "{self.uid("text")}")', '\t)',
        ]))

    def label(self, name: str, x: float, y: float, angle: int = 0) -> None:
        justify = " (justify left bottom)" if angle == 0 else " (justify right bottom)"
        self.items.append("\n".join([
            f'\t(label "{name}"', f'\t\t(at {x:.2f} {y:.2f} {angle})',
            f'\t\t(effects (font (size 1.00 1.00)){justify})',
            f'\t\t(uuid "{self.uid("label")}")', '\t)',
        ]))

    def no_connect(self, x: float, y: float) -> None:
        self.items.append("\n".join([
            f'\t(no_connect (at {x:.2f} {y:.2f})',
            f'\t\t(uuid "{self.uid("nc")}")', '\t)',
        ]))

    def symbol(self, part: Part) -> None:
        if isinstance(part.spec, str):
            identifier = part.spec
        else:
            identifier = self.registry.register(part.spec)
        symbol_uuid = self.uid("symbol")
        props = [
            ("Reference", part.ref, part.x - 5.08, part.y - 7.62, part.hide_reference),
            ("Value", part.value, part.x - 5.08, part.y + 7.62, part.hide_value),
            ("Footprint", part.footprint, part.x, part.y, True),
            ("Datasheet", part.datasheet, part.x, part.y, True),
            ("Description", part.description, part.x, part.y, True),
        ]
        if part.manufacturer:
            props.append(("Manufacturer", part.manufacturer, part.x, part.y, True))
        if part.mpn:
            props.append(("MPN", part.mpn, part.x, part.y, True))
        lines = [
            '\t(symbol)',
        ]
        lines = [
            '\t(symbol', f'\t\t(lib_id "{identifier}")',
            f'\t\t(at {part.x:.2f} {part.y:.2f} 0)', f'\t\t(unit {part.unit})',
            '\t\t(exclude_from_sim no)', f'\t\t(in_bom {"yes" if part.in_bom else "no"})',
            f'\t\t(on_board {"yes" if part.on_board else "no"})',
            f'\t\t(dnp {"yes" if part.dnp else "no"})', '\t\t(fields_autoplaced yes)',
            f'\t\t(uuid "{symbol_uuid}")',
        ]
        for key, value, x, y, hidden in props:
            escaped = value.replace('"', '\\"')
            lines.extend([
                f'\t\t(property "{key}" "{escaped}"',
                f'\t\t\t(at {x:.2f} {y:.2f} 0)',
                '\t\t\t(effects (font (size 1.27 1.27))' + (' (hide yes))' if hidden else ')'),
                '\t\t)',
            ])
        lines.extend([
            f'\t\t(instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{part.ref}") (unit {part.unit}))))',
            '\t)',
        ])
        self.items.append("\n".join(lines))

        if identifier == "QuadPreRecorder:Teensy41":
            pin_positions = teensy_pins()
        elif identifier == "QuadPreRecorder:SW_Nav5":
            pin_positions = nav_pins()
        else:
            pin_positions = self.registry.pins(identifier, part.unit)
        for number, net in part.pins.items():
            if number not in pin_positions:
                raise KeyError(f"{part.ref} {identifier} has no pin {number}")
            px, py, angle = pin_positions[number]
            x = part.x + px
            # KiCad symbol-library Y coordinates are Cartesian-up, while sheet
            # coordinates increase downward.
            y = part.y - py
            if net is None:
                self.no_connect(x, y)
            else:
                self.label(net, x, y, angle)


def teensy_pins() -> dict[str, tuple[float, float, int]]:
    block = custom_teensy_symbol()
    pins: dict[str, tuple[float, float, int]] = {}
    cursor = 0
    while True:
        start = block.find("(pin ", cursor)
        if start < 0:
            break
        pin_block = extract_block(block, "(pin ", start)
        number = re.search(r'\(number "([^"]+)"', pin_block)
        at = re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)', pin_block)
        if number and at:
            pins[number.group(1)] = (float(at.group(1)), float(at.group(2)), int(float(at.group(3))))
        cursor = start + len(pin_block)
    return pins


REGISTRY = SymbolRegistry()


def stock(library: str, filename: str, name: str, lib_id: str | None = None) -> LibrarySymbol:
    return LibrarySymbol(library, filename, name, lib_id)


R = stock("Device", "Device.kicad_sym", "R")
C = stock("Device", "Device.kicad_sym", "C")
C_POL = stock("Device", "Device.kicad_sym", "C_Polarized")
L = stock("Device", "Device.kicad_sym", "L")
LED = stock("Device", "Device.kicad_sym", "LED")
FUSE = stock("Device", "Device.kicad_sym", "Polyfuse")
DIODE = stock("Device", "Device.kicad_sym", "D_Schottky")
TVS = stock("Device", "Device.kicad_sym", "D_TVS")
FB = stock("Device", "Device.kicad_sym", "FerriteBead")
JACK_DC = stock("Connector", "Connector.kicad_sym", "Barrel_Jack_Switch")
DB9 = stock("Connector_Generic", "Connector_Generic.kicad_sym", "Conn_01x09")
DB25 = stock("Connector_Generic", "Connector_Generic.kicad_sym", "Conn_01x25")
RJ45S = stock("Connector", "Connector.kicad_sym", "8P8C_Shielded")
JACK_TRS = stock("Connector_Audio", "Connector_Audio.kicad_sym", "AudioJack3")
CONN14 = stock("Connector_Generic", "Connector_Generic.kicad_sym", "Conn_01x14")
SW_SPDT = stock("Switch", "Switch.kicad_sym", "SW_SPDT")
SW_PUSH = stock("Switch", "Switch.kicad_sym", "SW_Push")
ENCODER = stock("Device", "Device.kicad_sym", "RotaryEncoder_Switch")
POT_DUAL = stock("Device", "Device.kicad_sym", "R_Potentiometer_Dual")
BUCK = stock("Regulator_Switching", "Regulator_Switching.kicad_sym", "TPS62160DGK")
LDO = stock("QuadPreRecorder", "Regulator_Linear.kicad_sym", "LP5907MFX-1.2", "QuadPreRecorder:TPS7A20DBV")
VREF = stock("Reference_Voltage", "Reference_Voltage.kicad_sym", "TLE2426xD")
MUX = stock("Analog_Switch", "Analog_Switch.kicad_sym", "CD4053B")
ADC = stock("Audio", "Audio.kicad_sym", "PCM1864DBT")
DAC = stock("QuadPreRecorder", "Audio.kicad_sym", "PCM5100", "QuadPreRecorder:PCM5102A")
HPAMP = stock("Amplifier_Audio", "Amplifier_Audio.kicad_sym", "TPA6132A2RTE")
PWR_FLAG = stock("power", "power.kicad_sym", "PWR_FLAG")


def opa1654_spec() -> LibrarySymbol:
    identifier = "QuadPreRecorder:OPA1654"
    if identifier in REGISTRY.specs:
        return REGISTRY.specs[identifier]
    source = stock("Amplifier_Operational", "Amplifier_Operational.kicad_sym", "LM2902", identifier)
    REGISTRY.register(source)
    block = REGISTRY.embedded[identifier]
    block = block.replace("LM2902", "OPA1654")
    block = re.sub(r'\(property "Datasheet" "[^"]*"', '(property "Datasheet" "https://www.ti.com/lit/ds/symlink/opa1654.pdf"', block, count=1)
    REGISTRY.specs[identifier] = source
    REGISTRY.embedded[identifier] = block
    return source


def part(
    spec: LibrarySymbol | str,
    ref: str,
    value: str,
    footprint: str,
    pins: dict[str, str | None],
    x: float,
    y: float,
    **kwargs: object,
) -> Part:
    # KiCad's ERC connectivity grid is 50 mil (1.27 mm).  Keeping symbol
    # origins on that grid also keeps every stock-symbol pin and attached label
    # exactly on-grid.
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    return Part(spec, ref, value, footprint, pins, x, y, **kwargs)


def resistor(ref: str, value: str, a: str, b: str, x: float, y: float, *, precision: bool = False, dnp: bool = False) -> Part:
    return part(
        R, ref, value, "Resistor_SMD:R_0603_1608Metric", {"1": a, "2": b}, x, y,
        manufacturer="Vishay" if precision else "Yageo",
        mpn="TNPW0603 series, 0.1%" if precision else "RC0603FR series, 1%",
        dnp=dnp,
    )


def capacitor(ref: str, value: str, a: str, b: str, x: float, y: float, *, size: str = "0603", mpn: str = "") -> Part:
    footprint = {
        "0603": "Capacitor_SMD:C_0603_1608Metric",
        "0805": "Capacitor_SMD:C_0805_2012Metric",
        "1206": "Capacitor_SMD:C_1206_3216Metric",
    }[size]
    return part(
        C, ref, value, footprint, {"1": a, "2": b}, x, y,
        manufacturer="Murata", mpn=mpn or "GRM series X7R/C0G",
    )


def polarized_cap(ref: str, value: str, positive: str, negative: str, x: float, y: float) -> Part:
    return part(
        C_POL, ref, value, "Capacitor_SMD:CP_Elec_6.3x5.8", {"1": positive, "2": negative}, x, y,
        manufacturer="Panasonic", mpn="EEE-FK series low-ESR aluminium electrolytic",
    )


def build_parts() -> list[Part]:
    p: list[Part] = []

    # Power entry and rails.
    p.extend([
        part(JACK_DC, "J1", "9V DC IN", "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal",
             {"1": "+9V_IN", "2": "GND", "3": "GND"}, 22.0, 42.0,
             manufacturer="CUI Devices", mpn="PJ-102AH"),
        part(FUSE, "F1", "750mA PTC", "Fuse:Fuse_1206_3216Metric", {"1": "+9V_IN", "2": "+9V_FUSED"}, 42.0, 42.0,
             manufacturer="Littelfuse", mpn="1206L075/13.2WR"),
        part(DIODE, "D1", "SS14", "Diode_SMD:D_SMA", {"2": "+9V_FUSED", "1": "+9V"}, 60.0, 42.0,
             manufacturer="Diodes Incorporated", mpn="SS14-13-F"),
        part(TVS, "D2", "SMBJ12A", "Diode_SMD:D_SMB", {"1": "+9V", "2": "GND"}, 78.0, 42.0,
             manufacturer="Littelfuse", mpn="SMBJ12A"),
        polarized_cap("C1", "100uF 25V", "+9V", "GND", 96.0, 42.0),
        capacitor("C2", "100nF 25V", "+9V", "GND", 112.0, 42.0, size="0805"),
        capacitor("C3", "10uF 25V", "+9V", "GND", 128.0, 42.0, size="1206"),
        part(BUCK, "U1", "TPS62160DGK", "Package_SO:VSSOP-8_3x3mm_P0.65mm",
             {"1": "GND", "2": "+9V", "3": "+9V", "4": "GND", "5": "BUCK_FB", "6": "+5V", "7": "BUCK_SW", "8": "BUCK_PG"},
             152.0, 42.0, datasheet="https://www.ti.com/lit/ds/symlink/tps62160.pdf",
             manufacturer="Texas Instruments", mpn="TPS62160DGKR"),
        part(L, "L1", "2.2uH 1.5A", "Inductor_SMD:L_Abracon_ASPIAIG-F4020", {"1": "BUCK_SW", "2": "+5V"}, 176.0, 42.0,
             manufacturer="Abracon", mpn="ASPIAIG-F4020-2R2M-T"),
        resistor("R1", "680k", "+5V", "BUCK_FB", 196.0, 35.0),
        resistor("R2", "130k", "BUCK_FB", "GND", 196.0, 49.0),
        capacitor("C4", "22pF C0G", "+5V", "BUCK_FB", 214.0, 35.0),
        capacitor("C5", "22uF 10V", "+5V", "GND", 214.0, 49.0, size="1206"),
        capacitor("C6", "22uF 10V", "+5V", "GND", 230.0, 49.0, size="1206"),
        resistor("R3", "100k", "+5V", "BUCK_PG", 230.0, 35.0),
        part(LDO, "U2", "TPS7A2033PDBV", "Package_TO_SOT_SMD:SOT-23-5",
             {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3_A"}, 254.0, 42.0,
             datasheet="https://www.ti.com/lit/ds/symlink/tps7a20.pdf",
             manufacturer="Texas Instruments", mpn="TPS7A2033PDBVR"),
        capacitor("C7", "1uF 10V", "+5V", "GND", 274.0, 35.0, size="0805"),
        capacitor("C8", "4.7uF 10V", "+3V3_A", "GND", 274.0, 49.0, size="0805"),
        part(VREF, "U3", "TLE2426ID", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
             {"1": "VREF", "2": "GND", "3": "+9V", "4": None, "5": None, "6": None, "7": None, "8": "VREF_NR"},
             304.0, 42.0, datasheet="https://www.ti.com/lit/ds/symlink/tle2426.pdf",
             manufacturer="Texas Instruments", mpn="TLE2426IDR"),
        capacitor("C9", "1uF 10V", "VREF_NR", "GND", 326.0, 35.0, size="0805"),
        capacitor("C10", "47uF 10V", "VREF", "GND", 326.0, 49.0, size="1206"),
        capacitor("C11", "100nF", "VREF", "GND", 342.0, 49.0),
        # RC-filtered electret bias rail: keeps buck-input noise off the
        # capsule bias feeds (review finding, 2026-07-25).
        resistor("R67", "100R MIC BIAS FILTER", "+9V", "+9V_MIC", 356.0, 28.0),
        polarized_cap("C66", "100uF 16V", "+9V_MIC", "GND", 370.0, 28.0),
    ])

    # Explicit power-source flags keep ERC strict without hiding internally generated rails.
    for index, (net, x) in enumerate((("GND", 356.0), ("+9V", 368.0), ("+5V", 380.0), ("ADC_LDO", 392.0), ("HP_VSS", 404.0), ("TEENSY_VIN", 416.0), ("HPVDD", 428.0)), start=1):
        p.append(part(PWR_FLAG, f"#FLG0{index}", "PWR_FLAG", "", {"1": net}, x, 42.0,
                      hide_reference=True, hide_value=True, in_bom=False, on_board=False))

    # DE-9 microphone cable: four isolated capsule pairs and shield pin 5.
    # Rev B (2026-07-25): mic input is a shielded RJ45. Each electret rides a
    # proper T568 twisted pair (signal+return): FLU=1/2, FRD=3/6, BLD=4/5,
    # BRU=7/8; the cable shield lands on the jack shell -> CHASSIS.
    p.append(part(RJ45S, "J2", "AMBISONIC MIC RJ45", "Connector_RJ:RJ45_Amphenol_RJHSE5380",
                  {"1": "FLU_RAW", "2": "GND", "3": "FRD_RAW", "6": "GND",
                   "4": "BLD_RAW", "5": "GND", "7": "BRU_RAW", "8": "GND",
                   "SH": "CHASSIS"},
                  28.0, 88.0, manufacturer="Amphenol ICC", mpn="RJHSE-5380"))
    p.extend([
        resistor("R4", "1M", "CHASSIS", "GND", 52.0, 80.0),
        capacitor("C12", "1nF 1kV C0G", "CHASSIS", "GND", 52.0, 92.0, size="0805"),
        resistor("R5", "0R CHASSIS LINK", "CHASSIS", "GND", 52.0, 104.0, dnp=True),
        part(TVS, "D6", "PESD12VL1BA", "Diode_SMD:D_SOD-323", {"1": "FLU_RAW", "2": "CHASSIS"}, 66.0, 80.0,
             datasheet="https://assets.nexperia.com/documents/data-sheet/PESD12VL1BA.pdf",
             manufacturer="Nexperia", mpn="PESD12VL1BA,115"),
        part(TVS, "D7", "PESD12VL1BA", "Diode_SMD:D_SOD-323", {"1": "FRD_RAW", "2": "CHASSIS"}, 66.0, 88.0,
             datasheet="https://assets.nexperia.com/documents/data-sheet/PESD12VL1BA.pdf",
             manufacturer="Nexperia", mpn="PESD12VL1BA,115"),
        part(TVS, "D8", "PESD12VL1BA", "Diode_SMD:D_SOD-323", {"1": "BLD_RAW", "2": "CHASSIS"}, 66.0, 96.0,
             datasheet="https://assets.nexperia.com/documents/data-sheet/PESD12VL1BA.pdf",
             manufacturer="Nexperia", mpn="PESD12VL1BA,115"),
        part(TVS, "D9", "PESD12VL1BA", "Diode_SMD:D_SOD-323", {"1": "BRU_RAW", "2": "CHASSIS"}, 66.0, 104.0,
             datasheet="https://assets.nexperia.com/documents/data-sheet/PESD12VL1BA.pdf",
             manufacturer="Nexperia", mpn="PESD12VL1BA,115"),
    ])

    channel_names = ("FLU", "FRD", "BLD", "BRU")
    channel_y = (84.0, 120.0, 156.0, 192.0)
    # Reference allocations are deliberately regular for review and layout.
    for ch, (name, y) in enumerate(zip(channel_names, channel_y), start=1):
        raw = f"{name}_RAW"
        mic = f"{name}_MIC"
        ac = f"{name}_AC"
        atten = f"{name}_ATT"
        padout = f"{name}_PAD"
        out = f"{name}_PRE"
        fb = f"{name}_FB"
        adcsrc = f"{name}_ADC_SRC"
        adcin = f"{name}_ADC"
        bias_ref = 5 + ch
        series_ref = 9 + ch
        ac_bias_ref = 13 + ch
        atten_ref = 18 + (ch - 1) * 2
        shunt_ref = atten_ref + 1
        rg_ref = 26 + ch - 1
        rf_ref = 30 + ch - 1
        adc_series_ref = 34 + ch - 1
        adc_bleed_ref = 38 + ch - 1
        p.extend([
            resistor(f"R{bias_ref}", "4.7k ELECTRET BIAS", "+9V_MIC", mic, 76.0, y),
            resistor(f"R{series_ref}", "100R RF", raw, mic, 92.0, y),
            capacitor(f"C{12 + ch}", "100pF C0G", mic, "CHASSIS", 108.0, y),
            capacitor(f"C{16 + ch}", "4.7uF 16V", mic, ac, 124.0, y, size="1206"),
            resistor(f"R{ac_bias_ref}", "1M", ac, "VREF", 140.0, y),
            resistor(f"R{atten_ref}", "68k 0.1%", ac, atten, 156.0, y, precision=True),
            resistor(f"R{shunt_ref}", "33k 0.1%", atten, "VREF", 172.0, y, precision=True),
            resistor(f"R{rg_ref}", "10k 0.1%", fb, "VREF", 206.0, y + 8.0, precision=True),
            resistor(f"R{rf_ref}", "90.9k 0.1%", out, fb, 222.0, y + 8.0, precision=True),
            capacitor(f"C{20 + ch}", "22pF C0G", out, fb, 238.0, y + 8.0),
            capacitor(f"C{24 + ch}", "4.7uF 16V", out, adcsrc, 254.0, y, size="1206"),
            resistor(f"R{adc_series_ref}", "100R", adcsrc, adcin, 270.0, y),
            capacitor(f"C{28 + ch}", "10nF C0G", adcin, "GND", 286.0, y),
            # DNP: fights the PCM1864's internal AVDD/2 input self-bias
            # (review finding, 2026-07-25); pads kept for bring-up options.
            resistor(f"R{adc_bleed_ref}", "100k", adcin, "GND", 302.0, y, dnp=True),
        ])

    # Two triple SPDTs provide four matched pad selectors. Select high = direct.
    p.extend([
        part(MUX, "U4", "CD4053BPW", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
             {"1": "FRD_AC", "2": "FRD_ATT", "3": None, "4": None, "5": None, "6": "GND",
              "7": "GND", "8": "GND", "9": "GND", "10": "PAD_SELECT", "11": "PAD_SELECT",
              "12": "FLU_ATT", "13": "FLU_AC", "14": "FLU_PAD", "15": "FRD_PAD", "16": "+9V"},
             188.0, 100.0, datasheet="https://www.ti.com/lit/ds/symlink/cd4053b.pdf",
             manufacturer="Texas Instruments", mpn="CD4053BPWR"),
        part(MUX, "U5", "CD4053BPW", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
             {"1": "BRU_AC", "2": "BRU_ATT", "3": None, "4": None, "5": None, "6": "GND",
              "7": "GND", "8": "GND", "9": "GND", "10": "PAD_SELECT", "11": "PAD_SELECT",
              "12": "BLD_ATT", "13": "BLD_AC", "14": "BLD_PAD", "15": "BRU_PAD", "16": "+9V"},
             188.0, 172.0, datasheet="https://www.ti.com/lit/ds/symlink/cd4053b.pdf",
             manufacturer="Texas Instruments", mpn="CD4053BPWR"),
        part(SW_SPDT, "SW1", "PAD -10dB", "QuadPreRecorder:SW_Toggle_ESwitch_100SP_M7",
             {"1": "GND", "2": "PAD_SELECT", "3": "+9V"}, 224.0, 100.0,
             manufacturer="E-Switch", mpn="100SP1T1B1M7REH",
             description="Right-angle PCB toggle, 1/4-40 x 8.89mm threaded bushing through the left enclosure wall"),
        resistor("R42", "100k", "PAD_SELECT", "PAD_SENSE", 244.0, 100.0),
        resistor("R43", "47k", "PAD_SENSE", "GND", 260.0, 100.0),
        # Series protection for the 0/9V pad level exposed on debug J7.21.
        resistor("R68", "1k", "PAD_SELECT", "PAD_DBG", 244.0, 114.0),
        capacitor("C33", "100nF", "PAD_SENSE", "GND", 276.0, 100.0),
        capacitor("C34", "100nF", "+9V", "GND", 204.0, 110.0),
        capacitor("C35", "100nF", "+9V", "GND", 204.0, 182.0),
    ])

    # Quad OPA1654, one unit per channel plus explicit supply unit.
    op_spec = opa1654_spec()
    op_pin_sets = (
        ("1", "2", "3"), ("7", "6", "5"), ("8", "9", "10"), ("14", "13", "12")
    )
    for unit, (name, y, pins) in enumerate(zip(channel_names, channel_y, op_pin_sets), start=1):
        out_pin, minus_pin, plus_pin = pins
        p.append(part(op_spec, "U6", "OPA1654", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
                      {out_pin: f"{name}_PRE", minus_pin: f"{name}_FB", plus_pin: f"{name}_PAD"},
                      224.0, y, unit=unit, datasheet="https://www.ti.com/lit/ds/symlink/opa1654.pdf",
                      description="Quad low-noise FET-input audio operational amplifier",
                      manufacturer="Texas Instruments", mpn="OPA1654AIPWR"))
    p.append(part(op_spec, "U6", "OPA1654", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
                  {"4": "+9V", "11": "GND"}, 224.0, 210.0, unit=5,
                  datasheet="https://www.ti.com/lit/ds/symlink/opa1654.pdf",
                  description="Quad low-noise FET-input audio operational amplifier",
                  manufacturer="Texas Instruments", mpn="OPA1654AIPWR"))
    p.extend([
        capacitor("C36", "100nF", "+9V", "GND", 244.0, 210.0),
        capacitor("C37", "10uF 16V", "+9V", "GND", 260.0, 210.0, size="1206"),
    ])

    # PCM1864 four-channel 192 kHz ADC and its clocks/control.
    p.append(part(ADC, "U7", "PCM1864DBT", "Package_SO:TSSOP-30_4.4x7.8mm_P0.5mm",
                  {"1": "BLD_ADC", "2": "BRU_ADC", "3": "FLU_ADC", "4": "FRD_ADC",
                   "5": "ADC_MICBIAS", "6": "ADC_VREF", "7": "GND", "8": "+3V3_A",
                   "9": None, "10": None, "11": "ADC_LDO", "12": "GND", "13": "+3V3_D",
                   "14": "+3V3_D", "15": "ADC_MCLK_IC", "16": "ADC_LRCLK_IC", "17": "ADC_BCLK_IC",
                   "18": "ADC_TDM_IC", "19": None, "20": None, "21": None, "22": "ADC_DOUT2_IC",
                   "23": "I2C_SDA", "24": "I2C_SCL", "25": "GND", "26": "GND",
                   "27": None, "28": None, "29": None, "30": None},
                  334.0, 112.0, datasheet="https://www.ti.com/lit/ds/symlink/pcm1864.pdf",
                  description="Four-channel software-controlled 192 kHz audio ADC with matched PGA",
                  manufacturer="Texas Instruments", mpn="PCM1864DBTR"))
    p.extend([
        capacitor("C38", "1uF", "ADC_MICBIAS", "GND", 306.0, 78.0, size="0805"),
        capacitor("C39", "1uF", "ADC_VREF", "GND", 322.0, 78.0, size="0805"),
        capacitor("C40", "100nF", "ADC_VREF", "GND", 338.0, 78.0),
        capacitor("C41", "100nF", "+3V3_A", "GND", 354.0, 78.0),
        capacitor("C42", "10uF", "+3V3_A", "GND", 370.0, 78.0, size="1206"),
        capacitor("C43", "100nF", "ADC_LDO", "GND", 386.0, 78.0),
        capacitor("C44", "100nF", "+3V3_D", "GND", 402.0, 78.0),
        capacitor("C45", "10uF", "+3V3_D", "GND", 418.0, 78.0, size="1206"),
        capacitor("C62", "10uF", "ADC_LDO", "GND", 434.0, 78.0, size="1206"),
        capacitor("C63", "100nF", "+3V3_D", "GND", 450.0, 78.0),
        resistor("R44", "4.7k", "+3V3_D", "I2C_SDA", 306.0, 146.0),
        resistor("R45", "4.7k", "+3V3_D", "I2C_SCL", 322.0, 146.0),
        resistor("R46", "33R", "ADC_MCLK", "ADC_MCLK_IC", 338.0, 146.0),
        resistor("R47", "33R", "ADC_LRCLK", "ADC_LRCLK_IC", 354.0, 146.0),
        resistor("R48", "33R", "ADC_BCLK", "ADC_BCLK_IC", 370.0, 146.0),
        resistor("R49", "33R", "ADC_TDM_IC", "ADC_TDM", 386.0, 146.0),
        # Second serial-audio data line (PCM1864 GPIO0 as DOUT2, 2x I2S mode)
        # so all four channels can run at 192 kHz on Teensy SAI1 quad input.
        resistor("R69", "33R", "ADC_DOUT2_IC", "ADC_DOUT2", 402.0, 146.0),
    ])

    # Teensy module. Unused accessible pins are intentionally no-connect.
    teensy_nets: dict[str, str | None] = {key: None for key in teensy_pins()}
    teensy_nets.update({
        "GND1": "GND", "GND2": "GND", "GND3": "GND", "VIN": "TEENSY_VIN",
        "3V3A": "+3V3_D", "3V3B": "+3V3_D",
        "2": "DAC_DIN", "3": "DAC_LRCLK", "4": "DAC_BCLK",
        "6": "ADC_DOUT2", "7": "TFT_RST", "8": "ADC_TDM",
        # Rev B: pin 5 freed (capacitive TOUCH_RST gone); pin 24 drives the
        # MSP3520's XPT2046 touch chip-select on the shared SPI bus.
        "24": "TOUCH_CS",
        "9": "TFT_DC", "10": "TFT_CS", "11": "SPI_MOSI", "12": "SPI_MISO", "13": "SPI_SCK",
        "18": "I2C_SDA", "19": "I2C_SCL", "20": "ADC_LRCLK", "21": "ADC_BCLK",
        "22": "TOUCH_IRQ", "23": "ADC_MCLK", "28": "REC_BUTTON", "29": "GAIN_A",
        "30": "GAIN_B", "31": "GAIN_PUSH", "32": "PAD_SENSE", "33": "HP_ENABLE",
        "34": "DAC_MUTE", "35": "REC_LED",
        # 5-way TFT menu navigation switch (SW4). Direction-to-pin mapping is
        # firmware-remappable if the physical part reads differently.
        "36": "NAV_UP", "37": "NAV_DOWN", "38": "NAV_LEFT", "39": "NAV_RIGHT",
        "40": "NAV_PUSH",
    })
    p.append(part("QuadPreRecorder:Teensy41", "U8", "Teensy 4.1", "QuadPreRecorder:Teensy41_Socket",
                  teensy_nets, 340.0, 202.0, datasheet="https://www.pjrc.com/store/teensy41.html",
                  description="600 MHz Cortex-M7 module with native 4-bit SDIO microSD",
                  manufacturer="PJRC", mpn="TEENSY41"))
    p.extend([
        part(DIODE, "D3", "SS14", "Diode_SMD:D_SMA", {"2": "+5V", "1": "TEENSY_VIN"}, 304.0, 176.0,
             manufacturer="Diodes Incorporated", mpn="SS14-13-F"),
        capacitor("C46", "10uF", "TEENSY_VIN", "GND", 320.0, 176.0, size="1206"),
    ])

    # Recorder controls and the selected LCDWiki MSP2834 capacitive-touch
    # 14-pin ILI9341/FT6336G display header.
    p.extend([
        part(SW_PUSH, "SW2", "RECORD START/STOP", "Button_Switch_THT:SW_PUSH-12mm",
             {"1": "REC_BUTTON", "2": "GND"}, 286.0, 234.0,
             manufacturer="Omron", mpn="B3F-5150",
             description="12mm tactile switch, 17.5mm tall plunger to reach the 1590F lid"),
        resistor("R50", "10k", "+3V3_D", "REC_BUTTON", 286.0, 248.0),
        capacitor("C47", "100nF", "REC_BUTTON", "GND", 302.0, 248.0),
        part(ENCODER, "SW3", "MASTER GAIN", "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
             {"A": "GAIN_A", "B": "GAIN_B", "C": "GND", "S1": "GAIN_PUSH", "S2": "GND"},
             326.0, 248.0, manufacturer="Alps Alpine", mpn="EC11E15244G1"),
        # 5-way TFT menu navigation (added 2026-07-25): ALPS SKQUCAA010,
        # 4 directions + center push, active-low with 10k pullups + 100nF
        # debounce like the other panel controls. Stem is ~10mm above the
        # board vs the 16.5mm lid gap - a ~6.5mm stem-extension cap reaches
        # the lid (see enclosure-stackup-and-templates.md).
        part("QuadPreRecorder:SW_Nav5", "SW4", "TFT MENU NAV", "QuadPreRecorder:SW_Nav_ALPS_SKQUCAA010",
             {"1": "NAV_UP", "2": "NAV_LEFT", "3": "NAV_DOWN", "4": "GND",
              "5": "NAV_RIGHT", "6": "NAV_PUSH"}, 548.0, 244.0,
             datasheet="https://cdn-shop.adafruit.com/datasheets/SKQUCAA010-ALPS.pdf",
             description="ALPS 4-directional + center push TACT switch, snap-in",
             manufacturer="Alps Alpine", mpn="SKQUCAA010"),
        resistor("R70", "10k", "+3V3_D", "NAV_UP", 572.0, 224.0),
        resistor("R71", "10k", "+3V3_D", "NAV_DOWN", 572.0, 234.0),
        resistor("R72", "10k", "+3V3_D", "NAV_LEFT", 572.0, 244.0),
        resistor("R73", "10k", "+3V3_D", "NAV_RIGHT", 572.0, 254.0),
        resistor("R74", "10k", "+3V3_D", "NAV_PUSH", 572.0, 264.0),
        capacitor("C69", "100nF", "NAV_UP", "GND", 588.0, 224.0),
        capacitor("C70", "100nF", "NAV_DOWN", "GND", 588.0, 234.0),
        capacitor("C71", "100nF", "NAV_LEFT", "GND", 588.0, 244.0),
        capacitor("C72", "100nF", "NAV_RIGHT", "GND", 588.0, 254.0),
        capacitor("C73", "100nF", "NAV_PUSH", "GND", 588.0, 264.0),
        resistor("R51", "10k", "+3V3_D", "GAIN_A", 350.0, 236.0),
        resistor("R52", "10k", "+3V3_D", "GAIN_B", 366.0, 236.0),
        resistor("R53", "10k", "+3V3_D", "GAIN_PUSH", 382.0, 236.0),
        capacitor("C48", "10nF", "GAIN_A", "GND", 350.0, 250.0),
        capacitor("C49", "10nF", "GAIN_B", "GND", 366.0, 250.0),
        capacitor("C50", "100nF", "GAIN_PUSH", "GND", 382.0, 250.0),
        # Rev B display: LCDWiki MSP3520 3.5in 480x320 (ILI9488 + XPT2046
        # resistive touch). Same 14-pin header; touch rides the SPI bus with
        # its own chip-select instead of I2C (I2C now serves only the ADC).
        part(CONN14, "J3", "MSP3520 TFT 3.5IN 14PIN HEADER", "Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical",
             {"1": "+5V", "2": "GND", "3": "TFT_CS", "4": "TFT_RST", "5": "TFT_DC",
              "6": "SPI_MOSI", "7": "SPI_SCK", "8": "TFT_LED", "9": "SPI_MISO",
              "10": "SPI_SCK", "11": "TOUCH_CS", "12": "SPI_MOSI", "13": "SPI_MISO", "14": "TOUCH_IRQ"},
             408.0, 222.0, manufacturer="Sullins Connector Solutions", mpn="PRPC014SAAN-RC",
             description="14-pin 2.54 mm header for LCDWiki MSP3520 ILI9488/XPT2046 3.5in resistive-touch TFT module"),
        # Rev B: the external debug DB-25s became internal 0.1" test headers
        # (2x13, pin 26 unused). Same signals, same pin numbers, no wall
        # cutouts, no EMI stubs to big connectors.
        part(DB25, "J6", "ANALOG TEST HEADER 2x13", "Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical",
             {"1": "GND", "2": "CHASSIS", "3": "+9V", "4": "VREF",
              "5": "FLU_RAW", "6": "FLU_AC", "7": "FLU_PAD", "8": "FLU_PRE", "9": "FLU_ADC",
              "10": "FRD_RAW", "11": "FRD_AC", "12": "FRD_PAD", "13": "FRD_PRE", "14": "FRD_ADC",
              "15": "BLD_RAW", "16": "BLD_AC", "17": "BLD_PAD", "18": "BLD_PRE", "19": "BLD_ADC",
              "20": "BRU_RAW", "21": "BRU_AC", "22": "BRU_PAD", "23": "BRU_PRE", "24": "BRU_ADC",
              "25": "GND"},
             408.0, 256.0, manufacturer="Generic", mpn="2x13 0.1in pin header",
             description="Internal analog test header: every stage of all four channels"),
        part(DB25, "J7", "DIGITAL TEST HEADER 2x13", "Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical",
             {"1": "GND", "2": "+5V", "3": "+3V3_D", "4": "ADC_MCLK",
              "5": "ADC_BCLK", "6": "ADC_LRCLK", "7": "ADC_TDM", "8": "DAC_BCLK",
              "9": "DAC_LRCLK", "10": "DAC_DIN", "11": "DAC_MUTE", "12": "I2C_SDA",
              "13": "I2C_SCL", "14": "SPI_SCK", "15": "SPI_MOSI", "16": "SPI_MISO",
              "17": "TFT_CS", "18": "TFT_DC", "19": "TOUCH_CS", "20": "TOUCH_IRQ",
              "21": "PAD_DBG", "22": "REC_BUTTON", "23": "HP_ENABLE", "24": "REC_LED",
              "25": "GND"},
             438.0, 256.0, manufacturer="Generic", mpn="2x13 0.1in pin header",
             description="Internal digital/control test header: every bus and control line"),
        part(LED, "D4", "POWER BLUE", "LED_SMD:LED_0603_1608Metric", {"1": "GND", "2": "PWR_LED_A"}, 400.0, 250.0,
             manufacturer="Lite-On", mpn="LTST-C190TBKT"),
        resistor("R54", "2.2k", "+5V", "PWR_LED_A", 416.0, 250.0),
        part(LED, "D5", "RECORD RED", "LED_SMD:LED_0603_1608Metric", {"1": "GND", "2": "REC_LED_A"}, 400.0, 264.0,
             manufacturer="Lite-On", mpn="LTST-C190KRKT"),
        resistor("R55", "1k", "REC_LED", "REC_LED_A", 416.0, 264.0),
        part(R, "R56", "100R TFT BACKLIGHT", "Resistor_SMD:R_0805_2012Metric", {"1": "+5V", "2": "TFT_LED"}, 432.0, 250.0,
             manufacturer="Yageo", mpn="RC0805FR-07100RL"),
    ])

    # Stereo DAC and binaural line output; the volume pot + DirectPath
    # headphone amp are fed from the line-out nets, so headphones hear an
    # amplified duplicate of exactly the line-out signal.
    p.append(part(DAC, "U9", "PCM5102A", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                  {"1": "+3V3_A", "2": "DAC_CAPP", "3": "GND", "4": "DAC_CAPM", "5": "DAC_VNEG",
                   "6": "DAC_L", "7": "DAC_R", "8": "+3V3_A", "9": "GND", "10": "GND", "11": "GND",
                   "12": "GND", "13": "DAC_BCLK_IC", "14": "DAC_DIN_IC", "15": "DAC_LRCLK_IC",
                   "16": "GND", "17": "DAC_MUTE_IC", "18": "DAC_LDO", "19": "GND", "20": "+3V3_D"},
                  300.0, 294.0, datasheet="https://www.ti.com/lit/ds/symlink/pcm5102a.pdf",
                  manufacturer="Texas Instruments", mpn="PCM5102APWR"))
    p.extend([
        capacitor("C51", "2.2uF", "DAC_CAPP", "DAC_CAPM", 330.0, 276.0, size="0805"),
        capacitor("C52", "2.2uF", "DAC_VNEG", "GND", 346.0, 276.0, size="0805"),
        capacitor("C53", "1uF", "DAC_LDO", "GND", 362.0, 276.0, size="0805"),
        capacitor("C54", "100nF", "+3V3_A", "GND", 378.0, 276.0),
        capacitor("C55", "10uF", "+3V3_A", "GND", 394.0, 276.0, size="1206"),
        capacitor("C56", "100nF", "+3V3_D", "GND", 410.0, 276.0),
        capacitor("C64", "100nF", "+3V3_A", "GND", 426.0, 276.0),
        resistor("R57", "33R", "DAC_BCLK", "DAC_BCLK_IC", 330.0, 310.0),
        resistor("R58", "33R", "DAC_DIN", "DAC_DIN_IC", 346.0, 310.0),
        resistor("R59", "33R", "DAC_LRCLK", "DAC_LRCLK_IC", 362.0, 310.0),
        # Pull-DOWN: DAC stays muted until the Teensy actively raises XSMT
        # (review finding, 2026-07-25 — was a pull-up to +3V3_D).
        resistor("R60", "10k", "DAC_MUTE_IC", "GND", 378.0, 310.0),
        resistor("R61", "100R", "DAC_MUTE", "DAC_MUTE_IC", 394.0, 310.0),
        # TI-recommended PCM5102A line-out filter: 470R series + 2.2nF shunt.
        resistor("R62", "470R", "DAC_L", "LINE_L", 318.0, 330.0),
        resistor("R63", "470R", "DAC_R", "LINE_R", 334.0, 330.0),
        capacitor("C67", "2.2nF C0G", "LINE_L", "GND", 318.0, 344.0),
        capacitor("C68", "2.2nF C0G", "LINE_R", "GND", 334.0, 344.0),
        part(JACK_TRS, "J4", "1/4in BINAURAL LINE OUT", "Connector_Audio:Jack_6.35mm_Neutrik_NRJ6HF_Horizontal",
             {"T": "LINE_L", "R": "LINE_R", "S": "GND"}, 354.0, 330.0,
             manufacturer="Neutrik", mpn="NRJ6HF"),
        # Headphone path taps LINE_L/LINE_R (post reconstruction filter), not
        # the raw DAC pins, so the headphone out is an exact amplified
        # duplicate of the binaural line out (change 2026-07-25). The 10k pot
        # loads the 470R filter by only ~0.4 dB.
        part(POT_DUAL, "RV1", "10kA HEADPHONE VOLUME", "QuadPreRecorder:RK097_Dual_Horizontal_NoEdgeGuide",
             {"1": "LINE_L", "2": "HP_VOL_L", "3": "GND", "4": "LINE_R", "5": "HP_VOL_R", "6": "GND"},
             386.0, 330.0, manufacturer="Alps Alpine", mpn="RK0971221-F15-C0-A103"),
        capacitor("C57", "680nF X7R", "HP_VOL_L", "HP_IN_L", 414.0, 324.0, size="0805"),
        capacitor("C58", "680nF X7R", "HP_VOL_R", "HP_IN_R", 414.0, 338.0, size="0603"),
        part(HPAMP, "U10", "TPA6132A2", "Package_DFN_QFN:WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
             {"1": "HP_IN_L", "2": "GND", "3": "GND", "4": "HP_IN_R", "5": "HP_OUT_R",
              "6": "+3V3_D", "7": "GND", "8": "HP_VSS", "9": "HP_CPN", "10": "GND",
             "11": "HP_CPP", "12": "HPVDD", "13": "HP_ENABLE", "14": "+5V", "15": "GND",
              "16": "HP_OUT_L", "17": "GND"}, 446.0, 330.0,
             datasheet="https://www.ti.com/lit/ds/symlink/tpa6132a2.pdf",
             manufacturer="Texas Instruments", mpn="TPA6132A2RTER"),
        capacitor("C59", "1uF", "HP_CPP", "HP_CPN", 468.0, 310.0, size="0603"),
        capacitor("C60", "2.2uF", "HP_VSS", "GND", 484.0, 310.0, size="0603"),
        capacitor("C61", "2.2uF", "HPVDD", "GND", 500.0, 310.0, size="0603"),
        capacitor("C65", "2.2uF", "+5V", "GND", 516.0, 310.0, size="0603"),
        resistor("R64", "100k", "HP_ENABLE", "GND", 468.0, 344.0),
        resistor("R65", "10R", "HP_OUT_L", "HP_JACK_L", 484.0, 344.0),
        resistor("R66", "10R", "HP_OUT_R", "HP_JACK_R", 500.0, 344.0),
        part(JACK_TRS, "J5", "1/8in BINAURAL HEADPHONE OUT", "Connector_Audio:Jack_3.5mm_CUI_SJ1-3533NG_Horizontal",
             {"T": "HP_JACK_L", "R": "HP_JACK_R", "S": "GND"}, 522.0, 330.0,
             manufacturer="CUI Devices", mpn="SJ1-3533NG"),
    ])

    return p


def build() -> tuple[str, list[Part]]:
    registry = REGISTRY
    parts = build_parts()
    # Register every stock/custom symbol before serializing lib_symbols.
    for item in parts:
        if isinstance(item.spec, LibrarySymbol):
            registry.register(item.spec)
    registry.embedded["QuadPreRecorder:TPS7A20DBV"] = registry.embedded["QuadPreRecorder:TPS7A20DBV"].replace(
        "LP5907MFX-1.2", "TPS7A20DBV"
    )
    registry.embedded["QuadPreRecorder:PCM5102A"] = registry.embedded["QuadPreRecorder:PCM5102A"].replace(
        "PCM5100", "PCM5102A"
    )
    registry.embedded["QuadPreRecorder:Teensy41"] = custom_teensy_symbol()
    registry.embedded["QuadPreRecorder:SW_Nav5"] = custom_nav_symbol()

    sch = Schematic(registry)
    sch.text("QUAD PREAMP + 4-CHANNEL AMBISONIC RECORDER", 15.0, 15.0, 2.20, True)
    sch.text("192 kHz / 24-bit capture • real-time binaural monitor • two-layer Rev B (Hammond 1590XX)", 15.0, 21.0, 1.25)

    sch.text("POWER: protected 9 V input, 5 V buck, quiet 3.3 V audio rail, 4.5 V virtual ground", 15.0, 29.0, 1.30, True)
    sch.text("MICROPHONE INPUT + FOUR MATCHED CHANNELS", 15.0, 67.0, 1.30, True)
    sch.text("RJ45 (shielded): pair 1/2 FLU+ret; pair 3/6 FRD+ret; pair 4/5 BLD+ret; pair 7/8 BRU+ret; shell = shield to CHASSIS", 15.0, 72.0, 1.00)
    sch.text("One PAD switch controls four CD4053 paths: HIGH=direct, LOW=-9.7 dB. OPA1654 fixed gain is 20.1 dB.", 15.0, 76.0, 1.00)
    for name, y in zip(("FLU", "FRD", "BLD", "BRU"), (84.0, 120.0, 156.0, 192.0)):
        sch.text(f"{name} CHANNEL", 64.0, y - 9.0, 1.10, True)

    sch.text("ADC + DIGITAL AUDIO", 294.0, 67.0, 1.30, True)
    sch.text("PCM1864: four single-ended inputs, common software PGA, 192 kHz 4-slot TDM", 294.0, 72.0, 1.00)
    sch.text("CONTROLLER, TOUCHSCREEN, RECORD CONTROLS", 278.0, 162.0, 1.30, True)
    sch.text("Teensy 4.1 records four mono WAV files over native SDIO and decodes the 48 kHz binaural monitor.", 278.0, 168.0, 1.00)
    sch.text("J6/J7 are internal 2x13 0.1in test headers (Rev B): open the bottom plate to probe any stage or bus.", 278.0, 174.0, 1.00)
    sch.text("STEREO BINAURAL DAC, LINE OUTPUT, AND HEADPHONE AMPLIFIER", 278.0, 268.0, 1.30, True)
    sch.text("PCM5102A ground-centered line output; headphone path is an amplified duplicate of LINE_L/R (TPA6132A2, 0 dB, DirectPath, HP_ENABLE).", 278.0, 273.0, 1.00)
    sch.text("USB/POWER NOTE: do not connect 9 V barrel power and Teensy USB simultaneously unless the Teensy VIN-VUSB link is cut.", 15.0, 226.0, 1.05, True)
    sch.text("DISPLAY NOTE: J3 targets LCDWiki MSP3520 ILI9488/XPT2046 3.5in resistive touch (480x320); its mounting-hole pattern is UNPUBLISHED - verify against the physical module before drilling.", 15.0, 232.0, 1.05)
    sch.text("CAPSULE NOTE: this input is only for four independent two-wire electrets with internal FETs; confirm bias polarity and current.", 15.0, 238.0, 1.05)
    sch.text("Rev A by jdg511 • https://github.com/jdg511/quadpreandrecorder", 15.0, 244.0, 1.05)

    for item in parts:
        sch.symbol(item)

    header = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "quadpreandrecorder_generator")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{ROOT_UUID}")',
        '\t(paper "A2")',
        "\t(title_block",
        '\t\t(title "Quad Preamp and Recorder — Four-Channel Ambisonic Front End")',
        '\t\t(date "2026-07-19")',
        '\t\t(rev "A-prototype")',
        '\t\t(company "jdg511")',
        '\t\t(comment 1 "https://github.com/jdg511/quadpreandrecorder")',
        '\t\t(comment 2 "Four 192 kHz / 24-bit simultaneous microphone channels")',
        '\t\t(comment 3 "Hammond 1590XX • two copper layers • Rev B")',
        '\t\t(comment 4 "Prototype before production; see hardware/requirements.md")',
        "\t)",
        "\t(lib_symbols",
    ]
    for identifier in sorted(registry.embedded):
        header.extend("\t\t" + line for line in registry.embedded[identifier].splitlines())
    header.append("\t)")
    footer = [
        "\t(sheet_instances",
        '\t\t(path "/" (page "1"))',
        "\t)",
        "\t(embedded_fonts no)",
        ")",
    ]
    return "\n".join(header + sch.items + footer) + "\n", parts


def build_local_symbol_library() -> str:
    blocks = [
        REGISTRY.embedded["QuadPreRecorder:OPA1654"],
        REGISTRY.embedded["QuadPreRecorder:TPS7A20DBV"],
        REGISTRY.embedded["QuadPreRecorder:PCM5102A"],
        custom_teensy_symbol(),
        custom_nav_symbol(),
    ]
    # Local libraries use unqualified names at the library root.
    cleaned = []
    for source in blocks:
        cleaned.append(source.replace('(symbol "QuadPreRecorder:', '(symbol "', 1))
    body: list[str] = [
        "(kicad_symbol_lib", "\t(version 20251024)",
        '\t(generator "quadpreandrecorder_generator")', '\t(generator_version "1.0")',
    ]
    for block in cleaned:
        body.extend("\t" + line for line in block.splitlines())
    body.extend([")", ""])
    return "\n".join(body)


def write_project_scaffolding() -> None:
    project_path = HARDWARE / "QuadPreRecorder.kicad_pro"
    if not project_path.exists():
        project_path.write_text(
            "{\n"
            '  "board": {},\n'
            '  "boards": [],\n'
            '  "cvpcb": {},\n'
            '  "erc": {},\n'
            '  "libraries": {},\n'
            '  "meta": {"filename": "QuadPreRecorder.kicad_pro", "version": 1},\n'
            '  "net_settings": {"classes": [], "meta": {"version": 3}},\n'
            '  "pcbnew": {},\n'
            '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": [], "top_level_sheets": [{"filename": "QuadPreRecorder.kicad_sch", "name": "QuadPreRecorder", "uuid": "ad984389-991b-4f10-bf10-bd77562cc42d"}]},\n'
            '  "sheets": [],\n'
            '  "text_variables": {}\n'
            "}\n",
            encoding="utf-8",
        )
    (HARDWARE / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "QuadPreRecorder")(type "KiCad")(uri "${KIPRJMOD}/QuadPreRecorder.kicad_sym")(options "")(descr "Project-local symbols"))\n)\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    HARDWARE.mkdir(parents=True, exist_ok=True)
    schematic, generated_parts = build()
    OUT.write_text(schematic, encoding="utf-8")
    LOCAL_LIB_OUT.write_text(build_local_symbol_library(), encoding="utf-8")
    write_project_scaffolding()
    print(OUT)
    print(f"Symbol instances: {len(generated_parts)}")
