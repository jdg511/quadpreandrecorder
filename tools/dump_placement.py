"""Dump footprint reference, value, side, anchor and courtyard bbox as JSON."""
import json, math, re, sys

PCB = sys.argv[1] if len(sys.argv) > 1 else 'hardware/QuadPreRecorder.kicad_pcb'
src = open(PCB, encoding='utf-8').read()


def blocks(text, token):
    """Yield (start, end) for every top-level s-expression starting with token."""
    i = 0
    while True:
        i = text.find(token, i)
        if i < 0:
            return
        depth = 0
        j = i
        while j < len(text):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield i, j + 1
        i = j + 1


def rot(x, y, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return (x * ca + y * sa, -x * sa + y * ca)


out = []
for s, e in blocks(src, '(footprint '):
    fp = src[s:e]
    m = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)', fp)
    if not m:
        continue
    ax, ay = float(m.group(1)), float(m.group(2))
    ang = float(m.group(3)) if m.group(3) else 0.0
    ref = re.search(r'\(property "Reference" "([^"]*)"', fp)
    val = re.search(r'\(property "Value" "([^"]*)"', fp)
    lay = re.search(r'\(layer "([^"]*)"\)', fp)
    pts = []
    for layname in ('CrtYd', 'Fab'):
        for tok in ('(fp_line', '(fp_rect', '(fp_circle', '(fp_poly'):
            for gs, ge in blocks(fp, tok):
                g = fp[gs:ge]
                if layname not in g:
                    continue
                for gm in re.finditer(r'\((?:start|end|center|xy)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', g):
                    pts.append((float(gm.group(1)), float(gm.group(2))))
        if pts:
            break
    if not pts:
        continue
    xs, ys = [], []
    for px, py in pts:
        rx, ry = rot(px, py, ang)
        xs.append(ax + rx)
        ys.append(ay + ry)
    out.append({
        'ref': ref.group(1) if ref else '?',
        'val': val.group(1) if val else '',
        'side': 'B' if (lay and lay.group(1).startswith('B')) else 'F',
        'x': round(ax, 2), 'y': round(ay, 2), 'rot': ang,
        'x0': round(min(xs), 2), 'x1': round(max(xs), 2),
        'y0': round(min(ys), 2), 'y1': round(max(ys), 2),
    })

json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else 'review_outputs/placement.json', 'w'), indent=0)
print('dumped', len(out))
