# Rev C3: the audio-rule fix pass

Date: 2026-09-12
Board: `hardware/QuadPreRecorder.kicad_pcb` (Rev C3, routed, DRC 0 / 0 unconnected / 0 parity, ERC 0)
Backup of this exact board: `hardware/QuadPreRecorder.kicad_pcb.revc3-routed-clean-20260912`
Follows: `audio-rules-check-revC2.md` (the audit that found all of this)
Audit re-run outputs: `review_outputs/audio_audit_c3.txt`, `audio_audit2_c3.txt`, `audio_audit3_c3.txt`

## What was asked

Remove J6 and J7, fix every FAIL from the Rev C2 audit, put the converters'
digital rail on a second TPS7A2033, see whether film coupling caps fit now
that the headers are gone, and catch anything the four checks missed.

## Scorecard

| # | Rev C2 finding | Rev C3 |
|---|---|---|
| 1 | AGND/DGND: pass, but U10's exposed pad had **0** vias | 3x3 array of 0.30 mm vias on a 0.9 mm pitch in the pad; U10.13 tied straight into the pad. **Pass, no defect.** |
| 2 | Clock-to-analog: **366** parallel pairs, ~2100 mm broadside In2/B + ~230 mm same-layer, BRU_PRE 223 mm, analog copper over the whole board | **14** pairs, **0 mm broadside**, 64.6 mm same-layer. Analog copper 1654 mm total and confined to x 2..86 / y 41..108. BRU_PRE 82.7 mm. **Pass** (residual discussed below). |
| 3 | Decouplers 2.4..11.7 mm from their pins, 10 uF closer than 100 nF, no bead/LDO on the converter digital rail | Every 100 nF is 1.34..1.60 mm from its pin with its own via; 10 uF sit behind the 100 nF; DVDD/IOVDD come from U14 (+3V3_DC). **Pass.** |
| 4 | Coupling caps unspecified/X7R | C17-C20, C25-C28: Rubycon PMLCAP 4.7 uF 35 V (1812). C57/C58/C86/C87: PMLCAP 2.2 uF 25 V (1210). **Pass.** |
| + | Stackup: In2.Cu had no reference plane (1.07 mm across the core) and faced B.Cu at 0.21 mm | In2.Cu is a solid GND plane. Stackup is SIG / GND / GND / SIG and is now written into the board file. |

## What changed, in the order it was done

### J6 / J7 are gone
Both 2x13 test headers, their 41 net stubs, R68 (the 1 k PAD_DBG protector),
the schematic note and every doc mention. Nothing replaced them: with the
headers gone every stage node still has an 0603 / 1812 pad on the top side of
the channel rows, and the clocks are reachable at the 33 R terminators. The
generator edits are in `tools/generate_schematic.py` and
`tools/generate_pcb.py`; docs updated: README, AGENTS, `connector-pinout.md`,
`requirements.md`, `mechanical.md`, `enclosure-fit-audit.md`, the PCBWay
order notes and manufacturing README.

### In2.Cu became a plane
`generate_pcb.py::add_ground_planes` now puts the wire-keepout rule area on
In1 **and** In2; `tools/patch_dsn_plane.py` marks both as Specctra
`(type power)`. Freerouting therefore routed on F.Cu and B.Cu only. It
fitted: 8.72 m of track (F 4.67 m, B 4.05 m) against 12.0 m over three
layers in Rev C2, because the two headers were eating 1.9 m of analog
routing plus everything digital that had to follow them to the rear edge.
Every track now has a plane 0.21 mm away and no two signal layers face each
other, which is why the broadside number is exactly zero.

`tools/set_stackup.py` (new, end of pipeline) writes the explicit stackup:
35 um copper, 0.21 mm prepreg / 1.065 mm core / 0.21 mm prepreg, the same
build the fab was silently applying before. PCBWay's standard 1.6 mm
4-layer matches it; no impedance control is needed.

### U14: the converters' own 3.3 V
Second TPS7A2033 (SOT-23-5) off +5V, output net `+3V3_DC`, input C95 1 uF,
output C96 4.7 uF, placed on the bottom directly under U2 so both LDOs share
the +5V feed. It feeds only U7.13/14 (PCM1864 DVDD / IOVDD) and U9.20
(PCM5102A DVDD). `+3V3_D`, the Teensy's own regulator output, now carries
only pull-ups (I2C, buttons, encoder, charger status). C63, the second
+3V3_D 100 nF, was dropped. Cost: about $1.20 for the LDO and $0.10 for the
caps.

### Decoupling under the pins
The audit's target was a 100 nF within 1.5 mm of the pin with its own via.
On a 0.5 / 0.65 mm pitch TSSOP a 0.6 mm via cannot sit in the pin row (the
annulus would violate clearance to the neighbouring pins), so the legal
spot is just inside the IC body past the pad's inner end. The caps now sit
on the **bottom** with their pad 1 exactly under that spot:

```
U7  PCM1864   vias at x=82.0   C40 VREF 100n (47.7)  C41 AVDD 100n (49.3)
                                C43 LDO 100n (50.9)   C44 DVDD 100n (52.5)
              bulk column x=87.1: C42 AVDD 10u, C62 LDO 10u, C45 DVDD 10u
              C39 VREF 1u (83.0,45.9)  C38 MICBIAS 1u (80.2,46.5)
U9  PCM5102A  vias at x=98.5 (pins 1/8 AVDD -> C54, C64, caps point west)
              vias at x=101.5 (pin 20 DVDD -> C56, pin 18 LDOO -> C53 1u 0603)
              C55 AVDD 10u bulk south of the IC (99.9,55.0)
              C51 / C52 charge-pump 2.2u moved from 6 mm away to (94.7, 48.4 / 51.9)
U10 TPA6130A2 C59 flying cap straight above pins 17/18 (112.75,52.2)
              C61 CPVDD (110.3,51.75)  C60 CPVSS (116.25,54.6)  C65 VDD (116.25,56.2)
```

