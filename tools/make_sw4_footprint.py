"""Build the KiCad footprint for SW4, the Alps RKJXT1F42001 5-way encoder.

Geometry is NOT invented.  Every number below is converted straight out of
the official LCSC/EasyEDA library entry for LCSC part C160841:

    symbol   uuid 80a99ae43c094f028e53fc518925e053
    footprint uuid f2c3764afb3c4f93a8c5faf618ae8163   ("SW-TH_RKJXT1F42001")

EasyEDA stores that footprint in units of 10 mil, i.e. 1 unit = 0.254 mm,
with the package origin at (4000, 3000).  The 3D-outline node in the same
record declares c_width = c_height = 66.929 units, and 66.929 * 0.254 =
17.000 mm, which is exactly the 17 x 17 mm body Alps publishes - that is
the cross-check that pins the scale down.

Pad names are the EasyEDA/Alps names, and the functions come from the
EasyEDA symbol's pin labels:

    A, B, C, D  the four direction contacts
    5  = PUSH   centre push
    6  = COM    common for the directions AND the push
    7  = E_B    encoder phase B
    8  = E_A    encoder phase A
    9  = E_C    encoder common
    10 = unnamed in the library; leave it NC

Run:  python tools/make_sw4_footprint.py
"""

from pathlib import Path

MM = 0.254                      # one EasyEDA unit
OX, OY = 4000.0, 3000.0         # EasyEDA package origin

OUT = (Path(__file__).resolve().parent.parent
       / "hardware" / "QuadPreRecorder.pretty"
       / "SW_Nav5_ALPS_RKJXT1F42001.kicad_mod")

NAME = "SW_Nav5_ALPS_RKJXT1F42001"


def conv(x, y):
    """EasyEDA absolute coordinate -> KiCad mm, relative to the body centre."""
    return round((x - OX) * MM, 4), round((y - OY) * MM, 4)


# --- verified from the EasyEDA PAD records -------------------------------
# PAD~ELLIPSE~x~y~w~h~layer~net~number~holeRadius~...
PADS_EDA = [
    ("A",  3994.095, 3030.709),
    ("5",  4003.937, 3027.480),
    ("B",  4030.709, 3005.906),
    ("7",  4030.709, 2994.095),
    ("C",  4005.906, 2969.291),
    ("9",  3994.095, 2969.291),
    ("6",  3996.063, 2977.244),
    ("D",  3969.291, 2994.095),
    ("8",  3969.291, 3005.906),
    ("10", 4027.008, 3014.764),
]
PAD_DIA = round(7.0866 * MM, 3)          # 1.8 mm copper
PAD_DRILL = round(2 * 2.3622 * MM, 3)    # 1.2 mm hole for the 1.0 mm terminals

# HOLE~3985.039~3005.906~2.5591  (radius, in units) - the locating boss
BOSS_EDA = (3985.039, 3005.906)
BOSS_DRILL = round(2 * 2.5591 * MM, 3)   # 1.3 mm for the 1.1 mm boss

HALF = round(33.4645 * MM, 3)            # 8.5 mm - half of the 17 mm body
CHAM = round(25.0984 * MM, 3)            # 6.375 mm - where the corner chamfers start
SHAFT_R = round(8.366 * MM, 3)           # 2.125 mm shaft circle
CRTYD = 8.95                             # body 8.5 + pads reaching 8.7, +0.25

# Silk has to break where a pad pokes through the body edge.  For an edge pad
# the outline crosses the 1.8 mm pad over +/-0.566 mm; 0.77 mm gives 0.2 mm of
# clearance on top of that.
GAP = 0.77

_uid = [0]


def uuid():
    _uid[0] += 1
    n = _uid[0]
    return "4a1b0000-0000-4000-8000-%012x" % n


def line(x1, y1, x2, y2, layer, width):
    return f"""\t(fp_line
\t\t(start {x1} {y1})
\t\t(end {x2} {y2})
\t\t(stroke
\t\t\t(width {width})
\t\t\t(type default)
\t\t)
\t\t(layer "{layer}")
\t\t(uuid "{uuid()}")
\t)"""


def circle(cx, cy, r, layer, width, fill="no"):
    return f"""\t(fp_circle
\t\t(center {cx} {cy})
\t\t(end {round(cx + r, 4)} {cy})
\t\t(stroke
\t\t\t(width {width})
\t\t\t(type default)
\t\t)
\t\t(fill {fill})
\t\t(layer "{layer}")
\t\t(uuid "{uuid()}")
\t)"""


def rect(half, layer, width):
    return "\n".join([
        line(-half, -half,  half, -half, layer, width),
        line( half, -half,  half,  half, layer, width),
        line( half,  half, -half,  half, layer, width),
        line(-half,  half, -half, -half, layer, width),
    ])


def edge_segments(pad_offsets):
    """Split one body edge into silk runs, skipping each pad in pad_offsets."""
    stops = [-CHAM]
    for p in sorted(pad_offsets):
        stops += [round(p - GAP, 4), round(p + GAP, 4)]
    stops.append(CHAM)
    return [(stops[i], stops[i + 1]) for i in range(0, len(stops), 2)]


