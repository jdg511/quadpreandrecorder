"""Mark footprints whose duplicate pad numbers are bridged inside the part.

A 12 mm tact switch like SW2 (Button_Switch_THT:SW_PUSH-12mm) has four legs
but only two nets: pads 1,1,2,2. The two "1" legs are the same contact inside
the moulding, so no copper is needed between them. KiCad does not assume that
- it reports "missing connection between pad 1 of SW2 and pad 1 of SW2" until
the footprint says so, via duplicate_pad_numbers_are_jumpers.

Any footprint that reuses a pad number is making exactly that claim, so this
flips the flag wherever duplicates exist and leaves everything else alone.
Run after generate_pcb.py, before DRC.
"""
import sys
from collections import Counter
from pathlib import Path

import pcbnew

PCB = sys.argv[1] if len(sys.argv) > 1 else "hardware/QuadPreRecorder.kicad_pcb"

board = pcbnew.LoadBoard(PCB)
changed = []

for fp in board.Footprints():
    numbers = [p.GetNumber() for p in fp.Pads() if p.GetNumber()]
    dupes = [n for n, c in Counter(numbers).items() if c > 1]
    if not dupes:
        continue
    if fp.GetDuplicatePadNumbersAreJumpers():
        continue
    fp.SetDuplicatePadNumbersAreJumpers(True)
    changed.append((fp.GetReference(), sorted(dupes)))

for ref, dupes in changed:
    print("  %-6s duplicate pad numbers %s -> treated as internal jumpers"
          % (ref, ",".join(dupes)))
print("footprints updated: %d" % len(changed))

if changed:
    board.Save(PCB)
    print(str(Path(PCB).resolve()))