`tools/fanout_decouple.py` (new, runs before `fanout_gnd.py`) places those
vias and their 0.6 mm stubs on the pristine board so Freerouting inherits
them as protected wiring; it also lays the U10 exposed-pad array, the U10.13
ground stub, the U10.12 -> C65 track that Freerouting has never managed on
its own, and the U11.4 / U11.5 escape vias (see "the two stragglers").
Measured pin-to-cap-pad distances now:

```
U7.8  AVDD  1.40   U7.13/14 DVDD 1.47/1.39   U7.11 LDO 1.39   U7.6 VREF 1.60
U9.1  AVDD  1.34   U9.8 AVDD 1.34   U9.20 DVDD 1.34   U9.18 LDOO 1.34
U10.12 VDD 1.54    U10.20 CPVDD 1.67   U10.15 CPVSS 1.56   U10.18 CPP 1.84
U9.2 CAPP 2.45 / U9.5 VNEG 2.75  (were 6 mm)      U14 in/out 5.3 / 3.3 (LDO caps, fine)
```

The audit missed two of these: the PCM1864 **VREF** cap pair (C39/C40) and
its MICBIAS cap were 25 mm away on the far side of the Teensy socket, and
the PCM5102A charge-pump caps were 6 mm out. All fixed in the same move.

### Film coupling caps: they fit without moving anything
The blocker in Rev C2 was the 4 mm column pitch of the channel rows, not
the headers. Rubycon's PMLCAP (metallised acrylic film, the SMD film part
made for exactly this job) comes in 1812 at 4.7 uF: 4.5 x 3.2 x 1.6 mm,
which is 4.0 mm wide in the rotated orientation the rows already use.
So C17-C20 and C25-C28 changed footprint in place. The 1812 courtyard is
6.1 mm tall rotated, so the row pitch went from 6.0 to 6.3 mm (rows at y
85.5 / 91.8 / 98.1 / 104.4); nothing else moved and no wall part is
affected. The headphone caps went to 1210 (2.2 uF) and moved from 16 mm
past U10 in the right-wall strip to between the DAC filter and U10's input
pins (x 100.4 / 105.2, y 55.7 / 59.1); the filter (R62/R63/C67/C68) slid
2 mm west to make room.

Parts and prices (LCSC, in stock 2026-09-12):

| Ref | Part | Size | LCSC | Price | Stock |
|---|---|---|---|---|---|
| C17-C20, C25-C28 | Rubycon 35MU475KC44532, 4.7 uF 35 V PMLCAP | 1812 | C3778321 | ~$1.05 | 8269 |
| C57, C58, C86, C87 | Rubycon 25MU225MB23225, 2.2 uF 25 V PMLCAP | 1210 (3225) | C3778570 | ~$0.75 | 429 |

DigiKey and Mouser carry only the 16 V siblings (16MU475MC14532,
16MU225MB23225) at $7-11 each in ones, so the alternates are listed in the
BOM but the order should come from LCSC or PCBWay's own sourcing. Total
for the twelve: about $11.40. PPS (Panasonic ECH-U) tops out at 0.1 uF and
does not exist at these values in any SMD size; PMLCAP is the film option
that actually exists.

C86/C87 were kept as matched film rather than downgraded to X7R: TI wants
INP and INM balanced, and a DC-biased X7R next to a film part would not be.

## Check 2 residual, and why it is acceptable

The fourteen remaining parallel pairs are all same-layer, and the list is
now made of low-impedance nodes:

```
par_mm  gap_mm  aggressor    victim
11.3    0.171   ADC_BCLK     BRU_ADC
 9.5    0.899   ADC_BCLK     HP_INP_L
 6.1    0.522   ADC_BCLK     FLU_ADC
 5.6    0.241   DAC_BCLK     BRU_ADC
```

The `_ADC` nodes are the PCM1864 inputs behind the anti-alias network with
a 10 nF C0G to ground (C29-C32), which is about 1.3 ohms at 12 MHz; a few
picofarads of edge coupling into that is nothing. `HP_INP_L` is the
headphone amp's AC-grounded reference input through 2.2 uF. The
high-impedance nodes the audit was worried about (`_AC` at ~64 k, `_RAW`
behind the electret bias) do not appear in the list at all any more. The
ADC_LRCLK run under U7's input pads is on B.Cu with two solid planes above
it, so it is shielded in fact rather than in name.

## The two stragglers (and what a future rebuild has to know)

Freerouting left three items unrouted on the first two-layer pass and could
not finish them in a locked finishing pass either:

* **U10.12 (VDD)**: it had wrapped HP_OUT_L around the front of the pin.
  Fixed by hand: HP_OUT_L now runs through the 0.65 mm gap between C60's
  and C65's pads, the +5V feed that threaded through C60 was cut and
  re-joined to the B.Cu +5V through a via at (117.0, 53.64), and pin 12
  gets a 1.5 mm stub to C65. `fanout_decouple.py` now pre-places that stub.
