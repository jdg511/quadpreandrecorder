"""List the connected clusters of one net (pads, tracks, vias with layer/pos).
usage: net_clusters.py NET"""
import sys
from pathlib import Path
import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

NET = sys.argv[1]
board = pcbnew.LoadBoard(str(sp.BOARD_PATH))
mm = lambda v: v / 1e6
conn = board.GetConnectivity()
net = board.FindNet(NET)
code = net.GetNetCode()
items = []
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetNetCode() == code:
            items.append(p)
for t in board.Tracks():
    if t.GetNetCode() == code:
        items.append(t)
seen = set()
clusters = []
types = [pcbnew.PCB_PAD_T, pcbnew.PCB_TRACE_T, pcbnew.PCB_VIA_T, pcbnew.PCB_ARC_T]
for it in items:
    u = it.m_Uuid.AsString()
    if u in seen:
        continue
    group = conn.GetConnectedItems(it)
    members = [it] + [g for g in group]
    ids = set()
    rows = []
    for m in members:
        mu = m.m_Uuid.AsString()
        if mu in ids:
            continue
        ids.add(mu)
        seen.add(mu)
        if m.Type() == pcbnew.PCB_PAD_T:
            fp = m.GetParentFootprint()
            rows.append("pad %s.%s %s (%.2f,%.2f)" % (fp.GetReference(), m.GetNumber(),
                        board.GetLayerName(sp.pad_layers(m)[0]), mm(m.GetPosition().x), mm(m.GetPosition().y)))
        elif m.Type() == pcbnew.PCB_VIA_T:
            rows.append("via (%.2f,%.2f)" % (mm(m.GetPosition().x), mm(m.GetPosition().y)))
        else:
            rows.append("seg %s (%.2f,%.2f)-(%.2f,%.2f)" % (board.GetLayerName(m.GetLayer()),
                        mm(m.GetStart().x), mm(m.GetStart().y), mm(m.GetEnd().x), mm(m.GetEnd().y)))
    clusters.append(rows)
clusters.sort(key=len)
print("%s: %d clusters" % (NET, len(clusters)))
for i, rows in enumerate(clusters):
    print("--- cluster %d: %d items" % (i, len(rows)))
    for r in rows[:80]:
        print("   " + r)
    if len(rows) > 80:
        print("   ... %d more" % (len(rows) - 80))
