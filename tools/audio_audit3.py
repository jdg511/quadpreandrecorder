"""Layer budget + geographic partition check."""
import math, pcbnew
board = pcbnew.LoadBoard("hardware/QuadPreRecorder.kicad_pcb")
def mm(v): return v/1e6

per_layer = {}
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T: continue
    s, e = t.GetStart(), t.GetEnd()
    L = math.hypot(mm(e.x-s.x), mm(e.y-s.y))
    ln = board.GetLayerName(t.GetLayer())
    per_layer[ln] = per_layer.get(ln, 0.0) + L

print("=" * 70)
print("TRACK LENGTH PER LAYER")
print("=" * 70)
tot = sum(per_layer.values())
for ln in sorted(per_layer, key=lambda k: -per_layer[k]):
    print("  %-9s %9.1f mm   %5.1f%%" % (ln, per_layer[ln], 100*per_layer[ln]/tot))
print("  %-9s %9.1f mm" % ("TOTAL", tot))

nvia = sum(1 for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T)
print("  vias: %d" % nvia)

print("")
print("=" * 70)
print("WHERE THINGS ARE (mm)")
print("=" * 70)
for ref in ("U6","U4","U5","U7","U8","U9","U10","J1","J2","J3","U14"):
    fp = board.FindFootprintByReference(ref)
    if fp is None: continue
    p = fp.GetPosition()
    print("  %-5s (%6.1f, %6.1f)  %s  %s" % (
        ref, mm(p.x), mm(p.y),
        "BOT" if fp.IsFlipped() else "TOP", fp.GetValue()[:34]))

ANALOG = []
for ch in ("FLU","FRD","BLD","BRU"):
    for st in ("RAW","AC","PAD","PRE","ADC","ATT","MIC","FB","ADC_SRC"):
        ANALOG.append("%s_%s" % (ch, st))
CLOCK = ["ADC_MCLK","ADC_MCLK_IC","ADC_BCLK","ADC_BCLK_IC","ADC_LRCLK",
         "ADC_LRCLK_IC","ADC_TDM","ADC_TDM_IC","ADC_DOUT2","ADC_DOUT2_IC",
         "DAC_BCLK","DAC_BCLK_IC","DAC_LRCLK","DAC_LRCLK_IC","DAC_DIN",
         "DAC_DIN_IC","SPI_SCK","SPI_MOSI","SPI_MISO","I2C_SCL","I2C_SDA"]

def bbox_and_len(nets):
    x0=y0=1e9; x1=y1=-1e9; L=0.0
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T: continue
        if t.GetNetname() not in nets: continue
        s, e = t.GetStart(), t.GetEnd()
        for p in (s, e):
            x0=min(x0,mm(p.x)); x1=max(x1,mm(p.x))
            y0=min(y0,mm(p.y)); y1=max(y1,mm(p.y))
        L += math.hypot(mm(e.x-s.x), mm(e.y-s.y))
    return (x0,y0,x1,y1,L)

print("")
print("=" * 70)
print("COPPER FOOTPRINT OF EACH GROUP")
print("=" * 70)
for nm, nets in (("ANALOG", set(ANALOG)), ("CLOCK/DATA", set(CLOCK))):
    x0,y0,x1,y1,L = bbox_and_len(nets)
    print("  %-11s x %6.1f..%6.1f   y %6.1f..%6.1f   total %7.1f mm" % (nm,x0,x1,y0,y1,L))

# per-net longest offenders
print("")
print("  longest individual clock nets:")
lens = {}
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T: continue
    n = t.GetNetname()
    if n not in CLOCK: continue
    s, e = t.GetStart(), t.GetEnd()
    lens[n] = lens.get(n, 0.0) + math.hypot(mm(e.x-s.x), mm(e.y-s.y))
for n in sorted(lens, key=lambda k:-lens[k])[:10]:
    print("    %-14s %6.1f mm" % (n, lens[n]))

print("")
print("  longest individual analog nets:")
lens = {}
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T: continue
    n = t.GetNetname()
    if n not in ANALOG: continue
    s, e = t.GetStart(), t.GetEnd()
    lens[n] = lens.get(n, 0.0) + math.hypot(mm(e.x-s.x), mm(e.y-s.y))
for n in sorted(lens, key=lambda k:-lens[k])[:10]:
    print("    %-14s %6.1f mm" % (n, lens[n]))

b = board.GetBoardEdgesBoundingBox()
print("")
print("  board outline: %.1f x %.1f mm" % (mm(b.GetWidth()), mm(b.GetHeight())))