* **U11.4 (BOOST_EN) and U11.5 (BOOST_SS)**: with In2 gone, the TPS61175's
  two control pins were fenced in on F.Cu by VBOOST_IN and on B.Cu by the
  CHASSIS run that walls off the whole left strip. C79 (the soft-start
  cap) moved to the bottom right under pin 5, which makes BOOST_SS a 5 mm
  net. BOOST_EN got escape vias, a run down the left edge on B.Cu at
  x=1.6, and two via hops over CHASSIS and +9V at y 62.5 / 63.0. All of it
  was placed by `tools/poly_route.py` with every segment and via checked
  against the geometry rules first, then confirmed by DRC.

If the board is ever regenerated and re-routed from scratch, expect the
same three to come back. `fanout_decouple.py` pre-places the U10.12 stub
and the U11 escape vias, and `tools/route_c3_stragglers.ps1` / `poly_route.py`
hold the hand routes; `rev_c3_status` in project memory has the sequence.

## Pipeline changes

```
generate_pcb -> preflight_pads -> fanout_decouple (NEW) -> fanout_gnd --allow-existing
-> protect_fanout -> patch_dsn_plane (In1+In2) -> freerouting -> import -> cleanup
-> fix_jumper_pads -> stitching -> finishing pass -> set_stackup (NEW) -> gnd_cluster_check -> DRC
```

Freerouting took 19 minutes on two layers (was ~4 on three). The locked
finishing pass hangs when a pin is physically fenced in, so kill it after
15 minutes and use the straggler tools instead.

## Still open / not done here

* U14's caps are 3.3 / 5.3 mm from the LDO. TPS7A20 is stable with that;
  tightening it is cosmetic.
* Series terminators (R46-R49/R69 for the ADC clocks, R57-R59 for the DAC)
  sit mid-run, not at the drivers. The clocks are 44-73 mm now; leave it
  unless the bench shows ringing.
* BRU_PRE / FRD_PRE are still ~80 mm because the preamp (U6, x=52) and the
  channel rows (y 85-104) are where they are. It is an op-amp output, so
  low impedance; not a crosstalk victim.
* No test points were added. If you want a probe hook on the clocks, a
  1.5 mm pad next to R46-R49 costs nothing; say so and it goes in the
  generator.
* The 3D fit viewer still predates Rev C2; no wall part moved in Rev C3.

## Addendum: the test-point rebuild (later on 2026-09-12)

Twelve 1.5 mm probe pads were added on the bottom (TP3-TP14: five ADC
clock/data lines, three DAC lines, +3V3_DC, three grounds; table in
`../connector-pinout.md`), which forced a full regenerate-and-reroute. Three
placement changes rode along:

* **U11 (TPS61175) rotated 180 deg.** At rot 0 the switch node had to wrap
  around the IC's north and east sides to reach L2, fencing pins 8-10
  (COMP/FB/FREQ) into a 0.86 mm corridor and pins 4/5 against the board edge.
  Freerouting could not finish BOOST_FB. Now SW/VBOOST_IN/EN/SS face L2 and
  the board; the left-edge BOOST_EN hand route and the escape vias are gone.
  C79 (soft start) sits on the bottom under L2, 2 mm from pin 5.
* **U13 (BQ24074) pins 6 and 8** (GND, either side of PGOOD_N) are tied into
  the exposed pad by stubs instead of getting their own fanout vias, which
  had boxed pin 7 in.
* **C38 deleted, U7.5 (MICBIAS) left open.** The capsules are biased from
  +9V_MIC, TI's PCM186x datasheet (9.3.2.1) says the pin can be left
  unconnected if unused, and on a 0.5 mm pitch between pins 4 and 6 it was
  unroutable. Firmware should power the bias down (page 3, reg 0x15, PDZ=0).

Result: ERC 0, DRC 0 / 0 unconnected / 0 parity, GND 174 pads in one
cluster, 8.83 m of track on two layers, 496 vias, fab package rebuilt (235
placements). Check 3 unchanged (all decouplers 1.34-1.60 mm). Check 2: still
zero broadside, but this route drew 22 same-layer pairs / 165 mm against
14 / 65 mm on the earlier board, the worst being ADC_DOUT2 beside BRU_ADC for
26 mm at 0.152 mm. Every victim is again an `_ADC` node (10 nF C0G to ground,
about 1.3 ohms at 12 MHz) or LINE_L (DAC output); 1.5 pF into 1.3 ohms is
about 0.5 mV of 12.288 MHz, which the modulator samples as DC. The number
moves from route to route because BRU_ADC and the clocks must both thread the
Teensy socket gaps to reach U7. If it matters later, a re-route is a coin
flip on this metric; a placement change (U7 rotated so its inputs face U6)
is the deterministic fix and is out of scope here.

## Addendum 2: mic modes and balanced inputs (later still on 2026-09-12)

Jason asked for the mic bias to be selectable from the touchscreen (off,
5 V or 9 V, one setting for all four channels) and, when it is off, for the
RJ45 pairs to behave as balanced inputs for dynamic microphones. Both went
into the same regenerate-and-route.

### Global bias switch

Q6 (AO3401A, +9V) and Q8 (AO3401A, +5V) are high-side switches into the
existing R67 / C66 bias filter, each driven by a 2N7002 level shifter (Q7,
Q9; 100R gate series, 100k pull-down) from Teensy pins 1 (MIC9_CTRL) and 0
(MIC5_CTRL). Both FETs are off until the firmware says otherwise. D24
(BAT54) sits between the 5 V leg and the filter so the 9 V setting can never
back-feed the +5V rail; the 5 V setting therefore delivers about 4.7 V,
which every electret capsule in the BOM is happy with. R104 (100k) bleeds
C66 down in about a second when the bias is switched off.

