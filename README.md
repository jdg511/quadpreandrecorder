# Quad Preamp and Recorder

Compact four-channel ambisonic electret preamp, 192 kHz/24-bit recorder,
real-time binaural monitor, and touchscreen controller.

The hardware is derived from
[jdg511/Quadelectretpre](https://github.com/jdg511/Quadelectretpre) and is
redesigned as a mixed-signal two-layer PCB for a Hammond 1590BB2
enclosure.

## Project layout

- `hardware/` — KiCad project, fabrication package, design notes, and reviews.
- `tools/` — reproducible schematic, PCB, and fabrication-generation scripts.
- `firmware/` — recorder/DSP interface, pin map, file-naming rules, and
  implementation requirements. Production firmware is not included in Rev A.

## Revision status

Rev A is a routed, two-layer prototype release. The checked-in KiCad project
passes ERC and DRC with zero violations, zero unconnected pads, and zero
schematic/PCB parity issues. PCBWay-ready Gerbers, drills, BOM, placement data,
assembly drawings, and STEP output are in `hardware/manufacturing/`.

This is still new mixed-signal hardware, not a bench-proven production
revision. Read the prototype confirmations in `hardware/requirements.md` and
the order/bring-up notes in `hardware/manufacturing/README.md` before ordering.

## Rebuild

- `tools/route_pcb.ps1` regenerates the schematic/footprints/placement, runs a
  supplied Freerouting 2.2.4 jar headlessly, imports the route, and checks DRC.
- `python tools/build_manufacturing.py` regenerates the complete PCBWay handoff
  with KiCad 10's command-line tools.

The checked-in routed board is the release artifact; rerouting is not required
to order it.