def build():
    body = []

    # --- silk: body outline, broken around the edge pads ------------------
    for a, b in edge_segments([-1.5, 1.5]):          # top edge, pads 9 and C
        body.append(line(a, -HALF, b, -HALF, "F.SilkS", 0.15))
    for a, b in edge_segments([-1.5, 1.5]):          # bottom edge
        # only pad A sits on the bottom edge, at x = -1.5; the 1.5 slot is
        # filled in again below
        body.append(line(a, HALF, b, HALF, "F.SilkS", 0.15))
    for a, b in edge_segments([-1.5, 1.5]):          # right edge, pads 7 and B
        body.append(line(HALF, a, HALF, b, "F.SilkS", 0.15))
    for a, b in edge_segments([-1.5, 1.5]):          # left edge, pads D and 8
        body.append(line(-HALF, a, -HALF, b, "F.SilkS", 0.15))
    # bottom edge has no pad at x = +1.5, so close that gap back up
    body.append(line(round(1.5 - GAP, 4), HALF, round(1.5 + GAP, 4), HALF,
                     "F.SilkS", 0.15))

    # corner chamfers
    body.append(line( CHAM, -HALF,  HALF, -CHAM, "F.SilkS", 0.15))
    body.append(line( HALF,  CHAM,  CHAM,  HALF, "F.SilkS", 0.15))
    body.append(line(-CHAM,  HALF, -HALF,  CHAM, "F.SilkS", 0.15))
    body.append(line(-HALF, -CHAM, -CHAM, -HALF, "F.SilkS", 0.15))

    # --- fab: true body outline, unbroken, plus the shaft ------------------
    fab = [
        ( CHAM, -HALF), ( HALF, -CHAM),
        ( HALF,  CHAM), ( CHAM,  HALF),
        (-CHAM,  HALF), (-HALF,  CHAM),
        (-HALF, -CHAM), (-CHAM, -HALF),
    ]
    for i in range(len(fab)):
        x1, y1 = fab[i]
        x2, y2 = fab[(i + 1) % len(fab)]
        body.append(line(x1, y1, x2, y2, "F.Fab", 0.1))
    body.append(circle(0, 0, SHAFT_R, "F.Fab", 0.1))
    # orientation dot beside pad A, on fab so it cannot clash with silk
    body.append(circle(-1.5, 6.4, 0.25, "F.Fab", 0.1, fill="yes"))

    # --- courtyard ---------------------------------------------------------
    body.append(rect(CRTYD, "F.CrtYd", 0.05))

    # --- pads --------------------------------------------------------------
    for name, ex, ey in PADS_EDA:
        x, y = conv(ex, ey)
        body.append(f"""\t(pad "{name}" thru_hole circle
\t\t(at {x} {y})
\t\t(size {PAD_DIA} {PAD_DIA})
\t\t(drill {PAD_DRILL})
\t\t(layers "*.Cu" "*.Mask")
\t\t(remove_unused_layers no)
\t\t(uuid "{uuid()}")
\t)""")

    bx, by = conv(*BOSS_EDA)
    body.append(f"""\t(pad "" np_thru_hole circle
\t\t(at {bx} {by})
\t\t(size {BOSS_DRILL} {BOSS_DRILL})
\t\t(drill {BOSS_DRILL})
\t\t(layers "F&B.Cu" "*.Mask")
\t\t(uuid "{uuid()}")
\t)""")

    descr = ("ALPS RKJXT1F42001 multi-directional switch: 4-way + centre push + "
             "incremental rotary encoder, THT, 17x17x10.5 mm body, one 1.1 mm "
             "locating boss. Pads A/B/C/D = directions, 5 = PUSH, 6 = COM "
             "(shared by directions and push), 7 = E_B, 8 = E_A, 9 = E_C, "
             "10 = NC. Geometry from the LCSC/EasyEDA library for C160841.")

    header = f"""(footprint "{NAME}"
\t(version 20260206)
\t(generator "make_sw4_footprint.py")
\t(generator_version "10.0")
\t(layer "F.Cu")
\t(descr "{descr}")
\t(tags "ALPS RKJXT 5-way navigation encoder rotary push multidirectional THT")
\t(property "Reference" "REF**"
\t\t(at 0 -10.2 0)
\t\t(layer "F.SilkS")
\t\t(uuid "{uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t)
\t)
\t(property "Value" "{NAME}"
\t\t(at 0 10.2 0)
\t\t(layer "F.Fab")
\t\t(uuid "{uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t)
\t)
\t(property "Datasheet" "https://www.lcsc.com/product-detail/C160841.html"
\t\t(at 0 0 0)
\t\t(layer "F.Fab")
\t\t(hide yes)
\t\t(uuid "{uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t)
\t)
\t(property "Description" "5-way navigation switch with rotary encoder"
\t\t(at 0 0 0)
\t\t(layer "F.Fab")
\t\t(hide yes)
\t\t(uuid "{uuid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t)
\t)
\t(attr through_hole)
\t(duplicate_pad_numbers_are_jumpers no)"""

    return header + "\n" + "\n".join(body) + "\n\t(embedded_fonts no)\n)\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print("wrote", OUT)
    print("body half-size %.3f mm, chamfer at %.3f mm" % (HALF, CHAM))
    print("pad copper %.3f mm, drill %.3f mm, boss drill %.3f mm"
          % (PAD_DIA, PAD_DRILL, BOSS_DRILL))
    for name, ex, ey in PADS_EDA:
        print("  pad %-3s at %8.3f %8.3f" % ((name,) + conv(ex, ey)))
    print("  boss   at %8.3f %8.3f" % conv(*BOSS_EDA))
