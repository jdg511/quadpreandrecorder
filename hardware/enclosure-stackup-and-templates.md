# Hammond 1590F stackup study and drill templates — Rev A

**SUPERSEDED 2026-09-06.** The target enclosure changed from the Hammond 1590F to the compact Hammond 1590XX (Rev B), and the board outline changed from 174 x 174 mm to 138 x 114 mm with an entirely different wall layout (see `mechanical.md` and `enclosure-fit-audit.md` for the current Rev B placement). Everything below is a real physical stackup study done against an actual Hammond 1590F box and its drill templates — none of these measurements, corrections, or the companion PDF apply to the 1590XX. They are kept here only as a record of the method used, and as a reminder that a new stackup study against a real 1590XX box (with new drill templates) is required before drilling anything for Rev B. Do not use the `QuadPreRecorder-1590F-drill-templates.pdf` file for the current board.

---

## Original 1590F study (historical, retired 2026-09-06)

Date: 2026-07-25 (templates Rev 2, post-reroute). Companion file:
`QuadPreRecorder-1590F-drill-templates.pdf` (four 1:1 pages: left wall, right
wall, bottom wall, lid).

**TEMPLATES REV 2 — IMPORTANT.** Rev 1 of the PDF placed several wall features
on their footprint *anchor* (pin 1) instead of the true bushing/shell center,
and drew the bottom wall un-mirrored. Discard any Rev 1 prints. Corrections,
measured from the routed board's fab geometry: J2 DE-9 shell center 61.46 (was
67.0) — **NOTE: this is the OLD D-sub footprint; J2 is being replaced with an
Amphenol RJHSE-5380 shielded RJ45/CAT6 jack per the schematic, so this entire
J2 measurement is void until the PCB is regenerated with the new footprint and
re-measured against the RJHSE-5380's real shell geometry.** J6/J7 DB-25 shell
centers 138.38/48.38 (were 155/65 — 16.6 mm off),
RV1 shaft 164.5 (was 162.0), J4 bushing axis at board X 132.23 (was drawn at
the pad column, 7.2 mm off). The bottom wall now also carries J1 (9 V power,
moved off the left wall), and the left wall carries SW1, the pad toggle. The
lid pad-slide slot is gone.

**TEMPLATES REV 3 (2026-07-25, later the same day).** The record button (SW2)
and gain encoder (SW3) moved from the board's north edge to a control row
directly BELOW the TFT, and a new **SW4 ALPS SKQUCAA010 5-way navigation
switch** (TFT menus, Teensy pins 36–40) joined the row. Lid page 4 is redrawn
with true actuator centers measured from the routed board — Rev 2's lid page
had drawn SW2/SW3 on their footprint anchors (~6–7 mm off). Lid centers are
now: SW2 record (63.25, 95.5), SW3 gain (82.5, 95.5), SW4 nav (114.0, 95.5),
all Ø as printed. SW4's stem tops out ~6.5 mm below the lid; the plan of
record is a ~6.5 mm glued/3D-printed extension cap on its 3.2 mm square stem
(same reach-fix philosophy as the B3F-5150). Walls (pages 1–3) are unchanged.

**TEMPLATES REV 4 — external microSD access (no PCB change).** The recorder
writes to the Teensy 4.1's own card slot, which is buried under the board.
Plan of record: an **Adafruit 6070 round panel-mount microSD extender**
(~$9.50) — its 18 cm flex plugs into the Teensy's slot and its threaded
socket mounts through the **bottom wall at template u = 96.0, 34.0 mm below
the rim** (below the board, between J1 and J4). The 6070 accepts panels up to
16 mm; the wall is ~7.8 mm there. The template marks a pilot cross with a
NOMINAL Ø25 dashed circle — measure the real barrel before final drilling.
Two firmware notes: (1) cap the SDIO clock in SdFat if the extender is
marginal at full speed — even half speed leaves ~4x margin over the
3.07 MB/s recording budget; (2) card swaps are not hot-detected through the
extender, so re-mount the card from a menu action or on record-arm. Add the
6070 to the order list as an off-board part (it is not on the PCB BOM).

