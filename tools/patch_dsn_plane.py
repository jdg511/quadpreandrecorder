"""Make In1.Cu AND In2.Cu (Rev C3) Specctra PLANE layers instead of signal layers + full-layer keepouts.

Handing Freerouting a wire_keepout covering an entire routing layer makes it
repeatedly consider and reject that layer. The correct Specctra idiom for a
reference plane is (type power), which Freerouting excludes from routing
outright while still letting vias pass. KiCad's exporter always writes
(type signal) for every copper layer, so we post-process.

The KiCad rule area stays in the board file: it documents the intent and stops
anyone hand-routing on the plane later. It just should not reach the router.
"""
import re
import sys

src = sys.argv[1] if len(sys.argv) > 1 else 'hardware/review_outputs/QuadPreRecorder-unrouted.dsn'
dst = sys.argv[2] if len(sys.argv) > 2 else 'hardware/review_outputs/QuadPreRecorder-unrouted-plane.dsn'

s = open(src, encoding='utf-8', errors='replace').read()
before = len(s)

# 1) In1.Cu and In2.Cu become plane layers (Rev C3: SIG/GND/GND/SIG)
s, n_layer = re.subn(r'(\(layer\s+In[12]\.Cu\s*\(type\s+)signal(\))', r'\1power\2', s)

# 2) drop any wire_keepout that lives on In1.Cu / In2.Cu (balanced-paren removal)
removed = 0
while True:
    m = re.search(r'\(wire_keepout\s+""\s+\(polygon\s+In[12]\.Cu\b', s)
    if not m:
        break
    i = m.start()
    depth = 0
    j = i
    while j < len(s):
        if s[j] == '(':
            depth += 1
        elif s[j] == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    s = s[:i] + s[j + 1:]
    removed += 1

open(dst, 'w', encoding='utf-8').write(s)
print(f'layer decls changed to power : {n_layer}')
print(f'In1/In2 wire_keepouts removed: {removed}')
print(f'bytes {before} -> {len(s)}')
print(dst)
