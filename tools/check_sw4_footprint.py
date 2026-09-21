"""Load the new SW4 footprint through KiCad itself and sanity-check it.

If KiCad can read it and the pads land where we expect, the file is real.
"""
import pcbnew
from pathlib import Path

LIB = str(Path(__file__).resolve().parent.parent / "hardware" / "QuadPreRecorder.pretty")
FP = "SW_Nav5_ALPS_RKJXT1F42001"

EXPECT = {
    "A": (-1.500, 7.800), "5": (1.000, 6.980), "B": (7.800, 1.500),
    "7": (7.800, -1.500), "C": (1.500, -7.800), "9": (-1.500, -7.800),
    "6": (-1.000, -5.780), "D": (-7.800, -1.500), "8": (-7.800, 1.500),
    "10": (6.860, 3.750),
}

fp = pcbnew.FootprintLoad(LIB, FP)
if fp is None:
    raise SystemExit("FAIL: KiCad could not load the footprint")

print("loaded:", fp.GetFPID().GetUniStringLibItemName())

seen = {}
npth = 0
for pad in fp.Pads():
    name = pad.GetNumber()
    x = pcbnew.ToMM(pad.GetPosition().x)
    y = pcbnew.ToMM(pad.GetPosition().y)
    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
        npth += 1
        print("  NPTH  at %8.3f %8.3f  drill %.2f"
              % (x, y, pcbnew.ToMM(pad.GetDrillSize().x)))
        continue
    seen[name] = (round(x, 3), round(y, 3))
    print("  pad %-3s at %8.3f %8.3f  cu %.2f  drill %.2f"
          % (name, x, y, pcbnew.ToMM(pad.GetSize().x),
             pcbnew.ToMM(pad.GetDrillSize().x)))

bad = []
for name, want in EXPECT.items():
    got = seen.get(name)
    if got is None:
        bad.append("%s missing" % name)
    elif abs(got[0] - want[0]) > 0.002 or abs(got[1] - want[1]) > 0.002:
        bad.append("%s at %s, expected %s" % (name, got, want))
extra = set(seen) - set(EXPECT)
if extra:
    bad.append("unexpected pads: %s" % sorted(extra))
if npth != 1:
    bad.append("expected exactly 1 locating boss hole, found %d" % npth)

# pad-to-pad clearance: nothing may overlap
names = sorted(seen)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        (ax, ay), (bx, by) = seen[names[i]], seen[names[j]]
        d = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
        if d < 1.8 + 0.2:
            bad.append("pads %s and %s only %.3f mm apart (copper 1.8)"
                       % (names[i], names[j], d))

box = fp.GetBoundingBox()
print("bounding box %.2f x %.2f mm"
      % (pcbnew.ToMM(box.GetWidth()), pcbnew.ToMM(box.GetHeight())))

if bad:
    print("\nFAIL")
    for b in bad:
        print("  -", b)
    raise SystemExit(1)
print("\nOK: 10 pads + 1 locating boss, all positions match the LCSC library")
