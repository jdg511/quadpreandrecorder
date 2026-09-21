# PCBWay handoff — QuadPreRecorder Rev B (Hammond 1590XX)

Package regenerated 2026-09-06 from the fully routed Rev B board with
`tools/build_manufacturing.py` (KiCad 10.0.4 CLI). ERC: 0 errors / 0
warnings. DRC (`--all-track-errors --schematic-parity --severity-error`):
**0 violations, 0 unconnected pads, 0 schematic-parity issues.** J2 is the
Amphenol RJHSE-5380 shielded RJ45/CAT6 mic jack in the BOM, CPL and copper.

What is still a **human** check before you click order — the board has
never been test-fitted in a real 1590XX box (see the "Before ordering"
list at the end of this file).

## Order configuration

| Setting | Value |
|---|---|
| Board size | 138.0 x 114.0 mm, 12 mm corner chamfers (Hammond 1590XX max PCB envelope) |
| Layers | 2 |
| Material | FR-4 |
| Finished thickness | 1.6 mm |
| Copper | 1 oz outer layers |
| Minimum track / clearance (actual) | 0.20 mm / 0.15 mm — PCBWay standard floor is 0.10 / 0.10 |
| Minimum via (actual) | 0.80 mm pad / 0.40 mm drill (0.20 mm annular) — PCBWay floor 0.30 / 0.15 / 0.15 |
| Copper-to-edge | ≥ 0.65 mm (rule-area keepouts; PCBWay asks ≥ 0.30 mm) |
| Surface finish | Lead-free HASL for lowest cost; ENIG is an acceptable upgrade |
| Solder mask / silkscreen | Green / white |
| Assembly | Two-sided mixed SMT and through-hole: 175 placements (112 top, 63 bottom) |
| Stencil | Both sides — U8 (Teensy 4.1) and the bottom-side passives are on the back |

Upload `QuadPreRecorder-RevB-Gerbers.zip` as the PCB file (or the full
`QuadPreRecorder-RevB-PCBWay-handoff.zip`). Upload `QuadPreRecorder-BOM.csv`
and `QuadPreRecorder-CPL-PCBWay.csv` to the assembly quote, and attach
`QuadPreRecorder-BOM-extras.csv` (the U8 socket sub-assembly plus the loose
off-board parts you want PCBWay to quote and ship with the boards).
`PCBWAY-ORDER-NOTES-REVB.txt` has the paste-ready order text.

The Gerber archive includes top/bottom paste layers, an IPC-D-356 electrical
netlist, Excellon PTH/NPTH drills with maps, and the job file. Three 1 mm
global fiducials are present on each assembly side and intentionally omitted
from the BOM/CPL. Placement CSVs use KiCad's coordinate convention (Y grows
downward, so "Mid Y" is negative) — PCBWay's importer handles this; confirm
the placement preview during quoting.

## Assembly instructions

- `R5` is DNP (do not populate). It is the optional direct CHASSIS-to-GND link.
- `R38`-`R41` are DNP.
- `U8` (Teensy 4.1) is on the bottom. `J4` (6.35 mm line jack) is on the
  **top** side at the front wall (Rev B change; Rev A had it on the bottom).
- `U8` is a **socketed sub-assembly** (decided 2026-09-06, see
  `QuadPreRecorder-BOM-extras.csv`): PCBWay solders two Samtec
  **SLW-124-01-G-S** low-profile 1x24 sockets into the U8 footprint (bottom
  side, rows 17.78 mm apart), then plugs a PJRC **TEENSY41_PINS** (Teensy 4.1
  with the outer 2x24 pins pre-soldered) into them. The CPL lists U8 once at
  the module's position. The Teensy is customer-supplied if PCBWay cannot
  source PJRC parts. Its microSD slot must face the rear wall (Y=0 edge) —
  the silkscreen says "SD CARD SLOT THIS EDGE".
- `J3` is only the 1x14, 2.54 mm display header. The target module is the
  LCDWiki MSP3520 3.5-inch ILI9341-class/FT6336G capacitive-touch TFT. It is
  requested from PCBWay as a **loose, off-board** part in the extras BOM
  (quote requested; customer-supplied if unavailable) and is installed only
  after the exact module revision and pin order are verified. Do not solder
  it to J3 at assembly.
- `J6` and `J7` are **internal** 2x13, 2.54 mm test headers at the rear edge
  (they replaced the Rev A panel-mount DB-25 sockets). `J6` carries analog
  stage nodes; `J7` carries clocks, serial buses, and control/status
  signals. They do not need an enclosure cutout.
- Through-hole panel parts: J1 (CUI PJ-102AH barrel), J2 (RJHSE-5380 RJ45),
  J4 (Neutrik NRJ6HF), J5 (CUI SJ1-3533NG), RV1 (Alps RK097 dual pot), SW1
  (E-Switch 100SP toggle), SW2 (12 mm tactile), SW3 (Alps EC11E encoder),
  SW4 (Alps SKQUCAA010 5-way nav).
