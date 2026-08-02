# PCBWay handoff — QuadPreRecorder Rev A

Mechanical note: this handoff targets a Hammond 1590F mechanical-fit prototype.
The board-mounted panel parts have been moved to real board edges, but the
physical enclosure stackup still needs a human check against the STEP export,
the actual Hammond box, the connector shells, the lid standoffs, and the
purchased TFT module before ordering.

## Order configuration

| Setting | Value |
|---|---|
| Board size | 174.0 x 174.0 mm |
| Layers | 2 |
| Material | FR-4 |
| Finished thickness | 1.6 mm |
| Copper | 1 oz outer layers |
| Minimum track / clearance | 0.20 mm / 0.15 mm |
| Minimum finished via drill | 0.40 mm |
| Surface finish | Lead-free HASL for lowest cost; ENIG is an acceptable upgrade |
| Solder mask / silkscreen | Green / white |
| Assembly | Two-sided mixed SMT and through-hole assembly |
| Stencil | Both sides if PCBWay assembles U8 and J4 on the bottom |

Upload `QuadPreRecorder-RevA-Gerbers.zip` as the PCB file. Upload
`QuadPreRecorder-BOM.csv` and `QuadPreRecorder-CPL-PCBWay.csv` to the assembly
quote.

Current export caveat: after the Hammond 1590F mechanical-fit rework, the
Gerbers, drills, BOM, placement CSVs, schematic PDF, assembly PDFs, STEP,
connector pinout, mechanical notes, ERC/DRC reports, and
`QuadPreRecorder-RevA-PCBWay-handoff.zip` were refreshed from the corrected
KiCad board with KiCad 10.0.4 CLI. ERC is clean. DRC has no shorts, no
clearance/edge/hole/mask errors, no unconnected pads, and no schematic-parity
issues.

The Gerber archive also includes top/bottom paste layers and an IPC-D-356
electrical netlist. Three 1 mm global fiducials are present on each assembly
side and intentionally omitted from the BOM/CPL.

## Assembly instructions

- `R5` is DNP (do not populate). It is the optional direct CHASSIS-to-GND link.
- `U8` (Teensy 4.1) and `J4` (6.35 mm line jack) are mounted on the bottom.
- `U8` must be a genuine PJRC Teensy 4.1. It may be customer-supplied to PCBWay.
  If serviceability is preferred, install two low-profile 1x24 female headers
  instead and insert the module after assembly; record that substitution on the
  order because the CPL lists the module itself.
- `J3` is only the 1x14, 2.54 mm display header. The target module is the
  LCDWiki MSP2834 ILI9341/FT6336G capacitive-touch TFT, user-supplied and
  installed after the exact module revision and pin order are verified.
- `J6` and `J7` are right-angle DB-25 external debug sockets. `J6` carries
  analog stage nodes; `J7` carries clocks, serial buses, and control/status
  signals. Pin 25 is an extra ground/reference pin on both connectors.
- Use the exact listed ICs. Generic resistors/capacitors may be substituted with
  the same value, package, voltage rating, dielectric, and tolerance. Keep each
  four-part 0.1% resistor set from one manufacturer lot.
- Do not substitute the electret ESD parts with high-capacitance TVS diodes.
- Verify pin 1/orientation for U1, U4-U7, U9, and U10 before reflow.
- The PCB has intentional dense silkscreen. PCBWay may clip ink away from pads;
  use the assembly PDFs for reference designators.
- The STEP export includes the local vendor models for J1, J4, J5, RV1, SW2,
  and SW3. Still check those real parts directly during enclosure layout,
  especially the panel protrusion and cable-clearance geometry.

## Parts not standardized by the PCB

- The display mounting pattern is a nominal 78 x 42 mm rectangle. Low-cost
  2.8-inch TFT modules vary; compare the purchased module before drilling.
- The board targets Hammond 1590F, not the original 1590BB2-sized envelope.
  Check the STEP file and the real DB-25 cable exit path before drilling.
- The DE-9 cable plug must mate with the board's female socket and preserve the
  exact pinout in `../connector-pinout.md`.
- A metal enclosure must bond to the DE-9 shell/pin 5 at the connector. The four
  capsule returns are circuit ground, not shield conductors.

## Power and safety note

Use a regulated, center-positive 9 VDC supply rated for at least 1 A. Do not
connect the 9 V barrel input and Teensy USB power at the same time unless the
Teensy VIN-to-VUSB link is cut. USB data remains usable after that separation.

## Required Rev A bring-up

1. Power without U8, TFT, or microphone and verify +5 V, +3.3 V analog, and the
   4.5 V virtual reference.
2. Fit U8 and verify the +3.3 V digital rail and I2C communication with U7.
3. Configure U7 for four-channel, 192 kHz, 24-bit, 4-slot TDM and verify all
   clocks with an oscilloscope.
4. Inject the same low-level sine into all four inputs; measure gain, pad amount,
   polarity, noise, crosstalk, and clipping.
5. Verify sustained four-file SD writes on the exact microSD card.
6. Fit the DAC/headphone path, verify mute/enable sequencing, and test first
   into a dummy load.
7. Only then connect the electret microphone after confirming its bias polarity
   and current.

Rev A has clean automated ERC/parity reports and DRC is electrically and
fabrication clean. (An earlier note about headphone-cluster courtyard overlaps
referred to the pre-1590F compact layout; the current board was re-checked on
2026-07-25 and has zero courtyard overlaps.) It has not yet completed this
physical validation — see `../enclosure-stackup-and-templates.md` for the
desk-study results, the required PCB/BOM changes (H5-H8 TFT hole pattern, J2
DE-9 part number, SW2/SW1 lid reach), and the printable drill templates.
