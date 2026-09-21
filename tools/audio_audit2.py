"""Refined pass: stackup, parallel-run crosstalk, EP vias, exact pin coords."""
import math, pcbnew

board = pcbnew.LoadBoard("hardware/QuadPreRecorder.kicad_pcb")
def mm(v): return v/1e6

# ------------------------------------------------------------- stackup
print("=" * 74)
print("STACKUP")
print("=" * 74)
try:
    st = board.GetDesignSettings().GetStackupDescriptor()
    for it in st.GetList():
        try:
            nm = it.GetLayerName()
        except Exception:
            nm = ""
        try:
            th = mm(it.GetThickness())
        except Exception:
            th = -1
        print("  %-22s %-16s %.4f mm" % (it.GetTypeName(), nm, th))
except Exception as e:
    print("  (stackup query failed: %s)" % e)

# ------------------------------------------------------------- sides
side = {}
for fp in board.Footprints():
    side[fp.GetReference()] = "BOTTOM" if fp.IsFlipped() else "TOP"

# ------------------------------------------------------- exact pad coords
print("")
print("=" * 74)
print("EXACT PAD COORDINATES - audio ICs (mm)")
print("=" * 74)
want = {
    "U7": ["7","8","11","12","13","14","25","26"],
    "U9": ["1","3","8","9","10","11","12","16","18","19","20"],
    "U10": ["3","9","10","12","13","19","20","21"],
}
padpos = {}
for fp in board.Footprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        c = p.GetCenter()
        padpos[(ref, p.GetNumber())] = (mm(c.x), mm(c.y), p.GetNetname())
for ref in ("U7","U9","U10"):
    fp = board.FindFootprintByReference(ref)
    print("")
    print("%s  side=%s  origin=(%.2f, %.2f)  rot=%.0f" % (
        ref, side[ref], mm(fp.GetPosition().x), mm(fp.GetPosition().y),
        fp.GetOrientationDegrees()))
    for pn in want[ref]:
        if (ref, pn) in padpos:
            x, y, net = padpos[(ref, pn)]
            print("   pin %-3s  (%7.3f, %7.3f)  %s" % (pn, x, y, net))

# ------------------------------------------------------- U10 exposed pad
print("")
print("=" * 74)
print("U10 EXPOSED PAD (pin 21) - vias inside it?")
print("=" * 74)
fp = board.FindFootprintByReference("U10")
ep = None
for p in fp.Pads():
    if p.GetNumber() == "21":
        ep = p
if ep is None:
    print("  no pin 21 found")
else:
    c = ep.GetCenter(); sz = ep.GetSize()
    ex, ey, ew, eh = mm(c.x), mm(c.y), mm(sz.x), mm(sz.y)
    print("  EP centre (%.3f, %.3f)  size %.2f x %.2f mm" % (ex, ey, ew, eh))
    n = 0
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T: continue
        p = t.GetPosition(); vx, vy = mm(p.x), mm(p.y)
        if abs(vx-ex) <= ew/2 and abs(vy-ey) <= eh/2:
            n += 1
            print("    via inside EP at (%.3f, %.3f) net=%s" % (vx, vy, t.GetNetname()))
    print("  vias inside the exposed pad: %d" % n)
    print("  TI datasheet asks for a via array in this pad (it is the amp's")
    print("  ground return AND its only heat path).")

# ------------------------------------------------ parallel-run crosstalk
print("")
print("=" * 74)
print("CROSSTALK - PARALLEL RUNS ONLY (crossings at an angle are benign)")
print("=" * 74)
tracks = []
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T: continue
    s, e = t.GetStart(), t.GetEnd()
    tracks.append((t.GetNetname(), board.GetLayerName(t.GetLayer()),
                   (mm(s.x), mm(s.y)), (mm(e.x), mm(e.y)), mm(t.GetWidth())))

