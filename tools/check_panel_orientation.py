#!/usr/bin/env python3
"""Verify every panel part's fab outline actually faces its enclosure wall.

Pure-python (no pcbnew) — run with any Python 3 after regenerating the board:

    python tools/check_panel_orientation.py

Parses hardware/QuadPreRecorder.kicad_pcb, transforms each panel footprint's
F.Fab/B.Fab outline to board coordinates, and asserts the protruding feature
(nose/bushing/shaft/shell) extends toward the correct board edge. Exits 1 and
prints the measured extents on any failure, so a wrong rotation is caught
before routing or ordering. Added 2026-07-25 after J4/RV1 were found rotated
parallel to their walls.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1] / "hardware" / "QuadPreRecorder.kicad_pcb"
# Rev B: Hammond 1590XX board, 138 x 114. y=0 REAR, y=114 FRONT,
# x=0 LEFT (mic), x=138 RIGHT (volume/phones).
W = 138.0
H = 114.0

# ref -> (edge, min protrusion in mm past the board edge that the fab outline
# must reach; negative allows the tip to stop short of the edge)
RULES = {
    "J2": ("west", -1.5),   # RJ45 port face at/near the left edge
    "SW1": ("west", 4.0),   # pad toggle bushing through the left wall
    "J5": ("east", 0.3),    # 3.5mm phones nose just past the right edge
    "RV1": ("east", 10.0),  # volume shaft well past the right edge
    "J1": ("south", 3.0),   # 9V barrel nose past the front edge
    "J4": ("south", 5.0),   # NRJ6HF line-out bushing through the front wall
    # Teensy SD end must sit at the REAR edge (within 4mm) so the card
    # reaches the wall slot; a flipped module fails this by ~57mm.
    "U8": ("north", -4.0),
}


def footprint_blocks(text: str):
    i = 0
    while True:
        j = text.find("(footprint ", i)
        if j < 0:
            return
        depth = 0
        k = j
        while True:
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        yield text[j:k + 1]
        i = k + 1


def fab_extents(block: str):
    at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", block)
    fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    r = math.radians(rot)
    xs, ys = [], []
    for m in re.finditer(r"\(fp_(?:line|rect|poly|arc|circle)\b", block):
        s = m.start()
        depth = 0
        k = s
        while True:
            if block[k] == "(":
                depth += 1
            elif block[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        item = block[s:k + 1]
        if '.Fab"' not in item:
            continue
        for pm in re.finditer(r"\((?:start|end|xy|mid|center)\s+([-\d.]+)\s+([-\d.]+)\)", item):
            px, py = float(pm.group(1)), float(pm.group(2))
            xs.append(fx + px * math.cos(r) + py * math.sin(r))
            ys.append(fy - px * math.sin(r) + py * math.cos(r))
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def main() -> int:
    text = BOARD.read_text(encoding="utf-8", errors="ignore")
    found: dict[str, tuple] = {}
    for block in footprint_blocks(text):
        m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not m or m.group(1) not in RULES:
            continue
        ext = fab_extents(block)
        if ext:
            found[m.group(1)] = ext

    failures = 0
    for ref, (edge, need) in sorted(RULES.items()):
        if ref not in found:
            print(f"FAIL {ref}: footprint or fab outline not found")
            failures += 1
            continue
        x0, y0, x1, y1 = found[ref]
        got = {"west": -x0, "east": x1 - W, "south": y1 - H, "north": -y0}[edge]
        ok = got >= need
        status = "ok  " if ok else "FAIL"
        print(f"{status} {ref:4s} {edge:5s} protrusion {got:+6.2f} mm (need >= {need:+.2f})  "
              f"fab X {x0:7.2f}..{x1:7.2f}  Y {y0:7.2f}..{y1:7.2f}")
        failures += 0 if ok else 1
    if failures:
        print(f"\n{failures} orientation check(s) FAILED — fix rotations in "
              "tools/generate_pcb.py placements() before routing.")
        return 1
    print("\nAll panel orientations correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
