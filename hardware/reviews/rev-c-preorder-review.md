# Rev C pre-order review — QuadPreRecorder (Hammond 1590XX, 2-layer)

Date: 2026-09-08. Board: `hardware/QuadPreRecorder.kicad_pcb` (Rev C,
138 x 114 mm, 12 mm chamfers, GND pours both sides). Package:
`hardware/manufacturing/QuadPreRecorder-RevC-PCBWay-handoff.zip`. The Rev B
review (`rev-b-preorder-review.md`) still applies for everything Rev C did not
touch (front end, ADC, DAC, Teensy, controls, enclosure geometry).

## Verdict

**Electrically and fabrication-ready (ERC 0/0, DRC 0 violations / 0
unconnected / 0 parity on the routed board). Not yet order-ready** for the
same reason as Rev B — the board has never been test-fitted in a physical
1590XX — plus three Rev C items that are bench checks, not blockers (table).

## What changed (Rev B → Rev C)

| Change | Why | Where |
|---|---|---|
| USB-C receptacle J9 (rear wall), 5 V only, CC pull-downs | Power from any USB source, MTP access to the SD card, firmware updates over one cable. "Always intended to be USB-C." | `generate_schematic.py`, `generate_pcb.py` |
| 9 V barrel J1 moved front → rear-left wall | Jason: if the barrel stays it cannot be on the front. Between the corner post and the display standoff H5. | `generate_pcb.py`, `check_panel_orientation.py` |
| TPS61175 boost (10.45 V) + TPS7A4701 LDO (9.0 V) | Full operation from 5 V; the analog rail needs 9 V (capsule bias, CD4053, op-amp headroom). Boost → LDO keeps switching ripple off the mic bias; the 5 V buck takes its input from the boost, not the LDO. | power section |
| Relay K1 line-out mute + Q2 driver | Ground-loop protection while a computer is attached over USB; firmware mutes only on host enumeration, never for chargers; on-screen warning + override. Relay (not an analog switch) because the PCM5102A line out swings below ground. | DAC/line-out section |
| TPA6130A2 replaces TPA6132A2 + RV1 pot | Headphone volume on the encoder / touchscreen (I2C, 64 steps, software mute). Right-wall pot hole gone. | headphone section |
| Q1 level shifter replaces SW1 toggle | Pad becomes a screen control; PAD_SELECT still swings 0/9 V for the CD4053s; 10 k pull-up = direct at power-up. Left-wall toggle hole gone. | pad section |
| MSP3526 capacitive display, J3 = female socket, holes 92.0 x 49.5 | The MSP3520 named in Rev B is resistive (XPT2046); the capacitive 3.5-inch LCDWiki part is the MSP3526 (ST7796U + FT6336U, 5 V VCC, level shifting on board). Socket + 11 mm standoffs put the lens inside the lid window. | J3, H5-H8, TFT_* constants |
| Internal LiPo (J10) + BQ24074 charger (U13) + soft-power latch (Q3/Q4, D15-D19, R86-R88) | 5-6 h battery operation, charged over USB-C; RECORD + encoder push held 2 s switches on/off (hardware enable, firmware latch). Linear charger chosen for simplicity; 0.74 A keeps its dissipation ~1 W and it throttles thermally. | charger section |
| Teensy pins: 5 LINE_MUTE, 14 CTP_RST, 15 VBUS_SENSE, 32 PAD_CTRL (out), 24 KEEP_ON, 16 BAT_SENSE, 17 CHG_STAT_N, 25 PGOOD_N | See `firmware/docs/REV-C-CONTROL-MODEL.md`. | Teensy net map |
| Power netclass 0.30 mm | Rev B advisory (all rails were 0.20 mm). 0.50 mm was tried first and Freerouting left five 0.65 mm-pitch pads open. | `generate_pcb.py` |
| `cleanup_board.py` no longer forces fiducial positions | It was silently dragging FID1/2/4 back to their Rev B spots (FID2 landed on C87 → DRC shorts). | `tools/cleanup_board.py` |
| K1 placed top front-right, not bottom under the channel rows | First placement blocked the only corridor BRU_AC had north to U5 (one open connection). | `generate_pcb.py` |

## Blockers and open items

