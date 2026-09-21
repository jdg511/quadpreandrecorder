"""Where does a horizontal THT LED's body sit relative to its pads?

Needed to place D4/D5 so the lens reaches the front wall's outer face, which
is 3.60 mm past the board edge.
"""
import pcbnew

LIB = r"C:\Program Files\KiCad\10.0\share\kicad\footprints\LED_THT.pretty"
NAMES = [
    "LED_D3.0mm_Horizontal_O1.27mm_Z6.0mm",
    "LED_D3.0mm_Horizontal_O1.27mm_Z2.0mm",
    "LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm",
]


def mm(v):
    return pcbnew.ToMM(v)


for name in NAMES:
    fp = pcbnew.FootprintLoad(LIB, name)
    if fp is None:
        print("%s : not found\n" % name)
        continue
    print("=== %s" % name)
    for pad in fp.Pads():
        p = pad.GetPosition()
        print("    pad %-2s at (%6.2f, %6.2f)  drill %.2f"
              % (pad.GetNumber(), mm(p.x), mm(p.y), mm(pad.GetDrillSizeX())))
    for layername in ("F.Fab", "F.CrtYd", "F.SilkS"):
        lay = fp.GetBoard().GetLayerID(layername) if fp.GetBoard() else None
        xs, ys = [], []
        for item in fp.GraphicalItems():
            if item.GetLayer() != pcbnew.F_Fab and layername == "F.Fab":
                continue
            if item.GetLayer() != pcbnew.F_CrtYd and layername == "F.CrtYd":
                continue
            if item.GetLayer() != pcbnew.F_SilkS and layername == "F.SilkS":
                continue
            if not hasattr(item, "GetStart"):
                continue        # text items carry no start/end
            for p in (item.GetStart(), item.GetEnd()):
                xs.append(mm(p.x))
                ys.append(mm(p.y))
        if xs:
            print("    %-8s x %6.2f..%6.2f   y %6.2f..%6.2f"
                  % (layername, min(xs), max(xs), min(ys), max(ys)))
    print()
