**Rev C (2026-09-08) supersedes the wall table below:** SW1 (pad toggle) and
RV1 (volume pot) were removed; J1 (9 V barrel) moved to the REAR-LEFT wall at
X=17.5; J9 (USB-C) was added on the REAR wall at X=40; the display is the
MSP3526 (holes 92.0 x 49.5, socket J3 at X=25, Y 19.24-52.26). Current
positions: `mechanical.md`; enclosure reasoning: `enclosure-1590XX-desk-study.md`.

# Enclosure and panel-fit audit

Status: **Rev B / Hammond 1590XX — fully routed, DRC clean (2026-09-06).**
The design moved from the Hammond 1590F mechanical-fit prototype (Rev A) to
the compact 1590XX layout (Rev B) that `tools/generate_pcb.py` had carried
since 2026-07-25. On 2026-09-06 the last routing blocker was fixed (U7 moved
out of the Teensy socket's pin columns), the board was re-routed with
Freerouting 1.9.0, the GND pours were re-attached to the `GND` net, and the
PCBWay package was regenerated. What remains is the **physical** check
against a real 1590XX box — nothing below has been test-fitted yet.

Checked: 2026-09-06 (supersedes the 2026-07-24 1590F audit)

## Selected enclosure

Target metal enclosure: Hammond 1590XX.

- Official outside size: 145 x 121 x 39 mm.
- Official maximum PCB envelope: 138 x 114 mm.
- Rev B PCB outline: 138.0 x 114.0 mm — matches the 1590XX's PCB envelope
  exactly, with 12 mm chamfers cut at all four corners for the lid-screw
  posts.
- Reason: on 2026-09-05 the target enclosure was changed from the much
  larger 1590F (188 x 188 x 67 mm, 174 x 174 mm PCB envelope) to the compact
  1590XX. The generator script already had this Rev B layout built and dated
  2026-07-25; it just hadn't been reflected in any documentation or
  reconciled as the active design until now.

Reference:

- https://www.hammfg.com/part/1590XX

## Selected TFT

Target capacitive TFT module: LCDWiki MSP3520, 3.5-inch SPI module (ILI9341
or compatible controller) with FT6336G capacitive touch. (The 1590F-era
audit this replaces targeted the smaller 2.8-inch MSP2834 — Rev B uses the
larger 3.5-inch module instead.)

- Display: 3.5 inch, module 98.3 x 56.34 mm.
- Touch: capacitive, FT6336G over I2C.
- Mounting hole pattern: 93.3 x 51.34 mm at H5-H8, centered under the module.
- Connector: 14-pin, 2.54 mm header (J3).

Reference:

- https://www.lcdwiki.com/

## Current PCB panel-fit findings

Board outline: X=0.0 to 138.0 mm, Y=0.0 to 114.0 mm, corners chamfered 12 mm
(raised from 9 mm on 2026-09-06 after the desk study in
`enclosure-1590XX-desk-study.md`).
Positions below are read directly from the routed `QuadPreRecorder.kicad_pcb`
(2026-09-06); wall assignment is the design intent in `tools/generate_pcb.py`.

| Ref | Current routed placement | Status before physical stackup check |
|---|---|---|
| J2, ambisonic mic RJ45 (RJHSE-5380) | X=4.00, Y=74.00, Left wall, port ~flush | Present in copper, BOM and CPL. Re-audit clearance and shell/mating-plug fit against the real RJHSE-5380 part. |
| SW1, PAD -10dB toggle | X=2.20, Y=40.00, Left wall | Directionally correct; verify toggle bushing clearance against wall thickness. |
| RV1, dual-gang headphone volume | X=132.00, Y=82.00, Right wall | Directionally correct; verify shaft length and knob clearance. |
| J5, 1/8in headphone out | X=133.50, Y=41.00, Right wall | Directionally correct; verify jack nose and plug clearance. |
| J1, 9V barrel DC input | X=108.00, Y=105.80, Front wall | Directionally correct; verify barrel opening against wall thickness/cutout. |
| J4, 1/4in binaural line out | X=22.00, Y=97.00, Front wall, top side | Directionally correct; verify jack body and cable clearance. |
| J6 / J7 test headers | removed in Rev C3 (2026-09-12) | Nothing to fit. |
| SW2, record pushbutton | X=40.75, Y=71.00, top-mounted | Verify plunger height against lid standoffs. |
| SW3, master gain encoder | X=61.50, Y=71.00, top-mounted | Verify shaft length, nut/washer stack, and knob clearance. |
| SW4, TFT menu 5-way nav | X=91.00, Y=73.50, top-mounted, **internal only** | 2026-09-06: no lid hole — the 10 mm SKQU stem cannot reach the lid in the 1590XX and no extension is available; navigation is by the touch TFT + SW3 push. Reachable with the lid off. |
| TFT | H5-H8 at 93.3 x 51.34 mm pattern; J3 header at X=113.35, Y=63.00 | Verify the purchased MSP3520 module's mechanical drawing (or a physical sample) before drilling. |
| U8, Teensy 4.1 | X=60.00, Y=62.50, bottom side | SD/USB access at rear wall near X=69; verify clearance. |

Rev B has no H1-H4 board-mounting holes — the board is carried by its own
wall-mounted connectors and switches, not corner screws.

## KiCad validation after the Rev B re-route (2026-09-06)

- ERC: 0 errors, 0 warnings.
- DRC (`--all-track-errors --schematic-parity --severity-error`): 0
  violations, **0 unconnected pads**, 0 schematic-parity issues.
- Same-side courtyard overlaps: 0 (generator check).
- Panel orientation check (`tools/check_panel_orientation.py`): all pass.
- GND pours on both layers are on net `GND` (they were un-netted floating
  copper from 2026-09-05 to 2026-09-06 because `import_route.py` looked up
  `/GND`; fixed).
- Routing history: the 2026-09-05 board had 17 unconnected pads because U7
  (PCM1864) sat inside the Teensy socket's two THT pin columns; moving it to
  (83.5, 49.5) over its own decoupling caps cleared 16 of them, and switching
  from Freerouting 2.2.4 (whose .ses silently drops some nets) to 1.9.0
  cleared the rest.

## Remaining physical checks before manufacture

1. Import `manufacturing/QuadPreRecorder-RevB.step` into a mechanical CAD
   model of the Hammond 1590XX, or print `exports/QuadPreRecorder-top.pdf`
   and `-bottom.pdf` at 100% and test-fit the paper in the real box.
3. Confirm wall cutout centers and dimensions for J1, J2, J4, J5, and RV1
   using the real connector bodies, and the toggle bushing clearance for
   SW1.
4. Confirm lid standoff height so SW2, SW3, and the TFT reach through
   the top panel without being crushed.
5. Confirm the purchased MSP3520 module revision uses the expected 14-pin
   order and the 93.3 x 51.34 mm mounting pattern.
6. (J6/J7 test headers removed in Rev C3; nothing to route.)
7. Only then treat `manufacturing/QuadPreRecorder-RevB-PCBWay-handoff.zip`
   (regenerated 2026-09-06 from this board) as the order — see
   `manufacturing/README.md` and `reviews/rev-b-preorder-review.md`.