### Cold legs and the differential stage

J2 pins 2 / 6 / 5 / 8 were GND; they are now FLU/FRD/BLD/BRU_RAWC and carry
the same 100R / 100 pF C0G / PESD12VL1BA treatment as the hot legs (R110-113,
C97-100, D20-23). After the RF filter each cold leg (MICC) reaches a CD4053
section whose select pin is COLD_SEL: U4 and U5 had a spare C section each
(pins 3/4/9; pin 9 was grounded), U15 is a new CD4053 for the other two.
COLD_SEL is pulled to +9V by R106 (10k) so the power-up state is "cold leg
grounded" = electret mode; Q5 (2N7002, R107 100R, R108 100k) pulls it low
from Teensy pin 41 (COLD_CTRL) to release the cold legs.

The released cold leg goes through a 4u7 PMLCAP (C101-104) and 1M to VREF
(R114-117) into a new OPA1654 (U16, C109 100n), one unit per channel,
configured as the first amplifier of a two-op-amp instrumentation stage:
Ra = 10k 0.1 % (R118-121, CFB to CPRE), Rb = 90.9k 0.1 % (R122-125, CFB to
VREF), 22 pF across (C105-108). The second amplifier is the existing U6 unit;
its 10k (R26-29) now returns to the cold amplifier's output instead of VREF.
Net result Vout = (1 + 90.9k/10k) x (hot - cold), the same +20.1 dB the
single-ended stage had, so nothing downstream changes.

