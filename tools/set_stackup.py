"""Rev C3 (2026-09-12): write an explicit 4-layer stackup into the board file.

Until now the board had no stackup block, so the fab's default applied
silently: F / 0.21 prepreg / In1 / 1.065 core / In2 / 0.21 prepreg / B
(1.6 mm, 35 um copper). That build is now exactly what the design wants -
both inner layers are solid GND, so each outer signal layer has a plane
0.21 mm away - and writing it down means the fab, the DRC and the next
review all see the same numbers.

The pcbnew Python bindings do not expose BOARD_STACKUP, so this is a text
edit of the (setup ...) block; idempotent. Verified by the DRC run that
follows it in the pipeline (kicad-cli refuses a malformed file).

Usage: python tools/set_stackup.py [board.kicad_pcb]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"

COPPER = 0.035
PREPREG = 0.21
CORE = 1.065


def diel(n, kind, t):
    return (f'\t\t\t(layer "dielectric {n}"\n\t\t\t\t(type "{kind}")\n\t\t\t\t(thickness {t})\n'
            f'\t\t\t\t(material "FR4")\n\t\t\t\t(epsilon_r 4.5)\n\t\t\t\t(loss_tangent 0.02)\n\t\t\t)\n')


def cu(name):
    return f'\t\t\t(layer "{name}"\n\t\t\t\t(type "copper")\n\t\t\t\t(thickness {COPPER})\n\t\t\t)\n'


STACKUP = (
    '\t\t(stackup\n'
    '\t\t\t(layer "F.SilkS"\n\t\t\t\t(type "Top Silk Screen")\n\t\t\t)\n'
    '\t\t\t(layer "F.Paste"\n\t\t\t\t(type "Top Solder Paste")\n\t\t\t)\n'
    '\t\t\t(layer "F.Mask"\n\t\t\t\t(type "Top Solder Mask")\n\t\t\t\t(thickness 0.01)\n\t\t\t)\n'
    + cu("F.Cu") + diel(1, "prepreg", PREPREG) + cu("In1.Cu") + diel(2, "core", CORE)
    + cu("In2.Cu") + diel(3, "prepreg", PREPREG) + cu("B.Cu") +
    '\t\t\t(layer "B.Mask"\n\t\t\t\t(type "Bottom Solder Mask")\n\t\t\t\t(thickness 0.01)\n\t\t\t)\n'
    '\t\t\t(layer "B.Paste"\n\t\t\t\t(type "Bottom Solder Paste")\n\t\t\t)\n'
    '\t\t\t(layer "B.SilkS"\n\t\t\t\t(type "Bottom Silk Screen")\n\t\t\t)\n'
    '\t\t\t(copper_finish "None")\n'
    '\t\t\t(dielectric_constraints no)\n'
    '\t\t)\n'
)


def main():
    raw = BOARD.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    # drop an existing stackup block (balanced parens) if present
    m = re.search(r"\n\t\t\(stackup\b", text)
    if m:
        i = m.start() + 1
        depth, j = 0, i
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        text = text[:i] + text[j + 1:].lstrip("\n")
        if text[i - 1] != "\n":
            text = text[:i] + "\n" + text[i:]
    m = re.search(r"\n\t\(setup\n", text)
    if not m:
        raise SystemExit("no (setup block found")
    text = text[:m.end()] + STACKUP + text[m.end():]
    if crlf:
        text = text.replace("\n", "\r\n")
    BOARD.write_bytes(text.encode("utf-8"))
    total = 4 * COPPER + 2 * PREPREG + CORE + 0.02
    print(f"stackup written: 4 layers, {int(COPPER*1000)} um Cu, {PREPREG} / {CORE} / {PREPREG} mm dielectric (~{total:.2f} mm)")
    print(BOARD)


if __name__ == "__main__":
    main()
