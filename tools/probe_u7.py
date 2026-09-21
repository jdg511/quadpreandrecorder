"""What surrounds U7.23, and where is the nearest I2C_SDA copper?"""
import math
import pcbnew

board = pcbnew.LoadBoard("hardware/QuadPreRecorder.kicad_pcb")
code = board.FindNet("I2C_SDA").GetNetCode()

pad = None
for fp in board.Footprints():
    for p in fp.Pads():
        if fp.GetReference() == "U7" and p.GetNumber() == "23":
            pad, parent = p, fp
pos = pad.GetPosition()
px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
bb = pad.GetBoundingBox()
print("U7.23 at (%.3f, %.3f), pad %.2f x %.2f, layer %s, U7 rot %.0f flipped %s"
      % (px, py, pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()),
         board.GetLayerName(pad.GetLayer()),
         parent.GetOrientationDegrees(), parent.IsFlipped()))

print("\nnearest I2C_SDA copper:")
near = []
for t in board.GetTracks():
    if t.GetNetCode() != code:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        near.append((math.hypot(pcbnew.ToMM(p.x) - px, pcbnew.ToMM(p.y) - py),
                     "via at (%.2f, %.2f)" % (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))))
    else:
        for end, p in (("start", t.GetStart()), ("end", t.GetEnd())):
            near.append((math.hypot(pcbnew.ToMM(p.x) - px,
                                    pcbnew.ToMM(p.y) - py),
                         "track %s (%.2f, %.2f) on %s"
                         % (end, pcbnew.ToMM(p.x), pcbnew.ToMM(p.y),
                            board.GetLayerName(t.GetLayer()))))
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == code and p.m_Uuid.AsString() != pad.m_Uuid.AsString():
            q = p.GetPosition()
            near.append((math.hypot(pcbnew.ToMM(q.x) - px,
                                    pcbnew.ToMM(q.y) - py),
                         "pad %s.%s (%.2f, %.2f)"
                         % (fp.GetReference(), p.GetNumber(),
                            pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))))
near.sort()
for d, what in near[:8]:
    print("   %6.2f mm  %s" % (d, what))

print("\neverything within 2.5 mm of the pad:")
around = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.m_Uuid.AsString() == pad.m_Uuid.AsString():
            continue
        q = p.GetPosition()
        d = math.hypot(pcbnew.ToMM(q.x) - px, pcbnew.ToMM(q.y) - py)
        if d <= 2.5:
            around.append((d, "pad %s.%s [%s] on %s"
                           % (fp.GetReference(), p.GetNumber(),
                              p.GetNetname() or "-",
                              board.GetLayerName(p.GetLayer()))))
for t in board.GetTracks():
    q = t.GetPosition()
    d = math.hypot(pcbnew.ToMM(q.x) - px, pcbnew.ToMM(q.y) - py)
    if d <= 2.5:
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "trk"
        around.append((d, "%s [%s] on %s" % (kind, t.GetNetname() or "-",
                                             board.GetLayerName(t.GetLayer()))))
around.sort()
for d, what in around[:20]:
    print("   %6.2f mm  %s" % (d, what))
