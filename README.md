# Quad Preamp and Recorder

Compact four-channel ambisonic electret preamp, 192 kHz/24-bit recorder,
real-time binaural monitor, and touchscreen controller.

The hardware is derived from
[jdg511/Quadelectretpre](https://github.com/jdg511/Quadelectretpre) and is
redesigned as a mixed-signal two-layer PCB for a larger Hammond-style
enclosure with two external DB-25 debug connectors.

## Project layout

- `hardware/` — KiCad project, fabrication package, design notes, and reviews.
- `tools/` — reproducible schematic, PCB, and fabrication-generation scripts.
- `firmware/` — recorder/DSP interface, pin map, file-naming rules, and
  implementation requirements. Production firmware is not included in Rev A.

## Revision status

Rev A is routed as a Hammond 1590F mechanical-fit prototype. J1/J2/J5/RV1 are
left-wall parts, J4 is a bottom-wall line output, J6/J7 are right-wall debug
connectors, and the top side carries the TFT header plus SW1/SW2/SW3 controls.
The display target is the LCDWiki MSP2834 ILI9341/FT6336G capacitive-touch
module.

The checked-in KiCad PCB source, Gerbers, drills, BOM, and placement CSVs in
`hardware/manufacturing/` were refreshed using KiCad 10.0.4 CLI. ERC is clean.
DRC has no shorts, no clearance/edge/hole/mask errors, no unconnected pads, and
no schematic-parity issues.

This still needs a physical enclosure stackup check before ordering: confirm the
real Hammond 1590F lid height, standoff height, wall cutouts, connector shells,
button/shaft reach, and the purchased TFT module.

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
