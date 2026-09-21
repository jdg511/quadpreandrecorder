# Quad Preamp and Recorder

Compact four-channel ambisonic electret preamp, 192 kHz/24-bit recorder,
real-time binaural monitor, and touchscreen controller.

The hardware is derived from
[jdg511/Quadelectretpre](https://github.com/jdg511/Quadelectretpre) and is
redesigned as a mixed-signal two-layer PCB in a Hammond 1590XX enclosure.

## Project layout

- `hardware/` — KiCad project, fabrication package, design notes, and reviews.
- `tools/` — reproducible schematic, PCB, and fabrication-generation scripts.
- `firmware/` — recorder/DSP interface, pin map, file-naming rules, and
  implementation requirements. Production firmware is not included in Rev A.

## Revision status

The current design is **Rev C** (2026-09-08), routed for the compact
**Hammond 1590XX** (138 x 114 mm board, 145 x 121 x 39 mm enclosure). Rev C
takes the Rev B board and:

- adds a **USB-C** receptacle (J9) on the rear wall — 5 V power from any
  charger, power bank or computer port (TPS61175 boost + ADP7142 low-noise
  LDO make the 9 V analog rail), SD-card file transfer (MTP) and firmware
  updates; the 9 V barrel (J1) stays as an alternative input and moved to the
  rear-left wall;
- mutes the 1/4-inch line out with a signal relay (K1) while a computer is
  attached (ground-loop protection, on-screen warning with override);
- replaces the headphone pot with a **TPA6130A2** I2C-volume headphone amp
  (encoder / touchscreen control) and the pad toggle with a GPIO-driven
  level shifter (pad is a touchscreen control);
- changes the display to the LCDWiki **MSP3526** 3.5-inch IPS module with
  FT6336U **capacitive** touch (the MSP3520 named in Rev B is resistive).
- adds an internal **LiPo battery** (5000 mAh, 6-7 h) with a BQ24074 USB
  charger and a two-button soft-power gesture (hold RECORD + encoder push).

Walls: rear = SD slot + 9 V + USB-C, left = mic RJ45 (Amphenol RJHSE-5380),
right = headphones, front = line out; lid = display, record button, gain
encoder. Rev C3 (2026-09-12) removed the J6/J7 test headers (probe at
component pads or the TP3-TP14 pads), moved to a 4-layer SIG/GND/GND/SIG
stack, and made the mic input switchable from the screen: electret bias
off / 5 V / 9 V (one setting for all four channels) and, with the bias off,
the four RJ45 pairs become true balanced inputs for dynamic microphones
(two-op-amp instrumentation stage, +20.1 dB, SPICE-checked CMRR 58-67 dB
worst case across the audio band). The 9 V analog LDO is an ADP7142
(the TPS7A4701 it replaces had no distributor depth) and every BOM line
was re-checked for stock and price the same day. See
`hardware/reviews/audio-rules-check-revC3-fixes.md`, `hardware/mechanical.md`,
`hardware/connector-pinout.md` and `firmware/docs/REV-C-CONTROL-MODEL.md`.

ERC is clean and DRC (`--all-track-errors --schematic-parity
--severity-error`) reports 0 violations, 0 unconnected pads, 0 parity issues
on the routed board. The Gerbers, drills, BOM, placement CSVs, STEP and PDFs
in `hardware/manufacturing/` are regenerated from it
(`QuadPreRecorder-RevC-PCBWay-handoff.zip`). Rev B outputs are archived in
`hardware/manufacturing/revb-archive/`.

Still a human check before ordering: the physical Hammond 1590XX fit (wall
cutouts, button/shaft reach, the purchased MSP3526 module) — see
`hardware/enclosure-1590XX-desk-study.md` and
`hardware/reviews/rev-c-preorder-review.md`.

This is still new mixed-signal hardware, not a bench-proven production
revision. Read the prototype confirmations in `hardware/requirements.md` and
the order/bring-up notes in `hardware/manufacturing/README.md` before ordering.

## Rebuild

- `tools/route_pcb.ps1` regenerates the schematic/footprints/placement, runs
  Freerouting 1.9.0 (`tools/cache/freerouting19.jar`, single-threaded — the
  2.2.4 jar drops nets from its session export on this board), imports the
  route, adds the GND pours, and checks DRC. Allow ~35-60 minutes.
- `python tools/build_manufacturing.py` regenerates the complete PCBWay handoff
  with KiCad 10's command-line tools.

The checked-in routed board is the release artifact; rerouting is not required
to order it.
