# Rev 3 (4-layer) — PCBWay order package

**Date:** 2026-08-01 (BOM MPN fix: 2026-08-23)
**Upload this:** `manufacturing/QuadPreRecorder-Rev3-4Layer-PCBWay-v2.zip`
**Board source:** `hardware/QuadPreRecorder_rev3_4layer_routed.kicad_pcb`

## 2026-08-23 — BOM MPN fix (PCBWay request)

PCBWay support (Aug 9) rejected the quote because the MPN column in the BOM
was blank on the generic-passive lines. Every BOM line now carries a specific,
verified, in-production manufacturer part number:

- **1% resistors** → Yageo RC0603FR-07 series (exact per-value MPNs).
- **0.1% precision resistors** (R18–R33 gain set) → Vishay TNPW0603...BEEA
  thin-film, 25 ppm/°C — confirmed in stock at Mouser.
- **MLCCs** → Samsung CL-series X7R/C0G (several legacy Murata GRM parts are
  now factory-obsolete), plus Murata GRM1885C1H103JA01D (10nF C0G),
  Murata GRM188Z71E225KE43D (2.2uF 0603), TDK C2012X7R1H684K125AB (680nF
  0805), Yageo CC0603KRX7R8BB684 (680nF 0603).
- **Electrolytics** → Panasonic EEE-FK1E101P (C1, 100uF 25V) and
  EEE-FK1C101P (C66, 100uF 16V), both low-ESR FK series.
- **J6/J7 debug headers** → Sullins PRPC013DAAN-RC (2x13, 2.54 mm, THT).

Two documented spec deviations (noted in the BOM Description column):

1. **C12** (1nF 1kV, 0805): specified C0G, supplied as **X7R**
   (KEMET C0805C102KDRACTU). 1 kV C0G is not manufactured in 0805 by anyone;
   X7R is the industry standard at this rating. EMI/chassis cap, not in the
   audio path.
2. **C10** (47uF 10V, 1206): specified X7R, supplied as **X5R**
   (Samsung CL31A476MPHNNNE, JLC basic part). X7R does not exist at
   47uF/1206; X5R is standard for bulk rail decoupling.

DNP alignment: the PCBWay-format BOM now matches the KiCad export —
**R5, R38–R41 are DNP** (do not populate).

The audio-critical constraints are unchanged: C0G stays C0G everywhere else,
and the 0.1% gain-set resistors remain 0.1% thin-film.

## Verification status

| Check | Result |
|---|---|
| Unconnected items | **0** |
| DRC errors | **0** |
| DRC warnings | 59 — 58 silkscreen (cosmetic), 1 dangling track stub |
| ERC | **0 violations** |
| Schematic parity | **clean** |
| Copper layers (from gerber job) | **4** — L1 Top / L2 In1 / L3 In2 / L4 Bot |
| Drill | 381 holes, 14 tool sizes, 0.30–3.25 mm |
| Placement | 180 components — 113 top, 67 bottom |
| BOM | 74 line items, **every line has a specific MPN** |

The one remaining warning is a 5.8 mm dangling tail on `HP_CPN`. It is
load-bearing — removing it splits the net — so it stays. Electrically it is a
short stub on the headphone charge-pump net and is harmless.

## Stackup

- **L1 F.Cu** — signal
- **L2 In1.Cu** — solid GND plane (unbroken)
- **L3 In2.Cu** — signal + GND pour
- **L4 B.Cu** — signal

Placement, board outline, Hammond 1590F fit and the Cat 6 jack (J2) are
unchanged from the mechanical work already validated.

## PCBWay order settings

| Setting | Value |
|---|---|
| Layers | **4** |
| Material | FR-4 |
| Board size | 138.15 × 114.15 mm |
| Thickness | 1.6 mm |
| Copper weight | 1 oz outer / 1 oz inner |
| Min track / clearance | 0.20 mm / 0.15 mm |
| Min via | 0.80 mm pad / 0.30 mm drill |
| Surface finish | HASL lead-free (or ENIG if you want flatter pads for the QFNs) |
| Solder mask / silkscreen | your choice |
| Assembly | **two-sided full SMT** |

**Do not use** `QuadPreRecorder-RevA-PCBWay-handoff.zip`, the 2-layer
`rev3-gerbers`, or the original `QuadPreRecorder-Rev3-4Layer-PCBWay.zip`
(blank MPNs) — all predate the v2 package.

## Flag on the order

`EC11E15244G1` (gain encoder) was 0-stock at Mouser. Let PCBWay source it, or
approve an EC11E-family substitute with the same footprint.

## Two things to confirm with PCBWay

1. **Stackup.** The gerbers declare 4 copper layers but not layer thicknesses —
   PCBWay will apply their standard 1.6 mm 4-layer stackup. That is fine here;
   nothing in this design is impedance-controlled.
2. **Mixed plating.** The drill file is tagged `MixedPlating,1,4` (all holes
   plated through, no blind/buried vias). Standard 4-layer process.

## Fixed during this pass

A pre-existing fabrication hazard was found and removed: a 0.30 mm via had been
placed **inside** J7 pad 23's 1.00 mm drill hole (same net, so the via was
redundant — the through-hole pad already connects all layers). Overlapping
drills risk drill breakage and would likely have been queried by the fab.

Three GND stitching vias were added at (70.85, 48.70), (69.40, 47.00) and
(67.55, 49.55), tying U7's ground pins to the In1 plane — one of them sits
0.20 mm from U7 pin 26. This replaces a GND trace that had to be cut to free the
ADC's pin escapes, and is a lower-impedance ground than the trace it replaces.
