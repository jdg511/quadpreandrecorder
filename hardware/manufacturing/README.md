# PCBWay handoff — QuadPreRecorder Rev C3 (Hammond 1590XX, 4 layers)

Package regenerated 2026-09-12 from the fully routed Rev C3 board with
`tools/build_manufacturing.py` (KiCad 10.0.4 CLI). ERC: 0 errors / 0
warnings. DRC (`--all-track-errors --schematic-parity --severity-error`):
**0 violations, 0 unconnected pads, 0 schematic-parity issues.**

Rev C = Rev B + USB-C power/data (J9, rear wall), 9 V barrel moved to the
rear-left wall (J1), boost + low-noise LDO analog supply (U11/U12), relay
line-out mute (K1), TPA6130A2 I2C headphone amp (U10, no pot), GPIO-driven
pad (Q1, no toggle), the LCDWiki **MSP3526 capacitive** display in a
socket (J3), and an internal LiPo battery (J10, BQ24074 charger U13) with a
two-button soft-power latch (Q3/Q4). Rev B outputs are archived in `revb-archive/`.

Rev C2 (2026-09-08/11) made it a 4-layer board and fixed the enclosure fit.
Rev C3 (2026-09-12) is the audio-audit fix pass
(`../reviews/audio-rules-check-revC3-fixes.md`): the J6/J7 test headers are
gone, In2.Cu is a second solid GND plane (SIG/GND/GND/SIG), the converters'
digital rail has its own LDO (U14, +3V3_DC), every converter decoupler sits
under its pin, U10's exposed pad has its via array, and the eight
channel-coupling caps plus the four headphone-input caps are Rubycon PMLCAP
film instead of X7R.

What is still a **human** check before you click order: the board has never
been test-fitted in a real 1590XX box, and three Rev C circuits want a bench
look (see "Before ordering" at the end and
`../reviews/rev-c-preorder-review.md`).

## Order configuration

| Setting | Value |
|---|---|
| Board size | 138.0 x 114.0 mm, 12 mm corner chamfers (Hammond 1590XX max PCB envelope) |
| Layers | 4: F.Cu signal / In1.Cu solid GND / In2.Cu solid GND / B.Cu signal |
| Stackup | Standard 1.6 mm 4-layer: 35 um Cu, ~0.21 mm prepreg / ~1.07 mm core / ~0.21 mm prepreg (written into the board file; no impedance control) |
| Material | FR-4 |
| Finished thickness | 1.6 mm |
| Copper | 1 oz outer and inner |
| Minimum track / clearance (actual) | 0.20 mm / 0.15 mm (supply rails 0.30 mm) — PCBWay standard floor is 0.10 / 0.10 |
| Minimum via (actual) | 0.60 mm pad / 0.30 mm drill (0.15 mm annular) for the 185 decoupling/thermal/escape vias; 0.80 / 0.40 elsewhere (338); PCBWay floor 0.30 / 0.15 / 0.15 |
| Copper-to-edge | ≥ 0.65 mm (rule-area keepouts; PCBWay asks ≥ 0.30 mm) |
| Surface finish | Lead-free HASL for lowest cost; ENIG is an acceptable upgrade |
| Solder mask / silkscreen | Green / white |
| Assembly | Two-sided mixed SMT and through-hole: 293 placements (180 top, 113 bottom) |
| Stencil | Both sides — U8 (Teensy 4.1 sockets), TP1/TP2 and the bottom-side passives are on the back |

Upload `QuadPreRecorder-RevC-Gerbers.zip` as the PCB file (or the full
`QuadPreRecorder-RevC-PCBWay-handoff.zip`). Upload `QuadPreRecorder-BOM.csv`
and `QuadPreRecorder-CPL-PCBWay.csv` to the assembly quote, and attach
`QuadPreRecorder-BOM-extras.csv` (the U8 socket sub-assembly, the USB wire
step, and the loose off-board parts you want PCBWay to quote and ship with
the boards). `PCBWAY-ORDER-NOTES-REVC.txt` has the paste-ready order text.

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
  **top** side at the front wall.