This is the desk-study half of the "physical enclosure stackup check" required
by `requirements.md` and `enclosure-fit-audit.md`. It uses the official Hammond
1590F drawing, the MSP2834 factory drawing, and manufacturer drawings for every
panel part. It does NOT replace holding the real box: the checklist at the end
still requires physical confirmation before drilling or ordering.

## 1. Enclosure facts (Hammond 1590F drawing, hammfg.com)

- Outer 188.0 x 188.0 mm, assembled height 67.0 (body 63.0 + lid stack 4.0).
- Floor thickness 2.5. Inside depth floor-to-rim ~60.5; floor-to-lid-underside
  62.0 (the lid underside sits ~1.5 above the rim plane).
- The cavity is heavily drafted: 178.5 sq at the rim tapering to 167.43 sq at
  the floor (~0.09 mm per side per mm of depth). Wall is ~4.75 thick at the rim
  and thickens toward the floor.
- 8 lid screws (6-32 UNC), centers 5.0 mm in from the outer edges (4 corners +
  4 mid-sides). They thread into bosses that intrude into the cavity; at the
  mouth the mid-side bosses narrow the opening to ~172.03 mm. Boss depth is not
  dimensioned by Hammond — measure it on the real box.

## 2. Where the 174.0 mm board can sit

Cavity width vs depth d below the rim: `W(d) = 178.5 − 0.183·d`.

| Side clearance | Max board-top depth |
|---|---|
| 0 (touching) | 24.6 mm |
| 0.25 mm | 21.9 mm |
| 0.50 mm | 19.1 mm |

So the board lives only in the top ~20 mm of the box. **Boss interference:**
the board (174.0) is wider than the mid-side boss opening (~172.03) and its
corners fall inside the corner-boss radius, so wherever bosses exist at board
depth the board needs four mid-side notches (~12 x 2 mm) and four corner
notches (~R6), OR the board must sit below the bosses. Measure how far the
bosses extend down; a 1/2-inch lid screw needs roughly 8–12 mm of boss.

## 3. Recommended stackup (board top 15.0 mm below the rim)

- Cavity width at board level 175.76 → 0.88 mm clearance per side.
- Board-top to lid-underside gap: **16.5 mm**.
- Floor standoffs under H1–H4: **43.9 mm** (stack spacers; H1–H4 land on the
  floor with ~3.7 mm margin to the sloped wall).
- TFT module standoffs (module-PCB underside above main-board top): **10.6 mm**
  puts the touch lens flush with the lid underside; window cut in the lid.
- If you change the 15.0 depth, every wall-template depth shifts by the same
  amount — the templates say this on each page.

Reach vs the lid underside (16.5 above the board):

| Part | Height above board | Result |
|---|---|---|
| SW3 EC11E encoder shaft tip | 24.5 | +8.0 through the lid — good for a knob (Ø8 hole; plain bushing, no nut) |
| SW3 bushing top | 11.5 | stays 5.0 below the lid — only the shaft penetrates |
| SW2 B3F-4050 plunger | 7.3 | **9.2 mm short — cannot be pressed** (finding C — RESOLVED: BOM is now B3F-5150, 17.5 mm plunger, ~1 mm into the Ø9 lid hole) |
| SW1 OS102011 slide actuator | 7.5 | **9.0 mm short — cannot be reached** (finding D — RESOLVED: SW1 is now an E-Switch 100SP1T1B1M7 toggle through the LEFT WALL, not the lid) |
| TFT lens on 10.6 standoffs | 16.5 | flush with lid underside |
| SW4 SKQUCAA010 nav stem tip | 10.0 | 6.5 short of the lid — fit a ~6.5 mm stem-extension cap through the Ø8 lid hole (Rev 3) |

## 4. Findings that needed action BEFORE ordering the PCB — ALL RESOLVED 2026-07-25

Status: **A, B, C and D are all fixed in the generators, the BOM, and the
rerouted board** (DRC clean, panel-orientation checker 8/8). The original
findings are kept below for the record; E and F remain bench checks.

