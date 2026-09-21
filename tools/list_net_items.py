"""python3 tools/list_net_items.py NET [x0 y0 x1 y1]  (plain-text scan, no pcbnew)"""
import re, sys
s=open('hardware/QuadPreRecorder.kicad_pcb').read()
name=sys.argv[1]; box=list(map(float,sys.argv[2:6])) if len(sys.argv)>5 else None
def inb(x,y): return box is None or (box[0]<=x<=box[2] and box[1]<=y<=box[3])
for m in re.finditer(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*\(width ([\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net "([^"]+)"\)',s):
    a,b,c,d,w,l,n=m.groups()
    if n==name and (inb(float(a),float(b)) or inb(float(c),float(d))): print("seg %-5s %8s %8s -> %8s %8s w%s"%(l,a,b,c,d,w))
for m in re.finditer(r'\(via\s*(?:\(locked yes\)\s*)?\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([\d.]+)\)\s*\(drill ([\d.]+)\)\s*\(layers "([^"]+)" "([^"]+)"\)[^)]*?\(net "([^"]+)"\)',s):
    x,y,sz,dr,l1,l2,n=m.groups()
    if n==name and inb(float(x),float(y)): print("via %s %s size %s"%(x,y,sz))