- `U8` is a **socketed sub-assembly** (see `QuadPreRecorder-BOM-extras.csv`):
  solder two Samtec **SLW-124-01-G-S** low-profile 1x24 sockets into the U8
  footprint (bottom side, rows 15.24 mm apart; corrected 2026-09-15), then plug a PJRC
  **TEENSY41_PINS** (Teensy 4.1 with the outer 2x24 pins pre-soldered) into
  them, microSD slot toward the rear wall (Y=0 edge, silkscreen "SD CARD SLOT
  THIS EDGE"). **Before** plugging it in: cut the Teensy's underside VIN-VUSB
  link pad, and solder two ~20 mm wires from the Teensy's underside "USB
  Device" D+ / D- pads to the board's bottom-side pads **TP1 (D+)** and **TP2
  (D-)** next to the socket. The Teensy is customer-supplied if PCBWay cannot
  source PJRC parts.
- `J3` is a 1x14, 2.54 mm **female socket** (Sullins PPTC141LFBN-RC). The
  LCDWiki **MSP3526** module plugs into it later, on 11 mm M3 standoffs over
  H5-H8; it is requested from PCBWay as a **loose, off-board** part. Do not
  solder a display at assembly.
- `J9` is an HRO TYPE-C-31-M-12 USB-C receptacle (16-pin, through-hole shell
  tabs). `K1` is an Omron G6K-2F-Y DC5 signal relay — keep the exact part
  (pinout and coil polarity matter; coil pin 1 = +).
- `J10` (JST-PH, bottom side) takes the customer-supplied 3.7 V 5000 mAh
  906090 LiPo pouch (with PCM). Do not fit a battery at assembly. `U13`
  (BQ24074, QFN with exposed pad) is the charger.
- There are no test headers (J6/J7 were removed in Rev C3). Twelve bare 1.5 mm probe pads `TP3`-`TP14` sit on the **bottom** (ADC clocks at x=124, DAC clocks north of R57-R59, +3V3_DC and three grounds); they are not in the BOM or CPL.
- `U10` (TPA6130A2, WQFN) has a 3x3 array of 0.3 mm vias in its exposed pad. Keep them tented on the bottom side so paste does not wick through.
- `C17`-`C20`, `C25`-`C28`, `C57`, `C58`, `C86`, `C87` are Rubycon **PMLCAP film** chips (1812 / 1210), not MLCCs. Do not substitute ceramics. LCSC C3778321 / C3778570 are the cheap source; the 16 V siblings (16MU475MC14532 / 16MU225MB23225, DigiKey/Mouser) are acceptable alternates.
- Through-hole panel parts: J1 (CUI PJ-102AH barrel, rear-left), J2 (RJHSE-5380
  RJ45, left), J4 (Neutrik NRJ6HF, front), J5 (CUI SJ1-3533NG, right), SW2
  (12 mm tactile), SW3 (Alps EC11E encoder), SW4 (Alps SKQUCAA010 5-way nav,
  internal only).
- Use the exact listed ICs (U1, U4-U7, U9-U13). Generic resistors/capacitors
  may be substituted with the same value, package, voltage rating, dielectric
  and tolerance. Keep each four-part 0.1% resistor set from one lot.
- Do not substitute the electret ESD parts with high-capacitance TVS diodes.
- Verify pin 1/orientation for U1, U4-U7, U9-U13 and K1 before reflow.
- The STEP export uses the stock KiCad 3D models; several connectors have no
  model and appear as bare footprints. Check the real panel parts during
  enclosure layout.

## Parts not standardized by the PCB

- Display: LCDWiki MSP3526 (ST7796U + FT6336U capacitive, 5 V). H5-H8 are on
  the 92.0 x 49.5 mm pattern from the LCDWiki drawing; the socket J3 sits
  2.0 mm inside the module's left edge. Compare the purchased module (pin
  order, header position, pin length, hole pattern) before drilling the lid
  or buying standoffs.