Numbers (hand calculation; superseded by the SPICE results in Addendum 3,
which found two things this ignored): worst-case CMRR with 0.1 % resistors
is 20 log(2 x 10.09 / 0.004) = 68 dB (the OPA1654's own CMRR is 120 dB); input-referred
noise with two 4.7 nV/sqrt(Hz) amplifiers and the 10k / 90.9k network is about
17.6 nV/sqrt(Hz), an EIN of about -110 dBu over 20 kHz, which is 3 dB worse
than the single-ended stage on the electret capsules (they sit 20 dB above
that anyway) and fine for a dynamic mic after +20 dB of PCM1864 PGA. The pad
(R18-R25 through U4/U5) stays on the hot leg only: engaging it in balanced
mode would unbalance the pair by 9.7 dB, so the firmware locks it out there.

### Layout changes forced by the route

* U10 (TPA6130A2) pin 3 (GND, between the two INM pins) is tied into the
  exposed pad by a stub instead of getting a fanout via 0.7 mm west of the
  pin row, which had fenced HP_INP_L/R in.
* C86 / C87 (the 2.2 uF INM caps) are rotated 180 deg so their signal pad
  faces U10, and C57 / C58 (the 2.2 uF input coupling caps) moved 1.2 mm
  east and apart (y 54.6 / 60.2): the gap between their U10-side pads is
  2.9 mm now, and both HP_INP_L and HP_INP_R fit through it. The old 0.7 mm
  gap took one track and left HP_INP_R unroutable.
* U11 (TPS61175) pins 6 and 7 (both GND) share one fanout via north-west of
  pin 7, and VBOOST_IN (pin 3 to L2 pad to C1), BOOST_SS (pin 5 via at
  13.6/30.9, B.Cu to C79) and BOOST_EN (pin 4 via at 14.25/31.5) are laid by
  hand in `fanout_decouple.py`. The router kept spending the 1.4 x 1.6 mm
  pocket east of the pin row on a VBOOST_IN detour plus a 0.8 mm via and
  left U11.5 unrouted.

New parts on the board: U15, U16, Q5-Q9, D20-D24, R98-R125, C97-C110. The
cold-leg parts sit on the bottom in columns at x 32..63 under the channel
rows; U16 is at (52, 61.5) next to U6, the bias switch block at x 26..41,
y 64..83 on the bottom.

### Result

ERC 0 / 0 / 0 (the CD4053's switch terminals are embedded as passive pins
now, so grounding a spare terminal no longer trips the bidirectional-vs-
power warning). DRC 0 violations / 0 unconnected / 0 parity. GND: 187 pads
in one cluster. 10.6 m of track on two layers, 531 vias (185 x 0.6/0.3,
346 x 0.8/0.4). Fab package rebuilt: BOM 97 lines, 287 placements (178
top, 109 bottom). Freerouting needed 5.5 minutes for the main pass this
time and the locked finishing pass ran (3.7 s) instead of hanging; the
hand-finished stragglers were BOOST_COMP/BOOST_FB (U11's west column, a
lane at x=2.4 and a via pair) and one VREF row-to-row link (an 18 mm F.Cu
run at x=57.2 east of the ATT/AC verticals, via at the BRU row).

Audits: check 3 unchanged (every decoupler 1.39-1.47 mm from its pin).
Check 2: still zero broadside pairs; 10 parallel same-layer pairs totalling
42 mm (previous board: 22 / 165 mm). The two worth knowing about are
ADC_LRCLK beside FRD_ADC for 11.8 mm at 0.16 mm on B.Cu near U7 (the
low-impedance 10 nF node again, and LRCLK is 192 kHz, so anything that
couples lands at DC after the modulator) and I2C_SCL/SDA beside FLU_PAD for
10.8 / 9.2 mm at 0.5 / 0.86 mm on F.Cu west of U4. I2C only toggles when a
setting changes (volume, mode), so the worst case is a faint tick on FLU
during a volume change; if the bench shows it, the deterministic fix is to
move the I2C pair to B.Cu past U4 (the bus runs from the Teensy socket to
J3/U7/U10 and has no reason to be on the top side there).

## Addendum 3: SPICE check of the balanced stage, and what it changed (2026-09-12, later)

The two-op-amp INA was simulated in ngspice 42 (`tools/spice/ina_sim.py`:
behavioural op-amps, 120 dB open loop, 18 MHz GBW, 4.5 nV/rtHz, infinite
CMRR so only the passive network is measured; 300 ohm dynamic mic, 150 ohm
per leg; 16 corners of +/-0.1 % on Ra/Rb/Rf/Rg). The hand-calculated "68 dB
worst case" in Addendum 2 was wrong for two reasons the calculation had
ignored.

**Finding 1, input impedance imbalance.** The 68k + 33k pad divider hangs on
the hot leg only, so the hot leg sees 1M || 101k = 92k while the cold leg
sees 1M. With any real source impedance that converts common mode to
differential ahead of the amplifier, and the 4.7 uF coupling caps then give
the two legs different high-pass corners (0.37 Hz vs 0.034 Hz) which adds a
phase mismatch at low frequency. Simulated CMRR as drawn: 35 dB at 20 Hz,
43 dB at 50 Hz, 50 dB at 1 kHz, regardless of resistor matching.
Fix: **R126-R129, 100k 1 % from each cold leg (ACC) to VREF**, which
balances the loading (90.9k vs 91.7k). Result: 67 dB worst case from 20 Hz
to 1 kHz with nominal caps; with the film caps at their +/-10 % limits the
low end drops to 48 dB at 20 Hz, 56 dB at 50 Hz, 61 dB at 100 Hz (the
corner mismatch again; a tighter cap tolerance or larger caps would buy it
back if the bench ever asks for it).

**Finding 2, high-frequency roll-off mismatch.** A2's 22 pF across Rf rolls
the hot path off at 80 kHz, but the non-inverting "+1" term of that stage
does not roll off, and with A1's 22 pF across Ra the cold path did not track
either: CMRR fell to 37 dB at 10 kHz and 31 dB at 20 kHz. The cold path
needs A1 = 1 + Rg(1/Rf + sCf), i.e. a zero, not a pole. Fix: **C105-C108
moved from across Ra (CPRE-CFB) to across Rb (CFB-VREF)**, same value.
Result: 62 dB at 10 kHz, 58 dB at 20 kHz worst case.

Unchanged by either fix: differential gain 20.06 dB, -3 dB at 71 kHz,
electret-mode (cold leg grounded) gain 20.05 dB, input-referred noise
18.8 nV/rtHz, 2.65 uV rms 20 Hz-20 kHz, EIN -109.3 dBu with 150 ohm per leg.

Both changes are in `generate_schematic.py` / `generate_pcb.py` (R126-R129
sit at x=50 in the bottom cold-leg columns) and the board was regenerated
and rerouted.

**Test points.** The audit after that route showed ADC_BCLK running 21 mm
beside FRD_ADC at minimum spacing: the five ADC clock/data probe pads at
x=124 were pulling those nets 40 mm east past the DAC and the headphone
caps. TP3-TP8 now sit in the empty bottom strip between U7 and its
terminators (y=36.5, x 81-98.5), so the probe stubs are a few millimetres
instead of forty, and the board was rerouted once more. Final numbers are in
the section below.

### Final state (board `revc3mic3`, 2026-09-12 11:15)

ERC 0 / 0 / 0. DRC 0 violations / 0 unconnected / 0 parity. GND 187 pads
in one cluster. 320 footprints, 291 placements (178 top, 113 bottom), BOM
97 lines. 10.6 m of track on two layers, 521 vias (182 x 0.6/0.3, 339 x
0.8/0.4). Fab package rebuilt.

Audits: check 3 unchanged (decouplers 1.34-1.60 mm). Check 2: zero
broadside pairs; 11 parallel same-layer pairs totalling 42.7 mm (the route
before the test-point move had drawn 21 pairs / 104 mm, with ADC_BCLK 21 mm
beside FRD_ADC). Worst now is ADC_LRCLK beside BLD_ADC for 8.6 mm at
0.15 mm on B.Cu near U7, then DAC_BCLK_IC beside BLD_ADC for 5.6 mm; all
victims are the 10 nF-terminated _ADC nodes as before. Segment pairs within
2 mm: 163 (was 410). The five ADC clock nets are 62-80 mm long (were
81-101 mm) now that their probe pads sit beside U7.

Sourcing was checked the same day against Mouser, DigiKey and LCSC:
`../manufacturing/BOM-SOURCING-CHECK-20260912.md`. One scarce part (U12
TPS7A4701RGWR, LCSC only), about twenty obsolete commodity MPNs with
substitutes listed, nothing blocking.

## Addendum 4: the scarce-part pass (2026-09-12, afternoon)

Jason asked for a non-scarce replacement for the 9 V analog LDO and for
any other thin part, plus the best price on everything. Three things
changed on the board, one in the parts list only.

### U12: TPS7A4701RGWR out, ADP7142AUJZ-R7 in

The TPS7A4701 (VQFN-20, 1 A, 4 uVrms) was the one part with no depth
anywhere: Mouser 0, DigiKey reel-only, LCSC a few dozen at $12. The +9V
rail it feeds carries roughly 25-40 mA (the four OPA1654 quads, the
TLE2426 splitter, the CD4053s and the mic bias), so a 1 A regulator was
never the point; the noise and PSRR were. The Analog Devices ADP7142
(TSOT-23-5, 200 mA, 11 uVrms, PSRR 88 dB at 10 kHz, 40 V input) is the
same class of part in a package every distributor stocks by the thousand
(Mouser 11k, LCSC 4.7k, about $3 either way).

Circuit: VIN and EN tied to +10V5, VOUT = 1.2 V x (1 + R130/R131) with
R130 = 130k, R131 = 20k -> 9.0 V; C83 2.2 uF X7R on the input, the
existing 10 uF on the output. No soft-start pin, so nothing else changed.
Placement: U12 at (9.5, 50.5) top, C83 at (5.5, 50.5), R130/R131 at
x=13.3 rotated 90 (rot 0 overlapped the TSOT courtyard). Thermal: 1.5 V
drop x 40 mA = 60 mW, 170 C/W -> about 10 C rise, fine.

### Q8/Q9 rotated 180

The first route with the new U12 fenced Q9's gate (MIC5_CTRL) on both
layers. Turning the 5 V bias pair (Q8 AO3401A, Q9 2N7002) 180 degrees
put the gate pad on the open side and the route closed.

### Two hand-routed stragglers

The route finished with two unconnected items, both fixed by hand
(`tools/fix_c3mic4_stragglers*.ps1`, every piece checked by
`poly_route.py` against the 0.16 mm rule before saving):

- **+3V3_A, C41.1 to C42.1 under U7.** The U7.26 GND fanout via sat in
  the only lane. U7.26 now ties to U7.25 with a 0.5 mm stub on F.Cu
  (U7.25 has its own via), and +3V3_A runs on B.Cu at y = 48.5 between
  the two GND pads. U7 keeps four ground pins, worst pad-to-via 1.26 mm.
- **CHASSIS, the BRU row (C16.2 / C100.2 / D23.2).** The island was
  boxed in on both layers by the BLD row's hot/cold pair (BLD_MIC on
  F.Cu, BLD_MICC + BLD_RAWC on B.Cu) to the north and the BRU pair
  (BRU_AC on F.Cu, BRU_MICC on B.Cu) to the east, with the 1812 film-cap
  pads (3.4 mm wide) closing the gaps. Fix: BLD_MICC's C99.1 -> C103.1
  run lifted from y = 98.56 to y = 98.1 (between C99's two pads), which
  opens a via slot at (41.0, 98.85); CHASSIS now goes C15.2 -> F.Cu along
  y = 97.325 between the C19 pads -> via -> B.Cu down x = 41.0 -> D23.2.
  BRU_MICC's feeder, which used to fence that lane at y = 101.745 and
  x = 40.541, hops over BRU_RAWC on F.Cu instead (vias at (34.5, 102.3)
  and (39.0, 105.3)). The island's own via moved from (38.409, 102.594)
  to (39.0, 103.35). Net topology is unchanged; the cold-leg pairs still
  run side by side.

### Parts-list refresh (no board change)

`passive_catalog.py` primaries were re-picked from a live Mouser + LCSC
sweep of every BOM line (`tools`-side script in the cloud session; results
in `../manufacturing/QuadPreRecorder-best-source-20260912.csv`). Dead
Murata "D"/"L" suffix MLCC numbers gave way to the in-stock Samsung /
Yageo / TDK / Taiyo Yuden parts that were already the alternates, and the
discrete MPNs that Mouser no longer lists (2N7002,215, BAT54,215,
SS14-13-F, 1206L200/12WR, the no-name LEDs) were replaced by
2N7002NXAKR, BAT54-7-F, onsemi SS14, 1206L200PR and Kingbright
WP7113QBC/D / WP7113ID. The schematic was regenerated so the BOM carries
the new numbers; ERC 0 / 0 / 0 and DRC parity 0 afterwards.

### Final state (board `revc3mic4`, 2026-09-12 15:00)

ERC 0 / 0 / 0. DRC 0 violations / 0 unconnected / 0 parity. GND 184 pads
in one cluster (three fewer than revc3mic3: the VQFN LDO's ground pins
and pad are gone). 322 footprints, 293 placements (180 top, 113 bottom),
BOM 97 lines. 10.3 m of track on two layers, 513 vias (182 x 0.6/0.3,
331 x 0.8/0.4). Fab package rebuilt (`QuadPreRecorder-RevC-PCBWay-handoff.zip`).

Audits: check 3 unchanged (decouplers 1.34-1.60 mm; U14's 3.3/5.3 mm
still the known exception). Check 2: zero broadside pairs; 12 parallel
same-layer pairs totalling 45.9 mm (was 11 / 42.7 mm). Worst is now
ADC_TDM_IC beside BRU_ADC for 9.9 mm at 0.15 mm on B.Cu near (83, 64),
then ADC_MCLK_IC beside BLD_ADC 8.1 mm at 0.30 mm; the victims are the
10 nF-terminated _ADC nodes as before, so this stays on the bench list
rather than forcing another route. Segment pairs within 2 mm: 270.

Backups: `hardware/QuadPreRecorder.kicad_pcb.revc3mic4-routed-clean-20260912`
and `.kicad_sch.revc3mic4-20260912`; the pre-hand-fix board is
`.revc3mic4-prefix-20260912`.

## Addendum 5: final pre-order check (2026-09-13)

Independent pass with the kicad-happy analyzers (schematic, PCB with
per-track detail, cross-domain, EMC pre-compliance with ngspice PDN
models, thermal, SPICE of 102 detected subcircuits, Gerber/drill) plus a
DRC run at every severity, not just errors, and a hand cross-check of the
BOM against the placement file. Verdict: **ready to upload**, after the
fixes below.

### Found and fixed

1. **The Gerber set had no inner layers.** `build_manufacturing.py` still
   exported the Rev C2 two-layer list (F.Cu, B.Cu, mask, paste, silk,
   edge), so every "4-layer" package since the 2026-09-08 stackup change
   carried a job file that said four layers and copper for two. PCBWay
   would have quoted a 2-layer board or bounced it. In1.Cu / In2.Cu are
   now exported; the job file lists Copper L1-L4 and the analyzer reads
   the planes back as one region each with 632 clearance flashes.
2. **Two stitching vias were drilled inside through-hole pads.** The
   stitching pass had dropped 0.4 mm GND vias on top of SW3's pad S2
   (76.0, 71.0 vs 76.0, 70.5) and beside SW2's pad 2 (0.04 mm hole-to-hole)
   - warnings only, so the error-level DRC gate never showed them. A drill
   inside a drill breaks out and can tear the barrel. Both removed; the
   SW pads are themselves GND so nothing is lost.
3. **U13 (BQ24074, 0.74 A charger) had no thermal vias** under its exposed
   pad, and U11 (TPS61175) had one. At 5 V in / 3.6 V battery the charger
   dissipates about 1 W in a 3 x 3 mm QFN; without vias to the planes it
   would sit in thermal fold-back and charge slowly. Two 0.3 mm vias now
   sit in U13's pad (the other three candidate spots landed on the
   VBUS_FUSED trace underneath and were rejected by DRC) and four more in
   U11's, all requested bottom-tented in the order notes.
