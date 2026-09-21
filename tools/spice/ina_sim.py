"""Rev C3 differential front end (two-op-amp INA) check with ngspice.

Per channel, dynamic-mic mode (cold leg released):
  hot : RAW --100R-- MIC --4u7-- AC --(1M to VREF, and 68k+33k pad divider to VREF)-- A2(+)
  cold: RAWC --100R-- MICC --4u7-- ACC --(1M to VREF)-- A1(+)
  A1  : out CPRE, (-) CFB, Ra 10k CFB-CPRE, Rb 90.9k CFB-VREF, 22p CPRE-CFB
  A2  : out PRE,  (-) FB,  Rg 10k FB-CPRE,  Rf 90.9k PRE-FB,   22p PRE-FB
VREF is the AC ground here (0 V). Op-amps are behavioural: Aol 120 dB, GBW 18 MHz,
4.5 nV/rtHz input noise (as a 1.23 k noisy resistor), infinite CMRR (the OPA1654's
120 dB is far above the resistor-limited figure we are measuring).
"""
import itertools, math, subprocess, re, os, sys

RS = float(os.environ.get("RS", "150"))   # source resistance per leg (300 ohm dynamic mic)
COLD_LOAD = os.environ.get("COLD_LOAD", "none")  # "none" = board as designed, else ohms added ACC-VREF
CAP_HOT = float(os.environ.get("CAP_HOT", "4.7e-6"))
CAP_COLD = float(os.environ.get("CAP_COLD", "4.7e-6"))
CA_ACROSS = os.environ.get("CA_ACROSS", "ra")  # ra = board as designed (C105 CPRE-CFB), rb = proposed (CFB-VREF), none

OPAMP = """
.subckt opamp inp inn out
Rn inp inpn 1.23k
Ein x 0 inpn inn 1e6
Rp x y 1k
Cp y 0 8.84u
Eo out 0 y 0 1
.ends
"""
# Aol = 1e6 (120 dB); pole at 1/(2*pi*1k*8.84u) = 18 Hz -> GBW 18 MHz.

def netlist(ra, rb, rf, rg, mode, cold_grounded=False, noise=False):
    cold_load = "" if COLD_LOAD == "none" else f"Rcl acc 0 {COLD_LOAD}\n"
    if mode == "diff":
        src = "Vh raw 0 dc 0 ac 0.5\nVc rawc 0 dc 0 ac -0.5\n"
    elif mode == "cm":
        src = "Vh raw 0 dc 0 ac 1\nVc rawc 0 dc 0 ac 1\n"
    else:  # noise: drive from a single source through a centre-tapped ideal transformer is
        # overkill; use hot-only drive (input-referred noise is the same for a differential
        # stage driven single-ended with the other leg terminated in Rs).
        src = "Vh raw 0 dc 0 ac 1\nVc rawc 0 dc 0\n"
    cold_leg = ("Rsw micc 0 120\n" if cold_grounded else "")
    return f"""* two-op-amp INA, mode {mode}
{OPAMP}
{src}
Rsh raw mic_h {RS}
Rsc rawc micc {RS}
Rrfh mic_h mic 100
Rrfc micc micc2 100
{cold_leg}
Ch mic ac {CAP_HOT}
Cc micc2 acc {CAP_COLD}
Rbh ac 0 1meg
Rbc acc 0 1meg
Rpad1 ac att 68k
Rpad2 att 0 33k
{cold_load}Rsw2 ac pad 120
XA1 acc cfb cpre opamp
Ra cfb cpre {ra}
Rb cfb 0 {rb}
{"Ca cpre cfb 22p" if CA_ACROSS == "ra" else ("Ca cfb 0 22p" if CA_ACROSS == "rb" else "")}
XA2 pad fb pre opamp
Rg fb cpre {rg}
Rf pre fb {rf}
Cf pre fb 22p
.control
set filetype=ascii
{"noise v(pre) Vh dec 20 20 20k" if noise else "ac dec 20 1 1meg"}
{"print inoise_total onoise_total" if noise else "wrdata out.txt v(pre)"}
quit
.endc
.end
"""

