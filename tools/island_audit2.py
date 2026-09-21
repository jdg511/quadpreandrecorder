"""Per-layer GND fill census, then find which polygons form isolated clusters.

Every filled polygon has at least one anchor (island_audit.py), so the 10
remaining unconnected items must be polygons that are anchored only to each
other. Build the graph - polygons as nodes, shared vias/pads/tracks as edges -
and report any component that does not contain the main plane.
"""
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(PCB)
gndcode = board.FindNet("GND").GetNetCode()

polys = []       # (layername, layer, SHAPE_POLY_SET, area_mm2)
for zone in board.Zones():
    if zone.GetIsRuleArea() or zone.GetNetCode() != gndcode:
        continue
    for layer in zone.GetLayerSet().Seq():
        try:
            pl = zone.GetFilledPolysList(layer)
        except Exception:
            continue
        for i in range(pl.OutlineCount()):
            sp = pcbnew.SHAPE_POLY_SET()
            sp.AddOutline(pl.Outline(i))
            polys.append([board.GetLayerName(layer), layer, sp,
                          pcbnew.ToMM(pcbnew.ToMM(sp.Area()))])

count = {}
area = {}
for name, _layer, _sp, a in polys:
    count[name] = count.get(name, 0) + 1
    area[name] = area.get(name, 0.0) + a
print("GND fill by layer:")
for name in sorted(count):
    print("   %-8s %3d polygons, %9.1f mm2" % (name, count[name], area[name]))

# connectors: anything that can bridge two polygons
conns = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == gndcode:
            conns.append(("pad %s.%s" % (fp.GetReference(), p.GetNumber()),
                          p.GetPosition(), p.GetLayerSet().Seq()))
for t in board.GetTracks():
    if t.GetNetCode() != gndcode:
        continue
    if isinstance(t, pcbnew.PCB_VIA):
        conns.append(("via", t.GetPosition(), t.GetLayerSet().Seq()))
    else:
        lay = [t.GetLayer()]
        conns.append(("trk", t.GetStart(), lay))
        conns.append(("trk", t.GetEnd(), lay))

parent = list(range(len(polys)))

def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i

def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

for label, pos, layers in conns:
    touching = []
    for idx, (_name, layer, sp, _a) in enumerate(polys):
        if layer in layers and sp.Collide(pos):
            touching.append(idx)
    for k in range(1, len(touching)):
        union(touching[0], touching[k])

groups = {}
for idx in range(len(polys)):
    groups.setdefault(find(idx), []).append(idx)

ordered = sorted(groups.values(), key=lambda g: -sum(polys[i][3] for i in g))
print("\nconnected clusters of GND fill: %d" % len(ordered))
for n, g in enumerate(ordered):
    tot = sum(polys[i][3] for i in g)
    tag = "MAIN" if n == 0 else "ISOLATED"
    print("   %-9s %2d polygons, %9.2f mm2" % (tag, len(g), tot))
    if n > 0:
        for i in g:
            name, layer, sp, a = polys[i]
            bb = sp.BBox()
            anchors = []
            for label, pos, layers in conns:
                if layer in layers and sp.Collide(pos):
                    anchors.append(label)
            uniq = sorted(set(anchors))
            print("        %-7s centre (%7.2f, %7.2f)  %5.2f x %5.2f mm  %.3f mm2"
                  % (name,
                     pcbnew.ToMM(bb.GetX()) + pcbnew.ToMM(bb.GetWidth()) / 2,
                     pcbnew.ToMM(bb.GetY()) + pcbnew.ToMM(bb.GetHeight()) / 2,
                     pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), a))
            print("                 anchored by: %s"
                  % (", ".join(uniq) if uniq else "NOTHING"))
