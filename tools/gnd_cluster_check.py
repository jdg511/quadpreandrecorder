"""Ask KiCad's own connectivity engine whether every GND pad really reaches ground.

The hand-rolled island analysis can undercount (a track bridging two islands
looks like two separate anchors), so this defers to CONNECTIVITY_DATA, which
is the same engine DRC uses. Any GND pad that is not in the same cluster as
the bulk of the net is a genuinely floating ground pin.
"""
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.BuildConnectivity()
conn = board.GetConnectivity()

gndcode = board.FindNet("GND").GetNetCode()

pads = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == gndcode:
            pads.append((fp.GetReference() + "." + p.GetNumber(), p))
print("GND pads: %d" % len(pads))

TYPES = 0   # 0 = every connected-item type

parent = {}

def find(k):
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k

def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

for name, _p in pads:
    parent[name] = name

# SWIG hands back a fresh Python proxy each call, so id() is useless as an
# identity: key on the board item's own UUID instead.
index = {}
for name, p in pads:
    index[p.m_Uuid.AsString()] = name

for name, p in pads:
    for item in conn.GetConnectedItems(p, TYPES):
        other = index.get(item.m_Uuid.AsString())
        if other is not None:
            union(name, other)

groups = {}
for name, _p in pads:
    groups.setdefault(find(name), []).append(name)

ordered = sorted(groups.values(), key=len, reverse=True)
print("GND pad clusters: %d" % len(ordered))
for n, g in enumerate(ordered):
    if n == 0:
        print("   MAIN     %d pads" % len(g))
    else:
        print("   ORPHAN   %d pads: %s" % (len(g), ", ".join(sorted(g))))

print("\nKiCad unconnected count on the whole board: %d"
      % conn.GetUnconnectedCount(True))
