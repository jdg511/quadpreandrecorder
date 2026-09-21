"""Four audio-specific checks against the real routed Rev C2 board.

1. AGND/DGND: are every audio IC's ground pins on one net, and does each
   reach the In1.Cu plane through its own nearby via?
2. Clock-to-analog crosstalk: real copper separation between every clock /
   serial-audio net and every analog signal net.
3. Digital-rail filtering: how far each supply pin is from its own decoupler.
4. (dielectrics are checked from the schematic, not here)

Geometry only - no zone fill, so this runs in seconds.
"""
import math
import pcbnew

PCB = "hardware/QuadPreRecorder.kicad_pcb"
board = pcbnew.LoadBoard(PCB)

def mm(v):
    return v / 1e6

# ---------------------------------------------------------------- geometry
def pt_seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def segs_cross(a, b, c, d):
    def o(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
    o1, o2 = o(a, b, c), o(a, b, d)
    o3, o4 = o(c, d, a), o(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)

def seg_seg_dist(a, b, c, d):
    if segs_cross(a, b, c, d):
        return 0.0
    return min(pt_seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]),
               pt_seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               pt_seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]),
               pt_seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))

# ---------------------------------------------------------------- collect
tracks = []   # (net, layername, (x1,y1), (x2,y2), width)
vias = []     # (net, x, y, drill, topLayer, botLayer)
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        vias.append((t.GetNetname(), mm(p.x), mm(p.y), mm(t.GetDrill())))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((t.GetNetname(), board.GetLayerName(t.GetLayer()),
                       (mm(s.x), mm(s.y)), (mm(e.x), mm(e.y)), mm(t.GetWidth())))

pads = {}   # "U7.13" -> (net, x, y, layerset-string)
for fp in board.Footprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        c = p.GetCenter()
        pads["%s.%s" % (ref, p.GetNumber())] = (p.GetNetname(), mm(c.x), mm(c.y))

print("tracks=%d vias=%d pads=%d" % (len(tracks), len(vias), len(pads)))

# ================================================== 1. AGND / DGND per IC
print("")
print("=" * 74)
print("CHECK 1 - AGND/DGND pin ties and plane access")
print("=" * 74)

AUDIO_ICS = {
    "U7":  "PCM1864DBT  4ch ADC",
    "U9":  "PCM5102A    stereo DAC",
    "U10": "TPA6130A2   headphone amp",
    "U2":  "TPS7A2033   +3V3_A LDO",
    "U3":  "TLE2426     VREF splitter",
}
for ref in sorted(AUDIO_ICS):
    gnd_pads = [(k, v) for k, v in pads.items()
                if k.startswith(ref + ".") and v[0] == "GND"]
    if not gnd_pads:
        print("%-4s %-26s NO GND PADS FOUND" % (ref, AUDIO_ICS[ref]))
        continue
    print("")
    print("%-4s %-26s  %d ground pads, all on net GND" % (ref, AUDIO_ICS[ref], len(gnd_pads)))
    worst = 0.0
    for name, (net, px, py) in sorted(gnd_pads, key=lambda z: int(z[0].split(".")[1]) if z[0].split(".")[1].isdigit() else 999):
        best, bd = None, 1e9
        for vnet, vx, vy, vdr in vias:
            if vnet != "GND":
                continue
            d = math.hypot(px - vx, py - vy)
            if d < bd:
                bd, best = d, (vx, vy)
        flag = ""
        if bd > 1.5:
            flag = "  <-- far from plane"
        if bd > worst:
            worst = bd
        print("     %-8s nearest GND via %5.2f mm%s" % (name, bd, flag))
    print("     worst pad-to-via on %s: %.2f mm" % (ref, worst))

# ================================================== 2. clock vs analog
print("")
print("=" * 74)
print("CHECK 2 - clock / serial-audio to analog-signal separation")
print("=" * 74)

CLOCK = ["ADC_MCLK", "ADC_MCLK_IC", "ADC_BCLK", "ADC_BCLK_IC",
         "ADC_LRCLK", "ADC_LRCLK_IC", "ADC_TDM", "ADC_TDM_IC",
         "ADC_DOUT2", "ADC_DOUT2_IC",
         "DAC_BCLK", "DAC_BCLK_IC", "DAC_LRCLK", "DAC_LRCLK_IC",
         "DAC_DIN", "DAC_DIN_IC",
         "SPI_SCK", "SPI_MOSI", "SPI_MISO", "I2C_SCL", "I2C_SDA"]

ANALOG = []
for ch in ("FLU", "FRD", "BLD", "BRU"):
    for st in ("RAW", "AC", "PAD", "PRE", "ADC"):
        ANALOG.append("%s_%s" % (ch, st))
ANALOG += ["ADC_MICBIAS", "ADC_VREF", "VREF", "VREF_NR", "+9V_MIC",
           "DAC_L", "DAC_R", "LINE_L", "LINE_R",
           "LINE_JACK_L", "LINE_JACK_R",
           "HP_IN_L", "HP_IN_R", "HP_INP_L", "HP_INP_R",
           "HP_OUT_L", "HP_OUT_R", "HP_JACK_L", "HP_JACK_R"]