- The board targets the Hammond 1590XX (138 x 114 mm PCB envelope). Check
  `QuadPreRecorder-RevC.step` against the real box before drilling any wall
  (`../enclosure-1590XX-desk-study.md`, `../enclosure-1590XX-fit-viewer.html`).
- The mating microphone cable is a shielded CAT6 cord with an 8P8C (RJ45)
  plug; it must preserve the pinout in `connector-pinout.md`.
- A metal enclosure must bond to the RJ45 jack shell (SH pin) and the USB-C
  shell (both on the CHASSIS net) at the connector.

## Power and safety note

Power from a regulated centre-positive 9 VDC / 1 A barrel supply, a 5 V USB-C
source (any charger, power bank or computer port; ~450 mA plus up to 0.74 A
of battery charging), or the internal 1S LiPo (6-7 h). Any combination may
be connected at once; only USB charges the battery. On battery, hold RECORD
and the encoder push for 2 s to switch on or off. Use only a pouch with its
own protection circuit and check the pigtail polarity against J10 pin 1. The Teensy's VIN-VUSB link **must** be cut (the board
powers VIN). Never plug a cable into the Teensy's own micro-B while J9 is in
use — they carry the same D+/D-.

## Required Rev C bring-up

1. Power from the barrel without U8, TFT or microphone: verify VBOOST_IN,
   +10.45 V (U11), +9 V (U12), +5 V, +3.3 V analog and the 4.5 V reference.
   Scope the 10.45 V rail with a 0 → 200 mA load step (no ringing).
2. Repeat from USB-C 5 V only (a charger). Check the input current (~450 mA
   without a battery). Then plug in the LiPo: VBAT rises, /CHG low, U13 warm
   but not hot (it throttles at 125 °C junction); unplug USB and confirm the
   unit stays up on the battery only while RECORD + encoder push are held
   (until firmware asserts KEEP_ON).
3. Fit U8 (wires to TP1/TP2, VUSB link cut) and verify the +3.3 V digital
   rail, I2C to U7 (ADC), U10 (0x60) and the touch controller (0x38), and USB
   enumeration through J9.
4. Configure U7 for four-channel TDM and verify all clocks (192 kHz 4-ch TDM
   pushes BCK to 49.152 MHz; 96 kHz TDM or 192 kHz via 2x I2S are the safe
   modes — `../reviews/rev-a-final-review.md`, A.1).
5. Confirm relay K1: line out passes audio with the coil OFF and is silent
   with LINE_MUTE high. Confirm PAD_CTRL high inserts the pad (−9.7 dB).
6. Inject the same low-level sine into all four inputs; measure gain, pad,
   polarity, noise, crosstalk and clipping.
7. Verify sustained four-file SD writes on the exact microSD card, then MTP
   access to the same card from a computer over J9.
8. Fit the headphone path: TPA6130A2 volume steps, mute, /SD, into a dummy
   load first.
9. Only then connect the electret microphone after confirming its bias
   polarity and current.

## Before ordering — open items (2026-09-08)

1. **Physical 1590XX fit has not been checked.** Print
   `../exports/QuadPreRecorder-top.pdf` / `-bottom.pdf` at 100%, sit the paper
   in the real box, and check the J1/J9 (rear), J2 (left), J5 (right), J4
   (front) wall positions, the lid window for the MSP3526 lens, SW2/SW3
   reach (SW4 gets no lid hole), and the SD slot at the rear wall.
2. Confirm the purchased MSP3526 module (pin order, header position, pin
   length → standoff height, 92.0 x 49.5 holes).
3. Confirm the CAT6 cable/plug against the RJHSE-5380 jack.
4. Decide surface finish and quantity; get the assembly quote. PCBWay turnkey
   buys by MPN from global distributors, so the Neutrik, Alps, CUI, Amphenol,
   Omron and HRO parts are normally sourceable — keep "accept substitutes"
   set to NO for them.
5. microSD access: the Teensy's own slot faces the rear wall; if it is not
   finger-reachable through the wall slot, files can also be pulled over
   USB-C (MTP) — the extender is no longer needed.

Pre-order review: `../reviews/rev-c-preorder-review.md`.