**A (RESOLVED — H5–H8 now at 76.08 x 44.0 on the routed board).** The MSP2834 factory
drawing (QDtech V1.0) gives the module hole pattern as **76.08 x 44.0 mm**,
Ø3.2, with the pattern NOT vertically symmetric on the module (top holes 3.0
from the top edge, bottom holes 6.92 from the bottom edge). The board's H5–H8
are at **78 x 42** — off by ~1.9/2.0 mm, more than the screw slack. Move H5–H8
(and re-check J3's position/wiring to the module header) before ordering.

**B (SUPERSEDED — J2 is no longer a DE-9 at all).** This EU-vs-US DE-9 part-number
question (LD09S13A4GV00LF vs LD09S33E4GV00LF) is now moot: J2 has been changed to
a shielded 8P8C RJ45/CAT6 jack, Amphenol RJHSE-5380, per the schematic. The PCB
still has the old DSUB-9 footprint routed and must be regenerated with the
RJHSE-5380 footprint before ordering; new drill-template measurements for J2 are
needed once that's done, since the RJ45 jack's shell size/protrusion differs from
the D-sub.

**C (RESOLVED — BOM is now Omron B3F-5150).** The B3F-4050 plunger tops out
7.3 mm above the board against a 16.5 mm gap. Cleanest fix: swap SW2 to a
tall-plunger 12 mm switch in the same B3F family — **B3F-5150 (17.5 mm)** pokes
~1 mm into the Ø9 lid hole; add a keycap. Same footprint, no PCB change.

**D (RESOLVED — SW1 is now an E-Switch 100SP1T1B1M7REH right-angle toggle
through the left wall at board Y 96, with a custom project footprint; the lid
slot is deleted from the templates).** The old slide could not reach (7.5 vs 16.5 mm). Options:
treat the pad as a set-and-forget internal switch (open the lid to change it);
replace with a panel-mount mini toggle flown to the SW1 pads; or respin with a
tall-actuator slide. The lid template marks the slot DO-NOT-CUT.

**E. Board outline vs bosses** — see section 2; possible notches (PCB change if
the real box's bosses reach board depth).

**F. J3-to-module interconnect.** J3 is a male pin header and the MSP2834
ships with a male header (11.17 mm, on the module's back). Two males don't
mate, and at the 10.6 mm TFT standoff a soldered module header would collide
with the main board (−0.57 mm). Plan the interconnect explicitly: either fit
the module unpopulated and solder it onto J3's pins, or put a 14-pin female
socket on the board and check the mated stack height against 10.6 mm.

## 5. Findings to verify at the bench (no PCB change expected)

- **J4 nut engagement:** NRJ6HF bushing 8.9 long vs ~6.9 wall → ~2 mm of
  thread. Spot-face the wall outside ~1 mm if the nut won't seat, or run
  nutless (PCB-anchored).
- **D-sub shells:** mating shell projects 6.17 forward of the flange; with a
  ~5.5 mm wall the shells end near-flush with the outer face. Confirm cable
  plugs seat and jackscrews reach (2x Ø4 clearance holes are on the templates).
- **Barrel/phone jack recess:** J1 nose ends ~2 mm inside the wall — check the
  9 V plug seats; J5 nose ends ~1.5 mm inside — check headphone plugs seat.
- **RV1:** M7 bushing (5 mm) stays inside the wall — no nut, PCB-anchored;
  ~7 mm of shaft protrudes for the knob (Ø8 hole).

## 6. Physical checklist before drilling (with the real box in hand)

1. Verify the 100 mm calibration bar on every printed template page.
2. Measure boss depth below the rim at a corner and a mid-side; confirm the
   bare board drops to 15 mm depth without touching (notch if not).
3. Confirm rim-to-lid-underside offset (~1.5 mm) with the lid held on.
4. Dry-fit the bare PCB at depth; transfer any deviation to all wall depths.
5. Compare the purchased MSP2834 against the drawing (holes 76.08 x 44, lens
   69.2 x 50, thickness 5.9) before cutting the lid window.
6. Drill pilot holes first; open to final size only after re-checking against
   the assembled board.
