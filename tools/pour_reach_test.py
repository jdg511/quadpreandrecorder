"""Can a slightly tighter-filling GND pour reach the last stranded pads?

U6.11, U4.9, C38.2, C41.2 and C43.2 sit in pockets where the pour is pinched
off before it gets to them, and there is no room beside them for an escape
via. The pour currently fills with min_thickness 0.20-0.25 mm and a 0.25 mm
clearance; dropping both lets copper squeeze through necks it currently
abandons.

Note this is the OPPOSITE of an earlier experiment that RAISED min fill width
to 0.30 and made things worse. PCBWay's cheap tier does 0.127 mm trace /
0.127 mm space, so 0.15/0.20 is still comfortably inside spec.

Writes to a scratch copy so the good board is never at risk.
"""
import shutil
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
GOOD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
TEST = ROOT / "hardware" / "review_outputs" / "pour-reach-test.kicad_pcb"

MIN_THICK = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
CLEAR = float(sys.argv[2]) if len(sys.argv) > 2 else 0.20

TEST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(GOOD, TEST)

board = pcbnew.LoadBoard(str(TEST))
gndcode = board.FindNet("GND").GetNetCode()

touched = 0
for zone in board.Zones():
    if zone.GetIsRuleArea() or zone.GetNetCode() != gndcode:
        continue
    zone.SetMinThickness(pcbnew.FromMM(MIN_THICK))
    zone.SetLocalClearance(pcbnew.FromMM(CLEAR))
    touched += 1
print("zones retuned: %d  (min_thickness %.2f, clearance %.2f)"
      % (touched, MIN_THICK, CLEAR))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.BuildConnectivity()
conn = board.GetConnectivity()

pads = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == gndcode:
            pads.append((fp.GetReference() + "." + p.GetNumber(), p))

parent = {n: n for n, _ in pads}

def find(k):
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k

index = {p.m_Uuid.AsString(): n for n, p in pads}
for name, p in pads:
    for item in conn.GetConnectedItems(p, 0):
        other = index.get(item.m_Uuid.AsString())
        if other is not None:
            a, b = find(name), find(other)
            if a != b:
                parent[a] = b

groups = {}
for name, _p in pads:
    groups.setdefault(find(name), []).append(name)
ordered = sorted(groups.values(), key=len, reverse=True)
print("GND pad clusters: %d, main has %d of %d pads"
      % (len(ordered), len(ordered[0]), len(pads)))
for g in ordered[1:]:
    print("   ORPHAN: %s" % ", ".join(sorted(g)))
print("KiCad unconnected count: %d" % conn.GetUnconnectedCount(True))

pcbnew.SaveBoard(str(TEST), board)
print(TEST)
