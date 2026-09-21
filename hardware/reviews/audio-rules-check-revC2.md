# Rev C2 audio-rule check against the routed board

Date: 2026-09-11
Board: `hardware/QuadPreRecorder.kicad_pcb` (Rev C2, routed, DRC 0 / ERC 0)
Tools: `tools/audio_audit.py`, `audio_audit2.py`, `audio_audit3.py`
Origin: the four checks raised by the pcbparts `misc/audio.md` design rules

## Verdict at a glance

| # | Check | Result |
|---|-------|--------|
| 1 | AGND / DGND pin handling on the three audio ICs | **PASS**, one layout defect (U10 exposed pad) |
| 2 | Clock / serial-audio to analog-signal separation | **FAIL**, and it is the worst problem on the board |
| 3 | Converter digital-rail filtering and decoupling | **FAIL**, decouplers are 2.4 to 11.7 mm from their pins, no ferrite beads anywhere |
| 4 | C0G in the signal path | **PARTIAL**, 12 signal-path caps are X7R or unspecified |

Nothing here is a reason to panic. Items 1, 3 and 4 are local edits. Item 2 is
the one that needs a real decision before anything gets fabricated.

---

## Check 1: AGND / DGND. PASS

Pin names confirmed from the symbol libraries, not assumed:

* PCM1864 (U7): pin 7 = AGND, pin 12 = DGND. Both on net `GND`.
* PCM5102A (U9): pin 3 = CPGND, pin 9 = AGND, pin 19 = DGND. All on net `GND`.
* TPA6130A2 (U10): pins 3, 9, 10, 13, 19 = GND, pin 21 = EP. All on net `GND`.
  Pins 15/16 = CPVSS correctly go to `HP_VSS`, not to ground.

This is exactly what the rule asks for: the pin labels describe blocks inside
the die, and every one of them returns to the single In1.Cu plane. No split,
no ground potential to worry about, no ESD-structure risk.

Plane access measured as distance from each ground pad to its nearest ground via:

```
U7   PCM1864       4 GND pads, worst 1.26 mm
U9   PCM5102A      7 GND pads, worst 0.96 mm
U10  TPA6130A2     6 GND pads, worst 2.55 mm   <-- the exposed pad
U2   TPS7A2033     1 GND pad,  0.88 mm
U3   TLE2426       1 GND pad,  1.20 mm
```

### Defect 1.1: U10's exposed pad has zero vias in it

The TPA6130A2 EP is 2.70 x 2.70 mm at (112.000, 56.000). Vias inside it: **0**.
The nearest ground via is 2.55 mm from the pad centre, which is 1.2 mm outside
the pad entirely.

On a WQFN DirectPath amp the exposed pad is both the main ground return for
the output stage and the only heat path off the die. Leaving it with no vias
means the amp's ground current has to leave sideways through the paste joint
and the pad's own copper, and the die runs hot into a 16 ohm load.

**Fix:** a 3x3 array of 0.30 mm drill / 0.60 mm annulus vias on a 0.9 mm pitch
centred on (112.0, 56.0). Cheap, no fab surcharge at that drill size, and
tented from the bottom so paste does not wick away. Nine vias is the usual
count for a 2.7 mm pad.

---

## Check 2: clock to analog separation. FAIL

This is the finding that matters.

### What was measured

Every routed segment on the 21 clock / serial-audio nets was compared against
every routed segment on the 38 analog nets. Perpendicular crossings were
discarded (they couple almost nothing); only runs within 25 degrees of parallel
were counted. The stackup matters here:

```
F.Cu      signal      0.21 mm to In1.Cu (a solid plane)   -> well referenced
In1.Cu    solid GND
In2.Cu    signal      1.07 mm to In1.Cu (across the core) -> poorly referenced
B.Cu      signal      0.21 mm to In2.Cu (a SIGNAL layer)  -> couples to In2
```

Because In1.Cu sits between them, F.Cu is shielded from both inner layers.
The exposed pair is **In2.Cu against B.Cu**, 0.21 mm apart with nothing in
between, and In2.Cu carries more routing than any other layer (41.8%).

### Result

```
total parallel clock-over-analog length, In2/B broadside : ~2100 mm
total parallel clock-to-analog length,   same layer      :  ~230 mm
366 parallel clock/analog net pairs
```

(The totals sum every overlapping segment pair, so they over-count where several
short segments track the same run. Treat them as a severity index, not a
literal length. The individual pairs below are the ones that matter.)

