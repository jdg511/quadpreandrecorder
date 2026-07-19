# Mechanical reference

Coordinates use the upper-left PCB corner as `(0, 0)` in the KiCad board file.
The board is 110.0 x 84.5 mm and was sized for the Hammond 1590BB2 internal
envelope. Connector bodies deliberately approach or overhang the board edges.

## Board and TFT holes

All holes below are 3.2 mm nominal M3 non-plated mounting holes.

| Ref | X (mm) | Y (mm) | Purpose |
|---|---:|---:|---|
| H1 | 4.00 | 4.00 | PCB mounting |
| H2 | 92.00 | 4.00 | PCB mounting |
| H5 | 9.00 | 21.25 | TFT nominal upper-left |
| H6 | 87.00 | 21.25 | TFT nominal upper-right |
| H7 | 9.00 | 63.25 | TFT nominal lower-left |
| H8 | 87.00 | 63.25 | TFT nominal lower-right |

The TFT pattern is 78 x 42 mm. Verify the actual screen before drilling the lid.

## Principal component origins

These are placement origins, not enclosure drill diameters. Use the STEP model
and the real parts to mark panel cutouts.

| Ref | X (mm) | Y (mm) | Side | Function |
|---|---:|---:|---|---|
| J2 | 1.80 | 37.40 | Top | DE-9 microphone input at left wall |
| SW1 | 12.00 | 8.00 | Top | -10 dB pad |
| SW2 | 27.00 | 7.00 | Top | Record button |
| SW3 | 46.00 | 7.00 | Top | Master gain encoder |
| J3 | 75.00 | 19.00 | Top | TFT 14-pin header |
| RV1 | 102.00 | 5.00 | Top | Headphone volume |
| J4 | 83.50 | 56.50 | Bottom | 6.35 mm line output |
| J5 | 104.20 | 66.50 | Top | 3.5 mm headphone output |
| J1 | 108.00 | 77.00 | Top | 9 VDC input |
| U8 | 24.00 | 63.00 | Bottom | Teensy 4.1; preserve SD/USB access |

Before drilling the Hammond box, print the top and bottom PDFs at 100%, fit the
bare PCB, and transfer the actual connector/shaft centers. The STEP file is the
source for CAD interference checks; the nominal table is not a panel template.
