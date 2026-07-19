# PCBWay handoff — QuadPreRecorder Rev A

## Order configuration

| Setting | Value |
|---|---|
| Board size | 110.0 x 84.5 mm |
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
quote. The full handoff archive contains those files, drawings, reports, STEP,
and checksums.

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
- `J3` is only the 1x14, 2.54 mm display header. The ILI9341/XPT2046 TFT module
  is user-supplied and installed after the exact pin order is verified.
- Use the exact listed ICs. Generic resistors/capacitors may be substituted with
  the same value, package, voltage rating, dielectric, and tolerance. Keep each
  four-part 0.1% resistor set from one manufacturer lot.
- Do not substitute the electret ESD parts with high-capacitance TVS diodes.
- Verify pin 1/orientation for U1, U4-U7, U9, and U10 before reflow.
- The PCB has intentional dense silkscreen. PCBWay may clip ink away from pads;
  use the assembly PDFs for reference designators.
- The STEP export is electrically/mechanically useful for the board and modeled
  parts, but KiCad's installed library lacks 3D models for J1, J4, J5, RV1,
  SW2, and SW3. Check those six real parts directly during enclosure layout.

## Parts not standardized by the PCB

- The display mounting pattern is a nominal 78 x 42 mm rectangle. Low-cost
  2.8-inch TFT modules vary; compare the purchased module before drilling.
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

Rev A has clean automated ERC/DRC/parity reports, but it has not yet completed
this physical validation.
