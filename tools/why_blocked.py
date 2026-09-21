"""For each still-stranded GND pad, show what is crowding it.

Lists every copper object within a few mm, so it is obvious whether the pad is
0.05 mm short of a legal via spot or genuinely walled in.
"""
import math
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
TARGETS = ["U6.11", "U4.9", "C38.2", "C41.2", "C43.2"]
RADIUS = 3.0

board = pcbnew.LoadBoard(PCB)

wanted = {}
for fp in board.Footprints():
    for p in fp.Pads():
        key = fp.GetReference() + "." + p.GetNumber()
        if key in TARGETS:
            wanted[key] = (fp, p)

for key in TARGETS:
    fp, pad = wanted[key]
    pos = pad.GetPosition()
    px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
    side = "B" if fp.IsFlipped() else "F"
    bb = pad.GetBoundingBox()
    print("\n=== %s  (%s, %s) at (%.2f, %.2f), side %s, pad %.2f x %.2f mm"
          % (key, fp.GetReference(), fp.GetValue()[:18], px, py, side,
             pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())))
    print("    pad layers: %s"
          % ", ".join(board.GetLayerName(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu)
                      if pad.IsOnLayer(l)))

    near = []
    for ofp in board.Footprints():
        for op in ofp.Pads():
            if op.m_Uuid.AsString() == pad.m_Uuid.AsString():
                continue
            opos = op.GetPosition()
            d = math.hypot(pcbnew.ToMM(opos.x) - px, pcbnew.ToMM(opos.y) - py)
            if d <= RADIUS:
                obb = op.GetBoundingBox()
                near.append((d, "pad  %s.%s [%s] %.2fx%.2f"
                             % (ofp.GetReference(), op.GetNumber(),
                                op.GetNetname() or "-",
                                pcbnew.ToMM(obb.GetWidth()),
                                pcbnew.ToMM(obb.GetHeight()))))
    for t in board.GetTracks():
        tpos = t.GetPosition()
        d = math.hypot(pcbnew.ToMM(tpos.x) - px, pcbnew.ToMM(tpos.y) - py)
        if d > RADIUS:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            try:
                w = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            except Exception:
                w = pcbnew.ToMM(t.GetWidth())
            near.append((d, "via  [%s] dia %.2f" % (t.GetNetname() or "-", w)))
        else:
            near.append((d, "trk  [%s] on %s w %.2f"
                         % (t.GetNetname() or "-",
                            board.GetLayerName(t.GetLayer()),
                            pcbnew.ToMM(t.GetWidth()))))
    near.sort()
    for d, what in near[:14]:
        print("    %5.2f mm  %s" % (d, what))
    if not near:
        print("    nothing within %.1f mm - the pad is NOT crowded" % RADIUS)