| # | Item | Severity | Owner |
|---|---|---|---|
| 1 | **Physical 1590XX fit check** (unchanged from Rev B) — wall cutouts now: rear = barrel Ø7 at X≈17.5, USB-C 9.5 x 4 at X≈40, SD slot at X≈69; left = RJ45; right = 3.5 mm jack; front = 1/4-inch jack; lid = display window 85.5 x 56, SW2, SW3. No holes for SW1/RV1 any more. | Not blocking the PCB order | Jason |
| 2 | Confirm the purchased **MSP3526** (not MSP3520): 14-pin order, header 2.0 mm from the left edge, pin length (sets the standoff height, nominal 11 mm), 92.0 x 49.5 hole pattern. | Before drilling the lid / buying standoffs | Jason |
| 3 | **Relay sense**: K1 wiring assumes Omron G6K pins 2/7 = NC, 4/5 = NO, 3/6 = COM, coil 1 = +. Read from the datasheet drawing, not measured. If reversed, line out would be muted with the coil off — obvious at first power-up; fix = swap the two contact nets (schematic edit, re-route) or invert nothing in firmware (the NC/NO swap cannot be fixed in software because the default must be "pass"). | Bench check at bring-up | Jason |
| 4 | **Boost compensation**: R79/C80/C81 = 10 k / 4.7 nF / 47 pF is a textbook starting point for a 5 V → 10.45 V, ~0.2 A current-mode boost at 1.2 MHz, not a WEBENCH-optimised set. Check the 10.45 V rail with a 0 → 200 mA load step (scope: no ringing, < 5 % overshoot). Ripple at the LDO output should be unmeasurable. | Bench check | Jason |
| 5 | **USB data wires**: two ~20 mm wires from the Teensy's underside D+/D- pads to TP1/TP2. High-speed USB usually tolerates this; if enumeration is flaky, shorten the wires or fall back to full-speed (`USB_SPEED` in the firmware). | Bench check | Jason |
| 8 | **Battery / latch bench checks**: (a) with no external power the unit must be OFF until both buttons are held — an unpowered Teensy clamps its inputs, which is why D18/D19 isolate the switch nets; confirm Q3/Q4 gates sit at VBAT when idle; (b) BQ24074 temperature charging a flat pack in the closed box (thermal loop should hold it); (c) polarity of the pack's JST-PH pigtail vs J10 pin 1 before first connection; (d) the barrel does NOT charge — by design (BQ24074 OUT is 4.4 V regulated, a 9 V input would dissipate too much). | Bench check | Jason |
| 6 | Firmware is a spec, not code, for the new controls (`firmware/docs/REV-C-CONTROL-MODEL.md`): encoder modes in Settings, pad toggle, TPA6130A2 driver (0x60), FT6336U touch, ST7796U display init, USB-host mute logic, MTP. | Before the unit is usable | Firmware |
| 7 | Carry-overs: SW3 encoder 25/30 mm-height variant; SW4 no lid hole; 192 kHz TDM clocking note; CAT6 plug check. | Advisory | Jason / firmware |

## Verification basis

- KiCad 10.0.4 CLI on the routed board: DRC `--all-track-errors
  --schematic-parity --severity-error` → 0 / 0 / 0. ERC `--severity-all` →
  0 errors, 0 warnings. `check_panel_orientation.py` → all wall parts face
  their walls (J1 north +5.5 mm, J9 north −0.55 mm, J4 south, J2 west, J5
  east, Teensy SD end at the rear).
- Datasheets read for the new parts: BQ24074 (pin functions, EN1/EN2 table, ISET/ILIM/TS/TMR rules, 10.5 V input OVP, 4.4 V OUT regulation), TPS61175 (pin functions, FB 1.229 V,
  Rfreq table, inductor range 4.7-47 µH, SS), TPS7A4701 (strap-pin table,
  EN, NR, COUT ≥ 10 µF), TPA6130A2 (RTJ pinout, VIH 1.3 V, VDD 2.5-5.5 V,
  charge-pump caps), Omron G6K (coil 5 V 21 mA / 237 Ω, terminal drawing),
  LCDWiki MSP3525/3526 spec V1.0 (pinout, outline, holes, VCC 5 V, 95 mA
  backlight), PJRC Teensy 4.1 pinout card (USB-Device pads, VIN/VUSB cut).
- Not simulated: the boost loop (no SPICE model in the project). Not
  measured: relay contact sense, USB wire signal integrity, MSP3526 header
  pin length.

## False-positive / triage notes

- The first Rev C route reported 7 DRC errors around FID2 — a tooling bug
  (`cleanup_board.py` re-placing fiducials), not a layout problem; fixed.
- Freerouting 1.9.0 reports "completed" even when it leaves a connection
  open and only KiCad's DRC shows it; always read the DRC unconnected count.