Worst offenders:

```
par_mm   gap_mm   aggressor      victim        mode
43.1     0.152    DAC_DIN        BLD_AC        same-layer
40.4     ~0.21    ADC_DOUT2      BLD_RAW       broadside In2/B
36.1     ~0.21    ADC_DOUT2      BRU_PRE       broadside In2/B
35.2     ~0.21    ADC_DOUT2      FRD_RAW       broadside In2/B
35.0     ~0.21    DAC_BCLK       FRD_RAW       broadside In2/B
33.6     0.202    DAC_DIN        FRD_ADC       same-layer
24.1     0.152    ADC_TDM_IC     BRU_ADC       same-layer
```

Also, on B.Cu the `ADC_LRCLK` track runs directly over the PCM1864's own
analog input pads (U7.1 through U7.6, including `ADC_MICBIAS` and `ADC_VREF`).
Those are shielded by In1.Cu so it is not fatal, but it is not where you want
the word clock.

### Why this is bad, in numbers

The victim nodes are high impedance. `_RAW` sits behind a 4.7k electret bias
resistor, so a few kilohms. `_AC` is loaded by the 1M bias resistor and the
68k/33k pad divider, so roughly 64k. Against that, 40 mm of 0.2 mm track
stacked 0.21 mm above another 0.2 mm track is on the order of 1.5 to 2 pF of
coupling.

Against maybe 10 pF of node capacitance to ground, a 3.3 V logic edge puts
roughly 2/(2+10) x 3.3 V, several hundred millivolts, onto a node carrying a
few millivolts of microphone signal. Even allowing a factor of ten for the
partial shielding from the In2.Cu ground pour and for my coupling estimate
being pessimistic, that is tens of millivolts of 12.288 MHz hash arriving at
the PGA input. A 192 kHz sampler folds that straight back into the audio band.

### The actual root cause: J6 and J7

The analog nets are absurdly long for what they are:

```
BRU_PRE  223.1 mm      BLD_RAW  196.8 mm
FRD_PRE  220.4 mm      BRU_ADC  181.6 mm
BRU_RAW  215.4 mm      FRD_AC   178.1 mm
BRU_AC   212.9 mm      FRD_RAW  176.9 mm
```

`BRU_PRE` is an op-amp output. It should be a few millimetres. It is 223 mm.

The reason is `J6`, the 2x13 analog test header at (82.0, 6.0). It brings all
five stages of all four channels (20 analog nets) to the top edge of the board,
while the analog circuitry lives at x 40 to 56, y 44 to 56. Every analog node
therefore makes a round trip across the board to reach it.

And `J7`, the digital test header carrying all 21 clock and bus nets, sits at
(82.0, 12.5): **6.5 mm away from J6**.

So the two headers force every sensitive analog node and every digital node
into the same corner, and make them travel the length of the board side by
side to get there. The analog nets span x 1.7 to 120.1 and y 1.1 to 108.2,
which is essentially the whole 138 x 114 mm board. Freerouting did not do
anything unreasonable; it was handed a netlist that demands this.

### Options, cheapest first

**A. Replace J6 with local test pads. Recommended.**
Drop the header and put a 1.5 mm test pad at each node, right where the node
already is. Zero added trace length, still probeable with a scope hook, and
roughly 1.9 m of analog copper disappears from the board. Cost: nothing, and
it frees the routing budget that option D below needs.

**B. Keep J6 but move it into the analog block** (somewhere around x 45, y 75,
under U4/U5/U6) and move J7 over to the digital side near the Teensy. Keeps
the convenience of one connector per domain, cuts most of the length, and puts
real distance between the two headers.

**C. Keep J6 where it is and isolate it.** Put a 1k series resistor in each of
the 20 test-point nets so the long run becomes a stub hanging off 1k instead
of part of the live node. 20 extra 0402s, roughly $0.60 in parts. This fixes
the antenna effect but not the fact that 20 analog runs still cross the board
alongside 21 digital ones, so it is a partial fix only.

**D. Make In2.Cu a solid ground plane and route on F.Cu and B.Cu only.**
This is the textbook mixed-signal 4-layer: SIG / GND / GND / SIG. Every trace
then has a reference plane 0.21 mm away, and there is no signal-to-signal
broadside adjacency anywhere on the board. It also fixes the separate problem
that In2.Cu currently has no usable reference plane at all (1.07 mm across
the core).