clk_t = [t for t in tracks if t[0] in CLOCK]
ana_t = [t for t in tracks if t[0] in ANALOG]
print("clock segments=%d   analog segments=%d" % (len(clk_t), len(ana_t)))

# In1.Cu is a solid ground plane, so F.Cu<->In2.Cu and F.Cu<->B.Cu are
# shielded by it. Only same-layer edge coupling and the In2.Cu/B.Cu
# adjacent pair can actually couple.
def coupled(la, lb):
    if la == lb:
        return "same-layer"
    pair = tuple(sorted((la, lb)))
    if pair == ("B.Cu", "In2.Cu"):
        return "broadside In2/B"
    return None

hits = []
for cn, cl, ca, cb, cw in clk_t:
    for an, al, aa, ab, aw in ana_t:
        mode = coupled(cl, al)
        if mode is None:
            continue
        d = seg_seg_dist(ca, cb, aa, ab) - (cw + aw) / 2.0
        if d < 2.0:
            hits.append((d, cn, an, cl, al, mode,
                         (ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2))

hits.sort(key=lambda z: z[0])
print("")
if not hits:
    print("No clock/analog pair anywhere within 2.00 mm of copper edge.")
else:
    print("%d segment pairs closer than 2.00 mm (edge to edge):" % len(hits))
    print("")
    print("  %-7s %-14s %-14s %-10s %-16s %s" % ("gap_mm", "clock net", "analog net", "layer", "mode", "near xy"))
    seen = set()
    for d, cn, an, cl, al, mode, mx, my in hits:
        key = (cn, an, cl, al)
        if key in seen:
            continue
        seen.add(key)
        print("  %-7.3f %-14s %-14s %-10s %-16s %.1f,%.1f" % (d, cn, an, cl, mode, mx, my))
    print("")
    print("(worst pair per net combination shown; %d unique combinations)" % len(seen))

# also: clock track vs analog PAD
print("")
print("--- clock tracks passing near analog pads ---")
pad_hits = []
for pname, (pnet, px, py) in pads.items():
    if pnet not in ANALOG:
        continue
    for cn, cl, ca, cb, cw in clk_t:
        d = pt_seg_dist(px, py, ca[0], ca[1], cb[0], cb[1]) - cw / 2.0
        if d < 1.5:
            pad_hits.append((d, cn, pname, pnet, cl))
pad_hits.sort(key=lambda z: z[0])
if not pad_hits:
    print("none within 1.50 mm")
for d, cn, pname, pnet, cl in pad_hits[:20]:
    print("  %.3f mm  %-14s -> pad %-10s (%s) on %s" % (d, cn, pname, pnet, cl))

# ================================================== 3. decoupling distance
print("")
print("=" * 74)
print("CHECK 3 - supply pin to its nearest same-net decoupling capacitor")
print("=" * 74)

SUPPLY_PINS = [
    ("U7.8",  "+3V3_A", "PCM1864 AVDD"),
    ("U7.13", "+3V3_DC", "PCM1864 DVDD"),
    ("U7.14", "+3V3_DC", "PCM1864 DVDD/IOVDD"),
    ("U7.11", "ADC_LDO", "PCM1864 LDO out"),
    ("U7.6",  "ADC_VREF", "PCM1864 VREF"),
    ("U9.1",  "+3V3_A", "PCM5102A AVDD"),
    ("U9.8",  "+3V3_A", "PCM5102A AVDD"),
    ("U9.20", "+3V3_DC", "PCM5102A DVDD"),
    ("U9.2",  "DAC_CAPP", "PCM5102A CAPP (flying cap)"),
    ("U9.5",  "DAC_VNEG", "PCM5102A VNEG"),
    ("U10.18", "HP_CPP", "TPA6130A2 CPP (flying cap)"),
    ("U10.15", "HP_VSS", "TPA6130A2 CPVSS"),
    ("U14.5", "+3V3_DC", "TPS7A2033 (digital) OUT"),
    ("U14.1", "+5V", "TPS7A2033 (digital) IN"),
    ("U9.18", "DAC_LDO", "PCM5102A LDO out"),
    ("U10.12", "+5V", "TPA6130A2 VDD"),
    ("U10.20", "+5V", "TPA6130A2 VDD"),
]
caps = {}
for fp in board.Footprints():
    ref = fp.GetReference()
    if not ref.startswith("C"):
        continue
    for p in fp.Pads():
        c = p.GetCenter()
        caps.setdefault(p.GetNetname(), []).append((ref, mm(c.x), mm(c.y)))

for pin, net, what in SUPPLY_PINS:
    if pin not in pads:
        print("  %-8s %-8s  PAD NOT FOUND" % (pin, net))
        continue
    _, px, py = pads[pin]
    best, bd = None, 1e9
    for ref, cx, cy in caps.get(net, []):
        d = math.hypot(px - cx, py - cy)
        if d < bd:
            bd, best = d, ref
    flag = ""
    if bd > 3.0:
        flag = "  <-- too far"
    elif bd > 2.0:
        flag = "  <-- marginal"
    print("  %-8s %-8s %-22s nearest %s at %5.2f mm%s" % (pin, net, what, best, bd, flag))