- Use the exact listed ICs. Generic resistors/capacitors may be substituted with
  the same value, package, voltage rating, dielectric, and tolerance. Keep each
  four-part 0.1% resistor set from one manufacturer lot.
- Do not substitute the electret ESD parts with high-capacitance TVS diodes.
- Verify pin 1/orientation for U1, U4-U7, U9, and U10 before reflow.
- The PCB has intentional dense silkscreen. PCBWay may clip ink away from pads;
  use the assembly PDFs for reference designators.
- The STEP export uses the stock KiCad 3D models (vendor STEP overrides were
  removed 2026-07-25 because they were mis-rotated). Still check the real
  panel parts directly during enclosure layout, especially protrusion and
  cable-clearance geometry.

## Parts not standardized by the PCB

- The display mounting pattern is a nominal 93.3 x 51.34 mm rectangle for
  the LCDWiki MSP3520 3.5-inch module (H5-H8). Compare the purchased module
  before drilling the lid.
- The board targets the Hammond 1590XX (138 x 114 mm PCB envelope). Check
  the STEP file against the real box before drilling any wall.
- The mating cable is a shielded CAT6 cord terminated in an 8P8C (RJ45) plug; it
  must mate with the board's Amphenol RJHSE-5380 shielded jack and preserve the
  exact pinout in `connector-pinout.md`.
- A metal enclosure must bond to the RJ45/CAT6 jack shell (RJHSE-5380, SH pin)
  at the connector. The four capsule returns are circuit ground, not shield
  conductors.

## Power and safety note

Use a regulated, center-positive 9 VDC supply rated for at least 1 A. Do not
connect the 9 V barrel input and Teensy USB power at the same time unless the
Teensy VIN-to-VUSB link is cut. USB data remains usable after that separation.

## Required Rev B bring-up

1. Power without U8, TFT, or microphone and verify +5 V, +3.3 V analog, and the
   4.5 V virtual reference.
2. Fit U8 and verify the +3.3 V digital rail and I2C communication with U7.
3. Configure U7 for four-channel TDM and verify all clocks with an
   oscilloscope. Note the 2026-07-25 review finding: 192 kHz 4-ch TDM pushes
   PCM1864 BCK to 49.152 MHz; 96 kHz 4-ch TDM or 192 kHz via 2x I2S (DOUT2)
   are the safe modes (`../reviews/rev-a-final-review.md`, item A.1).
4. Inject the same low-level sine into all four inputs; measure gain, pad amount,
   polarity, noise, crosstalk, and clipping.
5. Verify sustained four-file SD writes on the exact microSD card.
6. Fit the DAC/headphone path, verify mute/enable sequencing, and test first
   into a dummy load.
7. Only then connect the electret microphone after confirming its bias polarity
   and current.

## Before ordering — open items (2026-09-06)

1. **Physical 1590XX fit has not been checked.** Print
   `../exports/QuadPreRecorder-top.pdf` / `-bottom.pdf` at 100%, sit the paper
   in the real box, and check J1/J2/J4/J5/RV1/SW1 wall positions, the lid
   standoff height for SW2/SW3 and the TFT (SW4 gets no lid hole — internal
   setup control; navigation is touch + SW3 push), and the SD slot at the rear
   wall. `../enclosure-stackup-and-templates.md` is the retired 1590F study
   and does not apply.
2. Confirm the purchased MSP3520 module's 14-pin order and 93.3 x 51.34 mm
   hole pattern.
3. Confirm the CAT6 cable/plug against the RJHSE-5380 jack.
4. Decide surface finish and quantity; get the assembly quote (PCBWay quotes
   assembly manually, typically 1-2 business days). Sourcing note: PCBWay
   turnkey buys by MPN from global distributors (DigiKey/Mouser/etc.), so the
   Neutrik NRJ6HF, Alps RK097/EC11E/SKQUCAA010, E-Switch 100SP, CUI and
   Amphenol parts are all normally sourceable — but keep "accept
   substitutes" set to NO for them; PCBWay will otherwise offer look-alikes.
5. microSD access: Rev B places the Teensy's own card slot at the rear wall
   (`SD CARD SLOT THIS EDGE`) so a rear-wall slot gives direct access — the
   Adafruit 6070 round extender needs a Ø30 mm panel hole and does not fit
   this 35 mm-tall box with the PCB in the way (see
   `../enclosure-1590XX-desk-study.md` §3). If the card turns out not to be
   finger-reachable through the wall, use a slim flat-ribbon microSD
   extender in a rectangular rear-wall cutout instead.

Pre-order review: `../reviews/rev-b-preorder-review.md`.
