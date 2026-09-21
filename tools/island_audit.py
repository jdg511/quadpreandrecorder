"""Find every filled GND-zone polygon and say what, if anything, ties it in.

DRC says 10 zone-to-zone connections are missing but never gives the island's
real coordinates (it prints the zone outline's origin instead), so locate them
directly: walk each zone's filled polygons and count the GND pads, vias and
tracks that actually land inside each one.

A polygon with 0 anchors is floating copper. A polygon whose only anchors are
vias may still be isolated if those vias only reach other floating polygons.
"""
import pcbnew
from pathlib import Path

PCB = "hardware/QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(PCB)

gnd = board.FindNet("GND")
gndcode = gnd.GetNetCode()

# every GND anchor point, by layer
pads, vias, tracks = [], [], []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == gndcode:
            pads.append((p.GetPosition(), p, fp.GetReference()))
for t in board.GetTracks():
    if t.GetNetCode() != gndcode:
        continue
    if isinstance(t, pcbnew.PCB_VIA):
        vias.append(t)
    else:
        tracks.append(t)

print("GND anchors: %d pads, %d vias, %d track segments"
      % (len(pads), len(vias), len(tracks)))

total_islands = 0
floating = []
for zone in board.Zones():
    if zone.GetIsRuleArea() or zone.GetNetCode() != gndcode:
        continue
    for layer in zone.GetLayerSet().Seq():
        try:
            poly = zone.GetFilledPolysList(layer)
        except Exception:
            continue
        n = poly.OutlineCount()
        for i in range(n):
            total_islands += 1
            shape = pcbnew.SHAPE_POLY_SET()
            shape.AddOutline(poly.Outline(i))
            bb = shape.BBox()
            area_mm2 = (pcbnew.ToMM(bb.GetWidth()) *
                        pcbnew.ToMM(bb.GetHeight()))
            anchors = 0
            who = []
            for pos, p, ref in pads:
                if p.IsOnLayer(layer) and shape.Collide(pos):
                    anchors += 1
                    if len(who) < 3:
                        who.append("pad %s.%s" % (ref, p.GetNumber()))
            for v in vias:
                if v.IsOnLayer(layer) and shape.Collide(v.GetPosition()):
                    anchors += 1
                    if len(who) < 3:
                        who.append("via")
            for t in tracks:
                if t.IsOnLayer(layer) and (shape.Collide(t.GetStart()) or
                                           shape.Collide(t.GetEnd())):
                    anchors += 1
                    if len(who) < 3:
                        who.append("track")
            if anchors == 0:
                floating.append((
                    board.GetLayerName(layer),
                    round(pcbnew.ToMM(bb.GetX()) + pcbnew.ToMM(bb.GetWidth()) / 2, 2),
                    round(pcbnew.ToMM(bb.GetY()) + pcbnew.ToMM(bb.GetHeight()) / 2, 2),
                    round(pcbnew.ToMM(bb.GetWidth()), 2),
                    round(pcbnew.ToMM(bb.GetHeight()), 2),
                    round(area_mm2, 3),
                ))

print("filled GND polygons: %d" % total_islands)
print("with NO pad/via/track anchor (true floating copper): %d" % len(floating))
for lay, cx, cy, w, h, a in sorted(floating, key=lambda r: -r[5]):
    print("   %-7s centre (%7.2f, %7.2f)  %5.2f x %5.2f mm  bbox %.3f mm2"
          % (lay, cx, cy, w, h, a))
