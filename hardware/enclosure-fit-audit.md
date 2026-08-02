# Enclosure and panel-fit audit

Status: PCB mechanically reworked for Hammond 1590F and rerouted. KiCad DRC/ERC
passes, but the physical enclosure stackup still must be checked with the real
box, lid, standoffs, connector shells, knobs/buttons, and TFT module before
ordering.

Checked: 2026-07-24

## Selected enclosure

Target metal enclosure: Hammond 1590F.

- Official outside size: 188 x 188 x 67 mm.
- Official maximum PCB envelope: 174.91 x 174.91 mm.
- Rev A PCB outline: 174.0 x 174.0 mm.
- Reason: the prior compact board could fit electrically but did not put J1,
  J4, and J5 on real panel edges. The 1590F gives enough PCB envelope for the
  DE-9 mic input, two DB-25 debug connectors, 9 V barrel input, 6.35 mm line
  output, 3.5 mm headphone output, headphone volume shaft, top controls, and
  TFT mounting pattern to coexist.

Reference:

- https://www.hammfg.com/part/1590F

## Selected TFT

Target capacitive TFT module: LCDWiki MSP2834 / 2.8inch IPS SPI Module ILI9341
with capacitive touch.

- Display: 2.8 inch, 240 x 320, ILI9341V over 4-wire SPI.
- Touch: capacitive, FT6336G over I2C.
- Module: 50.0 x 86.0 x 14.28 mm with touch, including header.
- Connector: 14-pin, 2.54 mm header plus optional FPC.
- PCB mounting pattern: 78 x 42 mm nominal at H5-H8.

Reference:

- https://www.lcdwiki.com/2.8inch_IPS_SPI_Module_ILI9341

## Current PCB panel-fit findings

Board outline: X=0.0 to 174.0 mm, Y=0.0 to 174.0 mm.

| Ref | Current routed placement | Status before physical stackup check |
|---|---|---|
| J2, DE-9 ambisonic mic input | X=5.20, Y=60.00, protrudes past left PCB edge | Directionally correct for left wall. Verify connector shell and mating plug clearance. |
| J1, 9 V barrel DC input | X=8.20, Y=96.00, body protrudes past left PCB edge while pads retain DRC edge clearance | Directionally corrected for left wall. Verify barrel opening against wall thickness/cutout. |
| J5, 3.5 mm headphone out | X=4.50, Y=124.00, protrudes past left PCB edge | Directionally correct for left wall. Verify jack nose and plug clearance. |
| RV1, headphone volume | X=6.50, Y=155.00, shaft/body protrudes past left PCB edge | Directionally correct for side-wall knob. Verify shaft length and knob clearance. |
| J4, 6.35 mm binaural line out | X=125.00, Y=171.00 on bottom side, protrudes past bottom PCB edge | Directionally correct for bottom wall. Verify bottom-side assembly and enclosure clearance. |
| J6, analog debug DB-25 | X=167.70, Y=26.00, protrudes past right PCB edge | Directionally correct for right wall. Verify DB-25 hardware/cable clearance. |
| J7, digital debug DB-25 | X=167.70, Y=116.00, protrudes past right PCB edge | Directionally correct for right wall. Verify DB-25 hardware/cable clearance. |
| SW1, pad enable slide switch | X=140.00, Y=78.00, top-mounted | Lid cutout required; verify actuator height. |
| SW2, record pushbutton | X=44.00, Y=10.00, top-mounted | Verify Omron B3F-4050 body/cap/plunger height against lid standoffs. |
| SW3, master gain encoder | X=68.00, Y=10.00, top-mounted | Verify shaft length, nut/washer stack, and knob clearance. |
| TFT | H5-H8 at 48/126 x 24/66 mm; J3 at X=87.00, Y=76.00 | Verify purchased MSP2834 mechanical drawing or physical sample before drilling. |

## KiCad validation after rework

- ERC: clean.
- DRC: 0 violations.
- Unconnected pads: 0.
- Schematic parity issues: 0.

## Remaining physical checks before manufacture

1. Import `QuadPreRecorder-RevA.step` into a mechanical CAD model of the Hammond
   1590F or test with a printed 1:1 drill template and bare PCB.
2. Confirm wall cutout centers and dimensions for J1, J2, J4, J5, J6, J7, and
   RV1 using the real connector bodies.
3. Confirm lid standoff height so SW1, SW2, SW3, and the TFT reach through the
   top panel without being crushed.
4. Confirm the purchased MSP2834 module revision uses the expected 14-pin order
   and the 78 x 42 mm mounting pattern.
5. Only then treat the PCBWay handoff ZIP as an order candidate.