4. **+3V3_A and CHASSIS hand routes re-seated.** The hand-routed segments
   from Addendum 4 ended 0.025 mm inside a pad edge and 0.0004 mm off a
   track end. KiCad counted them connected; the independent connectivity
   check did not. Both now land on pad centre / exact track end.
5. **Housekeeping:** In1/In2 typed as power layers in the board file (they
   were "signal", which the stackup checker took literally), a 6 um
   HP_OUT_L sliver deleted, TP1/TP2 (the two USB wire pads) taken out of
   the BOM on both schematic and board so PCBWay is not asked to source a
   pad.

### Checked and accepted (no change)

- **Buck input loop.** U1 (TPS62160, 2.25 MHz) has its 100 nF 6 mm and
  its 10 uF 10.5 mm from the VIN pins, pad to pad; the EMC pass sizes the
  hot loop at roughly 30-50 mm2 against a 25 mm2 target. It is the
  digital 5 V rail, 45 mm from the nearest preamp, inside a metal box.
  Rev D should pull C2/C3 against the pins; not worth a re-route now.
- **Op-amp decoupling.** U6/U16 (OPA1654) have their nearest 100 nF
  8.5-8.7 mm from pin 4 and the 10 uF bulk 8 mm away, on a 9 V LDO rail
  with two solid planes. Fine for 18 MHz audio op-amps; Rev D note.