CLOCK = ["ADC_MCLK","ADC_MCLK_IC","ADC_BCLK","ADC_BCLK_IC","ADC_LRCLK",
         "ADC_LRCLK_IC","ADC_TDM","ADC_TDM_IC","ADC_DOUT2","ADC_DOUT2_IC",
         "DAC_BCLK","DAC_BCLK_IC","DAC_LRCLK","DAC_LRCLK_IC","DAC_DIN",
         "DAC_DIN_IC","SPI_SCK","SPI_MOSI","SPI_MISO","I2C_SCL","I2C_SDA"]
ANALOG = []
for ch in ("FLU","FRD","BLD","BRU"):
    for st_ in ("RAW","AC","PAD","PRE","ADC"):
        ANALOG.append("%s_%s" % (ch, st_))
ANALOG += ["ADC_MICBIAS","ADC_VREF","VREF","VREF_NR","+9V_MIC","DAC_L","DAC_R",
           "LINE_L","LINE_R","LINE_JACK_L","LINE_JACK_R","HP_IN_L","HP_IN_R",
           "HP_INP_L","HP_INP_R","HP_OUT_L","HP_OUT_R","HP_JACK_L","HP_JACK_R"]

def ang(a, b):
    return math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180.0

def par_overlap(a, b, c, d):
    """Overlap length and mean perpendicular gap of two near-parallel segs."""
    ux, uy = b[0]-a[0], b[1]-a[1]
    L = math.hypot(ux, uy)
    if L < 1e-9: return 0.0, 1e9
    ux, uy = ux/L, uy/L
    t1 = (c[0]-a[0])*ux + (c[1]-a[1])*uy
    t2 = (d[0]-a[0])*ux + (d[1]-a[1])*uy
    lo, hi = max(0.0, min(t1, t2)), min(L, max(t1, t2))
    if hi <= lo: return 0.0, 1e9
    n1 = abs(-(c[0]-a[0])*uy + (c[1]-a[1])*ux)
    n2 = abs(-(d[0]-a[0])*uy + (d[1]-a[1])*ux)
    return hi - lo, (n1 + n2) / 2.0

def mode(la, lb):
    if la == lb: return "same-layer"
    if tuple(sorted((la, lb))) == ("B.Cu", "In2.Cu"): return "broadside"
    return None

clk = [t for t in tracks if t[0] in CLOCK]
ana = [t for t in tracks if t[0] in ANALOG]

# accumulate coupled length per (clock,analog,mode) bucketed by gap
agg = {}
for cn, cl, ca, cb, cw in clk:
    for an, al, aa, ab, aw in ana:
        m = mode(cl, al)
        if m is None: continue
        da = abs(ang(ca, cb) - ang(aa, ab))
        da = min(da, 180.0 - da)
        if da > 25.0:          # not parallel -> a crossing, benign
            continue
        ov, gap = par_overlap(ca, cb, aa, ab)
        if ov < 0.5: continue
        gap = gap - (cw + aw) / 2.0
        if m == "broadside":
            gap = 0.0          # directly stacked: separation is the dielectric
        if gap > 1.0 and m == "same-layer": continue
        k = (cn, an, m)
        cur = agg.get(k, [0.0, 9e9])
        cur[0] += ov
        cur[1] = min(cur[1], gap)
        agg[k] = cur

rows = sorted(agg.items(), key=lambda kv: -kv[1][0])
print("")
print("  %-9s %-7s %-14s %-14s %s" % ("par_mm", "gap_mm", "clock net", "analog net", "mode"))
for (cn, an, m), (ov, gap) in rows[:40]:
    print("  %-9.2f %-7.3f %-14s %-14s %s" % (ov, gap, cn, an, m))
print("")
print("  %d parallel clock/analog pairs total" % len(rows))
tot_b = sum(v[0] for k, v in agg.items() if k[2] == "broadside")
tot_s = sum(v[0] for k, v in agg.items() if k[2] == "same-layer")
print("  total parallel length, broadside In2/B : %.1f mm" % tot_b)
print("  total parallel length, same layer      : %.1f mm" % tot_s)
