# Enclosure fit recheck, Rev C2 — 2026-09-11

Every part that penetrates a wall or the lid, measured off the routed board
rather than the hand-entered figures in `enclosure-1590XX-desk-study.md`, and
checked against real manufacturer drawings.

## The datum everything hangs off

From Hammond's STEP (see [[enclosure-fit-findings]]): cavity 139 x 115 at the
floor opening out to 140.7 x 116.7 at the rim over 33.15 mm. The board is
138 x 114 and sits 19.5-20 mm above the floor.

At that height the cavity is **140.0 mm wide**, so:

| | |
|---|---|
| board edge to INNER wall face | **1.00 mm** |
| wall thickness at board height | **2.60 mm** |
| **board edge to OUTER wall face** | **3.60 mm** |
| board top to LID UNDERSIDE | **15.50 mm** |
| board top to OUTER LID FACE | **17.50 mm** |

Positions below are board coordinates, read from `QuadPreRecorder.kicad_pcb`
by `tools/penetration_audit.py` and `tools/max_outward_move.py`.

## Verdict table

| Ref | What | Measured | Verdict |
|---|---|---|---|
| J1 | 9 V barrel, rear | mouth 5.50 mm past the board edge = **1.90 mm proud** of the outer wall | **FITS** |
| J2 | RJ45, left | face 4.25 mm past the edge = **0.65 mm proud** | **FITS** (see cutout note) |
| J4 | 1/4 in jack, front | nose 8.90 mm past the edge = **5.30 mm proud** | **FITS, but the nut does not** |
| J5 | 3.5 mm jack, right | nose 1.20 mm past the edge = **2.40 mm RECESSED** | **RISKY** |
| J9 | USB-C, rear | face 0.55 mm inside the edge = **4.15 mm RECESSED** | **FAILS** |
| SW2 | record button, lid | 7.3 mm vs 15.5 mm needed | **FAILS** |
| SW3 | gain encoder, lid | **24.5 mm** total = 7.0 mm of D-shaft proud | **FITS** (old study was wrong) |
| SW4 | 5-way nav encoder, lid | **17.4 mm** total, tip 0.1 mm below the outer lid face | **FAILS for a knob** |
| J3 | TFT lens, lid | 16.4-16.9 mm = 0.9-1.4 mm into the 2 mm lid window | **FITS** |
| D4/D5 | indicator LEDs, lid | 0603 flat on the board, 15.5 mm below the lid | **FAILS** (never solved) |
| U8 | Teensy microSD, rear | card plane ~9-10 mm below the board underside | needs a rear slot, unchanged |

## 1. J9 USB-C — the serious one

The receptacle's mating face sits 0.55 mm INSIDE the rear board edge, so it is
**4.15 mm behind the outer wall face**. A USB-C plug shell is ~6.5 mm long and
the receptacle cavity is 6.20 mm deep, so the shell has to travel 4.15 + 6.20 =
**10.35 mm** from the outer face. It only has 6.5 mm. **A cable cannot seat.**

Moving it out does not fix it on its own: the binding constraint is the
connector's own through-hole shield tabs (SH pads at y = 3.15, ø0.60 drill),
which allow a maximum outward move of **2.05 mm** before they run out of edge
clearance. That puts the face 2.10 mm behind the outer face — still short.

**Fix (verified, no collisions): move J9 -2.05 mm in y AND open the rear-wall
cutout to about 13 x 7.5 mm** instead of the 9.5 x 4.0 in the old study.
With the face 2.10 mm in, the shell needs 8.30 mm of travel, is 6.5 mm long,
so the plug's overmold (~12.4 x 6.65 mm) must enter **1.80 mm**. The wall is
2.60 mm thick, so it fits with 0.8 mm to spare.

If a big rectangular hole is unacceptable cosmetically, the alternative is a
panel-mount USB-C on a short pigtail to a header, which decouples the port
from the board entirely.

## 2. SW2 record button — no Omron fix exists

B3F-5150 is **7.3 mm** and that is the tallest 12 mm B3F Omron makes. The
tallest cap, B32-16x0, adds 4.2 mm for **11.5 mm total** — still 4.0 mm short
of the lid underside. The Omron family cannot reach; it has to be replaced.

The part must land 15-17 mm above the board. Options, cheapest first:

