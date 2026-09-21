"""Report courtyard overlaps and near-misses for the parts we just moved.

Reads review_outputs/placement.json (from dump_placement.py). Same-side
bounding boxes only - a top-side part and a bottom-side part can share
footprint without touching.
"""
import json

WATCH = ["SW4", "R96", "R97", "C93", "C94"]
NEAR = 1.0          # mm; report anything closer than this as a near miss

data = json.load(open("review_outputs/placement.json"))
by_ref = {d["ref"]: d for d in data}

missing = [r for r in WATCH if r not in by_ref]
if missing:
    print("NOT ON THE BOARD:", missing)

def gap(a, b):
    """Separation between two bboxes; negative means they overlap."""
    dx = max(a["x0"] - b["x1"], b["x0"] - a["x1"])
    dy = max(a["y0"] - b["y1"], b["y0"] - a["y1"])
    if dx >= 0 or dy >= 0:
        return max(dx, dy)
    return max(dx, dy)          # both negative -> overlap depth

for ref in WATCH:
    a = by_ref.get(ref)
    if not a:
        continue
    print("\n%s  side %s  x %.2f..%.2f  y %.2f..%.2f  (%.1f x %.1f mm)"
          % (ref, a["side"], a["x0"], a["x1"], a["y0"], a["y1"],
             a["x1"] - a["x0"], a["y1"] - a["y0"]))
    hits = []
    for b in data:
        if b["ref"] == ref or b["side"] != a["side"]:
            continue
        g = gap(a, b)
        if g < NEAR:
            hits.append((g, b))
    for g, b in sorted(hits):
        tag = "OVERLAP" if g < 0 else "close  "
        print("   %s %-6s %-22s gap %+7.2f mm  x %.2f..%.2f y %.2f..%.2f"
              % (tag, b["ref"], b["val"][:22], g, b["x0"], b["x1"],
                 b["y0"], b["y1"]))
    if not hits:
        print("   clear: nothing within %.1f mm on the same side" % NEAR)

# board frame + the module keep-out zone
a = by_ref.get("SW4")
if a:
    print("\nSW4 vs the frame (board 138 x 114):")
    print("   left  edge gap %+7.2f mm" % (a["x0"] - 0.0))
    print("   right edge gap %+7.2f mm" % (138.0 - a["x1"]))
    print("   rear  edge gap %+7.2f mm" % (a["y0"] - 0.0))
    print("   front edge gap %+7.2f mm" % (114.0 - a["y1"]))
    print("   TFT module zone ends at y=64.34; SW4 starts at y=%.2f "
          "-> %+.2f mm" % (a["y0"], a["y0"] - 64.34))
