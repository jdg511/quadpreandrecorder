# Mechanical reference (Rev C, 2026-09-08)

Everything below describes **Rev C**: the 138 x 114 mm two-layer board in the
**Hammond 1590XX** with 12 mm corner chamfers for the lid-screw posts
(validated against Hammond's STEP, see `enclosure-1590XX-desk-study.md`).
Rev C moved the 9 V barrel to the rear wall, added a USB-C receptacle on the
rear wall, removed the pad toggle (left wall) and the volume pot (right
wall), and changed the display to the LCDWiki MSP3526 capacitive module, and added an internal LiPo battery with USB charging and a two-button soft-power latch.

Coordinates use the KiCad datum at the board's upper-left as `(0, 0)`, X to
the right, Y downward. Frame convention: Y=0 faces the REAR wall (SD slot,
9 V barrel, USB-C), Y=114 the FRONT wall (line out), X=0 the LEFT wall
(mic), X=138 the RIGHT wall (phones).

The board has no corner mounting holes — it is carried by its wall-mounted
connectors (RJ45, 1/4-inch jack, 3.5 mm jack) and sits 19.5-20 mm above the
box floor (see the desk study for the height stack).

## Wall parts

| Ref | X (mm) | Y (mm) | Rot | Wall | Function |
|---|---:|---:|---:|---|---|
| J2 | 4.00 | 74.00 | 270 | Left | Ambisonic mic RJ45 (Amphenol RJHSE-5380), port ~flush with the wall |
| J5 | 133.50 | 41.00 | 270 | Right | 1/8 in binaural headphone out (CUI SJ1-3533NG) |
| J4 | 22.00 | 97.00 | 270 | Front (top side) | 1/4 in binaural line out (Neutrik NRJ6HF) |
| J1 | 17.50 | 8.20 | 180 | Rear-left | 9 V DC barrel (CUI PJ-102AH), nose 5.5 mm past the board edge |
| J9 | 40.00 | 4.20 | 180 | Rear | USB-C receptacle (HRO TYPE-C-31-M-12), face 0.55 mm inside the board edge, 3.2 mm tall |
| U8 | 60.00 | 62.50 | 0 | Bottom side | Teensy 4.1 on sockets (rows x = 60.0 and 75.24, 15.24 mm apart, corrected 2026-09-15); body x 58.7 to 76.5; SD slot + (unused) micro-B at the rear edge near X=68 |

Wall cutout centres are the part centres in the table plus the board's
height; see the desk-study wall-cutout table for sizes.

## Lid parts

| Ref | X (mm) | Y (mm) | Rot | Function |
|---|---:|---:|---:|---|
| SW2 | 40.75 | 71.00 | 0 | Record start/stop pushbutton (Omron B3F-5150), plunger at (47, 73.5) |
| SW3 | 61.50 | 71.00 | 0 | Gain encoder (Alps EC11E), shaft at (69, 73.5) — use the 25/30 mm-height variant |
| SW4 | 91.00 | 73.50 | 0 | 5-way nav (Alps SKQUCAA010), stem at (91, 73.5); internal only, no lid hole |
| Display | 23.0-121.0 | 8.0-63.5 | — | MSP3526 module envelope (98.0 x 55.5); touch lens 84.96 x 55.5 centred on the module |

## TFT mounting holes (M3, 3.2 mm)

| Ref | X (mm) | Y (mm) |
|---|---:|---:|
| H5 | 26.00 | 11.00 |
| H6 | 118.00 | 11.00 |
| H7 | 26.00 | 60.50 |
| H8 | 118.00 | 60.50 |

Pattern 92.0 x 49.5 mm, module centre (72.0, 35.75). The module plugs into
the J3 socket at X = 25.0, Y 19.24 (pin 1, rear) .. 52.26 (pin 14) and rides
on 11 mm standoffs (8.5 mm socket + 2.5 mm header body). With the board top
at 20 mm above the floor the touch lens ends ~36.9 mm up, i.e. inside the
2 mm lid window (lid underside 35.25, lid face 37.25) — a near-flush touch
surface. Verify the real module (pin length, hole pattern) before drilling.

## Internal parts worth knowing about

| Ref | X (mm) | Y (mm) | Side | Function |
|---|---:|---:|---|---|
| J3 | 25.00 | 19.24 | Top | Display socket 1x14 (pin 1) |
| TP1 / TP2 | 56.50 | 18.0 / 21.5 | Bottom | USB D+ / D- wire pads to the Teensy underside pads |
| U11 / L2 | 9.5 / 18.0 | 31.5 | Top | TPS61175 boost + 10 uH (left strip) |
| U12 | 9.50 | 50.50 | Top | ADP7142 9 V analog LDO (TSOT-23-5; was TPS7A4701 until 2026-09-12) |
| K1 | 113.00 | 103.50 | Top | Line-out mute relay (Omron G6K-2F-Y), front-right strip |
| U13 | 129.50 | 16.50 | Top | BQ24074 battery charger (rear-right strip) |
| J10 | 121.00 | 109.50 | Bottom | JST-PH battery connector, front-right |
| Q3 / Q4 | 30.00 | 67 / 71 | Top | Soft-power latch MOSFETs (RECORD + encoder push) |
| Battery | 80–140 | 15–105 | Box floor | 906090 LiPo pouch, 9 mm thick, under the right half (Teensy stack occupies x 58-77) |
| U10 | 112.00 | 56.00 | Top | TPA6130A2 headphone amp (I2C volume) |

Before drilling the Hammond box, print the top and bottom PDFs at 100%, fit
the bare PCB, and transfer the actual connector centres. The Rev C STEP
(`manufacturing/QuadPreRecorder-RevC.step`) is the source for CAD
interference checks; this table is not a panel template.