| Part | Mfr | Height | Life | Stock | Price 1/100 |
|---|---|---|---|---|---|
| **TS02-66-150-BK-160-LCR-D** | Same Sky | **15.0 mm** | 80 k | 3,418 Mouser | $0.13 / $0.097 |
| TL1105YF160Q | E-Switch | 16.3 mm | - | 33,463 Mouser | $0.31 / $0.234 |
| SKHHDHA010 | Alps Alpine | 17.0 mm | **500 k** | 1,958 Mouser | $0.35 |
| KH-6X6X17H-TJ | Kinghelm | 17.0 mm | - | 18,463 LCSC | $0.025 |
| 5ETH935 + 1SS09-16.0 | APEM/MEC | 16.0 mm | 10 M, IP67 | in stock | ~$3.70 |

All of the 6 x 6 parts share the standard 4-pin 6.5 x 4.5 mm grid on ø1.0 mm
holes, which is KiCad's `Button_Switch_THT:SW_PUSH_6mm` — one footprint covers
every height, so the choice can change late.

**Recommended: Same Sky TS02-66-150-BK-160-LCR-D.** Named manufacturer with a
real datasheet, 15.0 mm leaves 0.5 mm of over-travel under the lid, and it is
1/38th the cost of the APEM combination.

**Verified placement:** footprint `SW_PUSH_6mm` anchored at **(43.75, 71.25)**
puts the plunger at exactly **(47.00, 73.50)**, on the existing control-row
line with SW3 and SW4, and collides with nothing.

**Do guide the stem through the lid hole** (drill ~ø3.6-3.8 mm). A 15 mm stem
on four 1 mm pins is a lever; let the lid take the side load, not the solder
joints. That is the only thing the expensive APEM part really buys you.

## 3. SW3 gain encoder — a false alarm, it was always fine

The old study said the shaft ends ~2.5 mm outside the lid and was "too short
for a knob set-screw", and recommended buying a 25 or 30 mm variant.
**That was wrong and no part change is needed.**

`EC11E15244G1` is **24.5 mm above the PCB seating plane** (body 4.5 + boss 7 +
shaft 13), which leaves **7.0 mm of shaft proud of the outer lid face**. The
shaft is ø6 mm with a single flat, 4.5 mm across the flat, and the flat starts
14.5 mm above the board — 1 mm below the lid underside — so the whole exposed
7 mm is D-flatted. Any 6 mm D-bore or set-screw knob fits.

The "H20mm" in the KiCad footprint name is Alps' *actuator length* column, not
a height above the board. That is where the bad number came from.

## 4. SW4 nav encoder — fits the hole, but there is nothing to hold

Total height **17.4 mm**, so the shaft tip finishes **0.1 mm below the outer
lid face**. It fills the hole and stops. The shaft is ø2.5 mm with a 1.8 mm
flat and only ~6.9 mm of it stands above the body.

There is no taller variant. **RKJXT1F42002 does not exist** — checked against
Alps' product page, the Alps multi-control catalog, the RKJXT datasheet,
Mouser, DigiKey, LCSC and Octopart. It has been removed from the BOM, where
this file previously listed it as an alternate. Alps publishes no knob for
this part either; no catalogue knob goes below a ø3 mm bore.

**Fix: a custom cap.** ø2.5 mm bore with a 1.8 mm flat, ~5 mm of engagement on
the shaft, a disc or dome top 8-10 mm across standing 2-4 mm proud. 3D printed
is fine. That restores all three functions — tilt, press and twist — because
twisting the cap twists the shaft.

**Lid hole ~ø5.5 mm.** The lever tilts 9 degrees about the top of the body, so
at the lid (7 mm of lever arm) the shaft sweeps 7 x sin(9 deg) = 1.10 mm each
way. ø2.5 + 2 x 1.10 + clearance.

Worth noting: SW4's rotary ring duplicates SW3's, so even if the cap is only
ever used as a thumb pad, no function is lost.

## 5. J5 3.5 mm headphone jack — recessed, and it is not a panel part

The nose tip sits **2.40 mm behind the outer wall face**, so a plug gives away
2.4 mm of its travel before it even reaches the jack. The SJ1-3533NG has no
thread and no bushing — Same Sky does not list it as panel-mountable — so
there is nothing to clamp and nothing to take the insertion force but the
solder joints.

This is the classic cause of a plug that clicks into its detent but lands the
tip contact on the wrong conductor: intermittent, mono, or swapped channels,
and it varies by plug brand because moulded consumer plugs have fatter,
more sharply stepped handles than a slim Neutrik/Rean barrel.

**Fix (verified, no collisions): move J5 +2.40 mm in x.** The nose then
finishes flush with the outer wall face. Its binding pad allows up to 3.30 mm,
so there is margin. Wall hole ø6.5-7.0 mm to clear the ø6.00 mm nose.