def run(nl):
    with open("nl.cir", "w") as f:
        f.write(nl)
    r = subprocess.run(["ngspice", "-b", "nl.cir"], capture_output=True, text=True)
    return r.stdout + r.stderr

def ac_gain(nl):
    run(nl)
    pts = {}
    for line in open("out.txt"):
        v = line.split()
        if len(v) >= 3:
            f, re_, im = float(v[0]), float(v[1]), float(v[2])
            pts[f] = math.hypot(re_, im)
    return pts

def at(pts, f0):
    f = min(pts, key=lambda x: abs(math.log(x / f0)))
    return pts[f]

def db(x):
    return 20 * math.log10(x) if x > 0 else -999

RA, RB, RF, RG = 10e3, 90.9e3, 90.9e3, 10e3
FREQS = (20, 50, 60, 100, 1000, 10000, 20000)

print(f"Rs per leg = {RS:.0f} ohm, cold-leg extra load = {COLD_LOAD}, A1 22p across = {CA_ACROSS}, caps hot/cold = {CAP_HOT*1e6:.2f}/{CAP_COLD*1e6:.2f} uF\n")

gd = ac_gain(netlist(RA, RB, RF, RG, "diff"))
print("Differential gain (nominal resistors):")
for f in FREQS + (50000, 100000):
    print(f"   {f:>7.0f} Hz  {db(at(gd, f)):6.2f} dB")
f3 = max(f for f, g in gd.items() if g >= at(gd, 1000) / math.sqrt(2))
print(f"   -3 dB (upper) about {f3/1e3:.0f} kHz\n")

ge = ac_gain(netlist(RA, RB, RF, RG, "noise", cold_grounded=True))
print(f"Electret mode (cold leg grounded through the CD4053, 120 ohm): hot-leg gain at 1 kHz = {db(at(ge, 1000)):.2f} dB\n")

gc = ac_gain(netlist(RA, RB, RF, RG, "cm"))
print("CMRR with NOMINAL resistors (limited only by the input network):")
for f in FREQS:
    print(f"   {f:>7.0f} Hz  {db(at(gd, f) / at(gc, f)):6.1f} dB")

print("\nCMRR worst case over the 16 +/-0.1 % resistor corners:")
worst = {f: 1e9 for f in FREQS}
worst_case = {}
for s in itertools.product((-1, 1), repeat=4):
    ra, rb, rf, rg = [v * (1 + 0.001 * k) for v, k in zip((RA, RB, RF, RG), s)]
    gcx = ac_gain(netlist(ra, rb, rf, rg, "cm"))
    gdx = ac_gain(netlist(ra, rb, rf, rg, "diff"))
    for f in FREQS:
        c = db(at(gdx, f) / at(gcx, f))
        if c < worst[f]:
            worst[f], worst_case[f] = c, s
for f in FREQS:
    print(f"   {f:>7.0f} Hz  {worst[f]:6.1f} dB   corner Ra,Rb,Rf,Rg = {worst_case[f]}")

out = run(netlist(RA, RB, RF, RG, "noise", noise=True))
m = re.search(r"inoise_total\s*=\s*([0-9.e+-]+)", out)
n = re.search(r"onoise_total\s*=\s*([0-9.e+-]+)", out)
if m:
    vin = float(m.group(1))
    vout = float(n.group(1))
    print(f"\nNoise 20 Hz - 20 kHz, source {RS:.0f} ohm per leg:")
    print(f"   output noise      {vout*1e6:7.2f} uV rms")
    print(f"   input-referred    {vin*1e9:7.2f} nV rms  = {20*math.log10(vin/0.7746):6.1f} dBu (EIN)")
    print(f"   spot density approx {vin/math.sqrt(19980)*1e9:5.2f} nV/rtHz")
else:
    print(out[-2000:])