- **Via-in-pad on the U7 decoupling caps** (8 x 0.3 mm vias in 0603 pads):
  accepted, tented on the far side; the notes tell PCBWay.
- **EMC pre-compliance score 0/100** is the tool's arithmetic on 18
  error-class findings, most of which do not apply: three "adjacent
  signal layer" errors from the layer typing (fixed), "harmonics" for U14
  which is an LDO, PDN anti-resonance at 250-320 MHz on audio rails, USB
  diff pair layer change on a 12 Mbit full-speed link that goes through a
  wire anyway, and "no filtering on J5" (headphone jack; TPA6130A2 output,
  no ferrites, the usual hobby-grade choice). Real items it raised: the
  U1 loop above, and the eleven clock nets on outer layers, which is
  inherent to a SIG/GND/GND/SIG stack.
- **Thermal 484 C on U12** is the analyzer assuming 4.5 V out at 0.3 A;
  the rail is 9 V at 25-40 mA, 60 mW, about +10 C.
- **Schematic analyzer**: 6 "errors" are all expected topology (diode-fed
  rails, the PCM1864 internal LDO pin, 3.3 V logic into 5 V-supplied I2C
  and enable pins that the TPA6130A2 datasheet allows); SPICE: 90 pass, 0
  fail, 12 skipped (VREF bulk cap, not a filter).
- **DRC warnings that remain:** 105 silkscreen overlaps and 98 silk-over-
  copper (reference text over pads; the export subtracts the mask so
  nothing prints on copper), 17 silk clipped at the edge (connector
  outlines over the wall), 199 "/NET vs NET" parity name warnings from
  the generated flat labels, 199 missing AltMPN footprint fields. All
  cosmetic.

### Package as uploaded

Board `revc3final` (backup `hardware/QuadPreRecorder.kicad_pcb.revc3final-20260913`).
ERC 0/0/0; DRC 0 violations / 0 unconnected / 0 parity at error level.
322 footprints, 293 placements (180 top, 113 bottom), BOM 95 lines, all
with MPNs, 5 DNP (R5, R38-R41). 517 vias: 188 x 0.6/0.3, 329 x 0.8/0.4.
Gerbers: 4 copper + mask/paste/silk both sides + edge, PTH/NPTH Excellon,
IPC-D-356 netlist, job file. BOM and CPL designators cross-check 1:1.

