# Mechanical reference

Coordinates use the KiCad placement datum near the upper-left as `(0, 0)`.
The final board outline spans X=0.0 to 174.0 mm and Y=0.0 to 174.0 mm. The
target enclosure is Hammond 1590F. Connector bodies deliberately approach or
overhang the board edges so the panel-mounted portions can pass through drilled
or milled wall cutouts.

## Board and TFT holes

All holes below are 3.2 mm nominal M3 non-plated mounting holes.

| Ref | X (mm) | Y (mm) | Purpose |
|---|---:|---:|---|
| H1 | 7.00 | 7.00 | PCB mounting |
| H2 | 167.00 | 7.00 | PCB mounting |
| H3 | 167.00 | 167.00 | PCB mounting |
| H4 | 7.00 | 167.00 | PCB mounting |
| H5 | 48.00 | 24.00 | TFT nominal upper-left |
| H6 | 126.00 | 24.00 | TFT nominal upper-right |
| H7 | 48.00 | 66.00 | TFT nominal lower-left |
| H8 | 126.00 | 66.00 | TFT nominal lower-right |

The TFT pattern is 78 x 42 mm and targets the LCDWiki MSP2834 module family.
Verify the actual screen before drilling the lid.

## Principal component origins

These are placement origins, not enclosure drill diameters. Use the STEP model
and the real parts to mark panel cutouts.

| Ref | X (mm) | Y (mm) | Side | Function |
|---|---:|---:|---|---|
| J2 | 5.20 | 60.00 | Top | DE-9 microphone input protruding past left wall |
| J1 | 8.20 | 96.00 | Top | 9 VDC input protruding past left wall |
| J5 | 4.50 | 124.00 | Top | 3.5 mm headphone output protruding past left wall |
| RV1 | 6.50 | 155.00 | Top | Headphone volume shaft protruding past left wall |
| J4 | 125.00 | 171.00 | Bottom | 6.35 mm line output protruding past bottom wall |
| J6 | 167.70 | 26.00 | Top | DB-25 analog debug connector protruding past right wall |
| J7 | 167.70 | 116.00 | Top | DB-25 digital/control debug connector protruding past right wall |
| SW1 | 140.00 | 78.00 | Top | -10 dB pad slide switch; lid cutout required |
| SW2 | 44.00 | 10.00 | Top | Record button; lid button/plunger check required |
| SW3 | 68.00 | 10.00 | Top | Master gain encoder; lid/knob stackup check required |
| J3 | 87.00 | 76.00 | Top | MSP2834 TFT 14-pin header |
| U8 | 39.00 | 144.00 | Bottom | Teensy 4.1; preserve SD/USB access |

Before drilling the Hammond box, print the top and bottom PDFs at 100%, fit the
bare PCB, and transfer the actual connector/shaft centers. The STEP file is the
source for CAD interference checks; the nominal table is not a panel template.