Feasibility: current routing is F 4.36 m, In2 5.01 m, B 2.62 m, total 12.0 m.
Two layers would need about 6 m each. B.Cu is only 21.9% utilised so there is
headroom, and doing option A first removes roughly 1.9 m of demand. Tight but
plausible. Worth one trial run of the pipeline before committing.

**E. Six layers.** Worth being straight with you here: when you asked about
going to 6 layers for AGND/DGND, the answer was no, and that is still correct,
splitting the ground plane would make things worse. But this measurement found
a *different* stackup problem, and 6 layers does address that one. A
SIG/GND/SIG/SIG/GND/SIG build gives all four signal layers a plane within
0.1 to 0.2 mm and puts the inner signal pair about 0.7 mm apart across the
centre core, instead of 0.21 mm.

Cost: 4-layer at this size is roughly $20 to $40 for five pieces from JLCPCB
or PCBWay. Six-layer is roughly $90 to $150 for the same five, with a longer
lead time and a stackup change that reopens the enclosure fit work.

My read: do A, then try D. If D will not route, then E is a legitimate
purchase rather than an over-spend. But do not buy layers before fixing J6,
because J6 is what is consuming them.

---

## Check 3: converter digital rails. FAIL

### 3.1 Decoupling capacitors are nowhere near their pins

Distance from each supply pin to the centre of its nearest same-net capacitor:

```
pin      net       function                nearest    distance
U7.8     +3V3_A    PCM1864 AVDD            C42 10uF     2.41 mm    (C41 100nF is 6.4 mm)
U7.13    +3V3_D    PCM1864 DVDD            C44 100nF    4.76 mm
U7.14    +3V3_D    PCM1864 IOVDD           C44 100nF    4.35 mm
U7.11    ADC_LDO   PCM1864 LDO out         C43 100nF    2.77 mm
U9.1     +3V3_A    PCM5102A AVDD           C54 100nF    5.77 mm
U9.8     +3V3_A    PCM5102A AVDD           C64 100nF    7.23 mm
U9.20    +3V3_D    PCM5102A DVDD           C63 100nF   11.72 mm
U9.18    DAC_LDO   PCM5102A LDOO           C53 1uF      7.56 mm
U10.12   +5V       TPA6130A2 VDD           C65 1uF      5.04 mm
U10.20   +5V       TPA6130A2 VDD_CP        C65 1uF      5.61 mm
```

The target is under 1.5 mm for a 100 nF, with its own via right beside the pad.
Every single one of these misses, and the DAC's DVDD pin misses by 8x.

Two things go wrong at that distance. The loop inductance roughly triples,
which drops the decoupler's series-resonant frequency and makes its impedance
climb steeply above about 20 MHz, so the IC's fast transient current is no
longer supplied locally. And that current instead travels several millimetres
through the rail and the plane, which is precisely the noise that check 2 is
already struggling to keep out of the analog nodes.

Also note U7.8: the 10 uF bulk cap is closer to the pin than the 100 nF. That
ordering should be reversed; small cap nearest, bulk behind it.

**Fix:** reposition each decoupler to within 1.5 mm of its pin, on the bottom
side directly beneath where possible, with its ground via at the cap pad. The
exact pad coordinates are now known and in `tools/audio_audit2.py` output, so
this can be scripted against `generate_pcb.py` rather than dragged by hand.

### 3.2 There is not a single ferrite bead on the board

`generate_schematic.py` defines an `FB` symbol at line 568 and never
instantiates it. Grep confirms zero bead parts in the BOM.

More to the point, `+3V3_D` is **the Teensy 4.1's own on-board 3.3 V
regulator output** (`3V3A`/`3V3B` on the module). That single rail feeds:

* the i.MX RT1062 running at 600 MHz
* the PCM1864's DVDD and IOVDD
* the PCM5102A's DVDD
* the I2C pull-ups and every button pull-up (R50, R51-53, R70-74, R94-97)

So the two converters' digital sections are hanging directly off the noisiest
node in the system, with no filtering at all between them.

`+3V3_A` is in much better shape: buck U1 to +5V, then LDO U2 (TPS7A2033) to
+3V3_A. That is the right topology and it should stay.

**Fix, in order of value:**