## Addendum 6 (2026-09-15): the Teensy 4.1 socket footprint was wrong; board re-routed

The in-depth review dossier (`hardware/reviews/QuadPreRecorder-RevC3-review-dossier.md`)
cross-checked every IC pinout against its datasheet and, last, the custom
`Teensy41_Socket` footprint against PJRC's Teensy 4.1 dimension drawing, the
PJRC pinout card and the XenGi `Teensy4.1` symbol (pins 1-48 numbered around
the module). The footprint, unchanged since Rev B and never built, had two
errors:

1. **Row spacing.** The two 1x24 socket rows were drawn 17.78 mm apart. The
   module's pin rows are 15.24 mm (0.6 in) apart on a 17.78 mm wide body
   (pins 1.27 mm in from each long edge). A real Teensy could not have been
   plugged in at all.
2. **Right-row order.** From the USB end the right row was drawn VIN, GND,
   23, 22 ... 13, 41 ... 33, GND, 3V3. The module is VIN, GND, **3.3V**,
   23 ... 13, **GND**, 41 ... 33. Twenty-two of the twenty-four right-row
   pads were therefore one position off: ADC_MCLK would have sat on the
   Teensy's 3.3 V pin, every right-side signal on its neighbour's pin, the
   NAV_PUSH pull-up on a GND pin, and the +3V3_D rail on I/O 33.

The left row (GND, 0 to 12, 3.3V, 24 to 32, square pad = GND next to pin 0)
was correct, so the schematic, netlist and BOM were unaffected. The
2026-09-13 PCBWay package is void.

### What changed

- `tools/generate_footprints.py`: rows 15.24 mm apart, right row
  VIN GND2 3V3B 23..13 GND3 41..33, outline 17.78 x 60.96 mm.
- `tools/generate_schematic.py`: the second 3.3 V pin (3V3B) is now a
  no-connect. Both 3.3 V pins are the same regulator output inside the
  module; the corrected position (USB end of the right row) has no +3V3_D
  copper within 25 mm, and one pin carries the rail's few milliamps of
  pull-ups easily. ERC 0/0/0 after the change.
- First attempt, abandoned: `tools/teensy_fix_stageA.py` patched the routed
  board in place and `tools/astar_route.py` (a grid router that checks every
  step with `stitch_pass3`'s geometry rules) closed the short escapes, but
  moving the right pin row 2.54 mm inward had swallowed the slot between the
  analog bus and the row that six long control lines (NAV_LEFT, NAV_ENC_A,
  REC_LED, GAIN_SW, LINE_MUTE, NAV_DOWN) used to reach the module. Neither
  the grid router nor two Freerouting passes with everything else exported
  `(type protect)` (`tools/finish_teensy*.ps1`, `tools/protect_except.py`,
  `tools/import_ses_into_current.py`) could close them without moving
  preamp routing. Those intermediate boards are kept as
  `QuadPreRecorder.kicad_pcb.teensyfix-*-20260915`.
- Done instead: a full re-route through the Rev C3 pipeline
  (`tools/launch_full_route.ps1` -> `full_route_body.ps1`: pristine board
  from `generate_pcb.py` with the corrected footprint library, pre-flight,
  decoupling and GND fanout, Freerouting 1.9 single-threaded, import, GND
  pours, stitching). Freerouting finished in under 3 minutes with nothing
  left over (the finishing-pass Freerouting instance then sat idle because
  it had no work; it was killed and the first route kept). Post passes as
  in Addendum 5 (`tools/post_teensy_reroute.ps1`, `post_teensy_reroute2.ps1`):
  U11/U13 exposed-pad thermal vias, In1/In2 typed power, TP1/TP2 out of the
  BOM, stitch pass 3 (nothing to rescue), four stitching vias that landed in
  the J10 / SW2 / U8 GND pad holes removed.

### Result

Board `revc3teensy-final` (backup
`hardware/QuadPreRecorder.kicad_pcb.revc3teensy-final-20260915`, raw route
`.revc3teensy-routed-raw-20260915`, pre-fix board
`.revc3final-preteensyfix-20260915`, schematic
`.kicad_sch.revc3final-preteensyfix-20260915`). ERC 0/0/0; DRC 0 violations,
0 unconnected, 0 parity at error level; at every severity the same 220
cosmetic warnings as before (105 silk_overlap, 98 silk_over_copper, 17
silk_edge_clearance) plus the 199 + 199 AltMPN / "/NET" name notes. GND: 184
pads, one cluster. 3050 segments, 523 vias (185 x 0.6/0.3, 338 x 0.8/0.4),
10.55 m of track. 322 footprints, 293 placements, BOM 95 lines.

Audits on the new route: check 1 unchanged (placement); check 2 zero
broadside pairs, 15 same-layer parallel clock/analog pairs totalling
34.9 mm (was 12 / 45.9 mm), worst I2C_SCL beside FRD_AC 7.4 mm at 0.48 mm
(an idle I2C line; bench item as before); check 3 analog copper 1766 mm
confined to x 1..86 / y 41..107, BRU_PRE 82.1 mm (was 82.7). Fab package
`QuadPreRecorder-RevC-PCBWay-handoff.zip` rebuilt 2026-09-15 with all four
copper layers; the 2026-09-13 zip is void.