## 6. J4 1/4 in jack — the jack fits, the nut does not

The nose stands 5.30 mm proud of the outer wall, which is plenty of 3/8-32
thread for a nut. The problem is what the nut has to clamp.

The bushing shoulder sits at the board edge, and from there to the outer wall
face is 1.00 mm of air plus 2.60 mm of wall = **3.60 mm**. Neutrik specifies
a **maximum panel thickness of < 3.0 mm**. Tightening a nut on that stack
either exceeds the spec or pulls the jack outward against its solder joints.

**Fix (verified, no collisions): move J4 +1.00 mm in y.** The bushing shoulder
then seats against the inner wall face and the nut clamps only the 2.60 mm
wall, inside spec, with the wall properly carrying plug insertion force
instead of the PCB. Its binding pad allows 2.50 mm, so 1.00 mm is safe.

Also note: **the nut is not supplied.** Order one — NRJ-NUT-B (plastic hex),
NRJ-NUT-MK (knurled ring), NRJ-NUT-MS (ring) or NRJ-NUT-MN (metal hex).
Panel hole is 11.2 mm per Neutrik, though that does not reconcile with a
3/8-32 thread (9.53 mm major) and is worth confirming before drilling.

## 7. D4/D5 indicator LEDs — never solved, and 0603 cannot be made to work

Two 0603 top-firing chip LEDs lie flat on the board 15.5 mm below the lid with
nothing between them and it. As drawn they are invisible from outside. There
is no mention of light pipes anywhere in the design.

**0603 is too small to couple into any light pipe long enough to cross the
gap.** Every rigid board-mount pipe in that length class is specified for a
PLCC-2 class emitter: VCC VBL wants 3.0 x 3.0 x 2.0 mm, Dialight 515 VBM wants
PLCC-2/PLCC-4, Bivar LPV3 has a 3.8 mm square window. Feeding a 3 mm entrance
face from a 1.3 mm2 emitter over 15 mm of polycarbonate gives a dim dot.

Three honest options, none free:

1. **3 mm THT LEDs in Bivar LTM-600 spacers (15.24 mm).** Cheapest optically
   and mechanically; the spacer uses the LED's own two lead holes so no extra
   mounting holes are needed. Lid drilled ~ø3.6 mm. LTM-600 was 0 stock at
   Mouser on 2026-09-11; LTM-500 (12.7 mm) is 5,365 in stock.
2. **Stay SMD: PLCC-2 LEDs + VCC VBL3D0700C (17.78 mm, $0.51/100).** Keeps the
   board reflow-only. Requires changing both LED footprints AND adding the
   pipe's press-fit holes.
3. **Move the indicators to the front wall** alongside J4, using right-angle
   THT LEDs. Avoids the lid entirely.

**All three need local re-placement.** D4/D5 sit in a tight cluster with R37,
R54, R55 and C28; a 3 mm THT LED at either position overlaps its own series
resistor. This is a small placement job plus a re-route, not a drop-in.

## 8. Build-sequence issue worth thinking about before drilling

Five of the six wall connectors protrude past the board edge by more than the
1.00 mm of clearance to the inner wall: J4 by 8.90, J1 by 5.50, J2 by 4.25,
J5 by 1.20 (2.40 after the fix above), J9 by 1.50 after its fix. That means
**the board cannot be lowered straight down into the box** with closed holes on
four walls — the connectors have to pass through as it descends.

The usual answers are to file the tall cutouts open to the rim on one wall, or
to make them generous and tilt the board in. Worth settling before any metal
is cut, because it changes how the holes are shaped.

## Change list

Board changes, all verified collision-free against the routed board:

| Ref | Change |
|---|---|
| J9 | move -2.05 mm in y; rear cutout becomes ~13 x 7.5 mm |
| J5 | move +2.40 mm in x |
| J4 | move +1.00 mm in y |
| SW2 | footprint 12 mm -> `Button_Switch_THT:SW_PUSH_6mm`, anchor (43.75, 71.25); part -> Same Sky TS02-66-150-BK-160-LCR-D |
| D4/D5 | LED package change plus local re-placement of R37/R54/R55/C28 |

No change: J1, J2, SW3, SW4 (part), J3.

Buy list additions: a Neutrik NRJ-NUT-x, a custom cap for SW4, LED spacers or
pipes, and the new SW2.

Lid drilling: SW2 ~ø3.6-3.8, SW4 ~ø5.5, SW3 per the knob, LEDs per the option
chosen. The J4 front-wall X in the desk study predates the Rev C2 move and
must be re-measured.