1. A ferrite bead in series with `+3V3_D` at each converter, with the 100 nF on
   the IC side of the bead. Something like a Murata BLM18PG221SN1D (220 ohm at
   100 MHz, 1.6 A, 0603), about $0.10 each. Two beads, one for U7 and one for
   U9. This alone confines each converter's switching loop to its own local cap.
2. Better still, feed both converters' digital rails from their own small LDO
   off +5V rather than from the Teensy. A second TPS7A2033 in SOT-23-5 plus two
   caps is about $1.20 and roughly 30 mm2. Given that this is a recorder whose
   entire reason to exist is the noise floor, that is cheap.

---

## Check 4: signal-path dielectrics. PARTIAL

Correct already:

```
C13-C16   100pF C0G    _MIC to CHASSIS        RF bypass
C21-C24   22pF  C0G    _PRE to _FB            op-amp feedback
C29-C32   10nF  C0G    _ADC to GND            anti-alias
C67 C68   2.2nF C0G    LINE_L/R to GND        reconstruction filter
```

Needs attention:

```
ref        value        path                        note
C17-C20    4.7uF 16V    _MIC -> _AC                 input coupling, dielectric unspecified
C25-C28    4.7uF 16V    _PRE -> _ADC_SRC            output coupling, dielectric unspecified
C57 C58    2.2uF X7R    LINE_L/R -> HP_IN_L/R       headphone input coupling
C86 C87    2.2uF X7R    HP_INP_L/R -> GND           headphone input reference
```

C17-C20 and C25-C28 are listed only as "4.7uF 16V" size 1206. At that value
and package they will be ordered as X5R or X7R by default, which is worth
fixing deliberately rather than by accident.

The real-world position: a 2.2 or 4.7 uF C0G does not exist in any sane package,
so C0G is not the answer here. What matters is how much signal voltage appears
*across* the cap, because Class II ceramic distortion scales with that. Three
practical routes:

1. **Oversize the ceramic.** Going from 4.7 uF to 22 uF X7R drops the signal
   voltage across the cap by about 5x at the low end, and distortion drops
   faster than linearly with it. Costs about $0.15 each and one package size.
   This is the lazy-but-effective option.
2. **PPS film.** Panasonic ECH-U or similar, 2.2 uF PPS is roughly $1.20 each
   and physically large (about 7 x 6 mm). Essentially zero voltage coefficient
   and no piezoelectric behaviour. Eight of these is about $10 and a real
   amount of board area you do not currently have.
3. **Bipolar electrolytic.** Nichicon MUSE ES 4.7 uF, about $0.50, small,
   well-behaved for coupling. The usual audio compromise.

For C57/C58/C86/C87 in the headphone path: the TPA6130A2's input impedance is
around 10k, so 2.2 uF gives a 7 Hz corner. Bumping those to 10 uF X7R (about
$0.10 each) puts the corner at 1.6 Hz and cuts the signal voltage across the
dielectric by more than 4x. Cheapest meaningful improvement in this section.

For C9/C10/C11 (the TLE2426 VREF rail) and C38/C39/C40 (MICBIAS and VREF):
these are bias rails, not signal path, so X7R is fine. They should still be
specified explicitly rather than left blank.

---

## Recommended order of work

1. **Decide the J6 question.** Everything in check 2 flows from it. Option A
   (local test pads) is my recommendation.
2. Reposition the decouplers (check 3.1). Scriptable against the pad
   coordinates now in hand.
3. Add the nine EP vias under U10 (check 1.1).
4. Add the two ferrite beads, or the dedicated digital LDO (check 3.2).
5. Specify the coupling-cap dielectrics (check 4).
6. Re-run the full pipeline, then re-run these three audit scripts and confirm
   the parallel-run numbers actually came down.

Steps 1 through 5 are all edits to `generate_schematic.py` and
`generate_pcb.py`, so they land in one rebuild.

## What is NOT wrong

Worth stating plainly, because the board is in good shape otherwise:

* Ground topology is correct. One net, one solid plane, 174/174 pads in a
  single connected cluster, per-pad fanout vias.
* AGND/DGND handling matches the rule exactly.
* The analog supply chain (buck to +5V, LDO to +3V3_A) is the right topology.
* PCM5102A configuration pins are all set correctly: SCK low for internal PLL,
  FMT low for I2S, DEMP low, FLT low.
* Series termination resistors (33R) are present on every clock and data line.
* DRC 0, ERC 0, 0 unconnected, 0 schematic parity issues.
