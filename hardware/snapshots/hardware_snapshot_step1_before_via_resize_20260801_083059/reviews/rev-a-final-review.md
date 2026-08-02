# Rev A final pre-order review — consolidated report

Date: 2026-07-25. Method: netlist pin→net extraction cross-validated against the
routed PCB (527 pads, 0 mismatches), per-IC datasheet reviews using the cached
datasheet text extracts, fab-outline orientation analysis, and the 1590F
enclosure stackup study. Per-instance evidence: `power-stage-review.md`,
`afe-review.md`, `adc-review.md`, `dac-hp-review.md`, `controller-io-review.md`
(same folder). The kicad-schematic-review helper scripts were unavailable in
this environment; equivalent extraction tooling was used and is described in
each instance file.

## A. Blockers (change before ordering)

1. **192 kHz four-channel TDM is not achievable as documented** (high,
   PCM1864 datasheet). The PCM1864 TDM frame is fixed at 256 BCK/frame, so
   fs=192 kHz forces BCK=49.152 MHz — at the chip's 50 MHz limit and beyond
   what the Teensy SAI and the 33R/DB-25-stub wiring can carry. The
   "four 32-bit slots" description in architecture.md trips the PCM1864
   BCK-ratio detector. The copper itself is fine for **96 kHz 4-ch TDM**
   (BCK 24.576 MHz) or 192 kHz stereo. The DOUT2 fallback (2×I2S at 192 kHz)
   is unavailable because GPIO0-3 (pins 19-22) are unconnected. Decide: accept
   96 kHz/4-ch (recommended for Rev A) or respin the digital audio wiring.
2. **J4 (NRJ6HF 1/4" line out) faces the wrong way at the copper level.**
   Fab outline: body X 117.65–141.95, threaded bushing pointing +X (east,
   parallel to the bottom wall). It cannot exit the bottom wall. Rotate 90°
   (bushing +Y/south) and position so the bushing passes through the wall with
   the body face at the wall inner surface.
3. **RV1 (headphone volume) faces the wrong way at the copper level.**
   Fab outline: body at Y 150–159.55 with shaft+bushing extending north to
   Y=130 — parallel to the left wall. Rotate so the shaft points −X (west)
   through the left wall.
4. **SW1 (pad switch) cannot reach any panel and is the wrong part class.**
   It is a C&K OS102011MS2QN1 micro slide (8.6×4.3 mm body, 2 mm knob, 7.5 mm
   total height) at mid-board (140,78) — 9 mm below the lid, nowhere near a
   wall. Owner decision 2026-07-25: relocate to the right wall between J6 and
   J7 (free band board-Y ≈ 70–105). Recommended implementation: replace with a
   panel-bushing SPDT toggle through the right wall (centerline depth ~8.5 mm
   below rim), either wired to PCB pads or a PCB-pin right-angle bushing
   toggle at the board edge. A top-actuated slide cannot traverse the ~5.5 mm
   wall.
5. **H5–H8 TFT holes wrong** (78×42 vs true MSP2834 76.08×44) — see
   `../enclosure-stackup-and-templates.md`.
6. **J2 BOM part number** LD09S13A4GV00LF is EU-style (2.54 mm rows); the
   routed footprint needs US-style **LD09S33E4GV00LF**.
7. **SW2 record button** cannot reach the lid (7.3 vs 16.5 mm) — swap to
   B3F-5150 (17.5 mm, same footprint) + keycap.

## B. Orientation verdicts for parts flagged in the 3D view

| Part | Copper (fab outline) | 3D model in STEP |
|---|---|---|
| J1 barrel | CORRECT — nose −X, 3.5 mm nose section past left edge | mis-rotated (cosmetic) |
| J5 3.5 mm | CORRECT — nose −X, tip 0.7 mm past left edge | mis-rotated (cosmetic) |
| J2 DE-9 | CORRECT — protrudes −X | OK |
| J6/J7 DB-25 | CORRECT — protrude +X past right edge | OK |
| J4 1/4" | **WRONG — bushing points east, parallel to bottom wall** | also wrong |
| RV1 volume | **WRONG — shaft points north, parallel to left wall** | model looks right, copper is not |
| SW2 button | orientation N/A (symmetric); height issue stands | lying on its side (cosmetic) |

The vendor STEP models merged with wrong rotations make the exported
QuadPreRecorder-RevA.step unreliable for CAD interference checks until fixed.

## C. Warnings (fix or accept knowingly)

- Electret bias R6-R9 fed from the raw +9V input rail shared with the buck
  converter input — no RC bias filter despite docs saying "filtered"; buck
  noise reaches the capsules ahead of +20 dB gain. Add an RC (e.g. 100R+100uF)
  ahead of the bias resistors. (afe-review)
- PCM5102A XSMT is pulled UP (R60 10k to 3V3) — DAC un-muted before firmware
  boots; line-out pop risk. Pull DOWN instead and let the Teensy raise it.
  (dac-hp-review, controller-io-review)
- PCM5102A recommended output filter (470R + 2.2nF) absent on line out; only
  100R series fitted. Out-of-band noise on J4. (dac-hp-review)
- PAD_SELECT is a 0/9 V swing exposed on "digital" debug J7.21 with no series
  resistance — an external 3.3 V driver would fight the 9 V rail. Add series R
  or document loudly. (afe-review)
- R38-R41 100k bias-to-GND on the ADC side of the coupling caps fight the
  PCM1864's internal AVDD/2 self-bias (~150 mV offset) — recommend DNP.
  (adc-review)
- TPS62160 in DGK (no thermal pad): ~65-75°C rise at 0.8 A worst case on this
  board; fine on the bench, warm in a closed box — consider the DSG variant.
  (power-stage-review)
- TLE2426 with 47uF directly on VREF is in/near the datasheet's unstable
  load-capacitance region — verify stability at bring-up or add series R.
  (power-stage-review)
- C1 input electrolytic 16 V vs SMBJ12A clamp ~19.9 V during surge — use 25 V.
- RV1 wiring may reverse rotation/taper depending on which Alps terminal is
  pad 1 of the custom footprint — verify against the Alps drawing (dac-hp).
- J4 TS/mono plug shorts ring output through 100R — acceptable, note it.
- Docs: firmware README + connector-pinout call J7.19/U8.5 "TOUCH_CS" but the
  net is TOUCH_RST (FT6336G is I2C, no CS); architecture.md still says
  XPT2046. Fix docs. (controller-io-review)

## D. Verified-good highlights

Buck FB divider = 4.985 V; LC choice inside TI's table; TPS7A20 fed from 5 V
(in range, 1.7 V headroom); polarity protection topology sound; Teensy on
4.65 V via D3; U6 all 14 pins correct, gain 20.08 dB, VCM inside range; CD4053
single-supply wiring correct, select levels legal (9 V logic from SW1, Teensy
senses via 100k/47k divider = 2.88 V); pad = −9.72 dB by design topology; ESD
parts correct; I2C pull-ups 4.7k to 3.3 V; PCM1864 IOVDD=3.3 V; unused ADC
inputs correctly floating per datasheet; coupling caps flat to 20 Hz;
PCM5102A 3-wire BCK-PLL mode strapping correct; TPA6132A2 input caps, gain
straps, charge pump, EN pull-down, exposed pad all per datasheet; Teensy I2S1/
I2S2/SPI/I2C nets all on hardware-capable pins; J3 header matches the MSP2834
order; J6 25/25 and J7 24/25 match the pinout doc; SW2/SW3 debounce networks
present; chassis network (1 nF/1 M, R5 DNP) as documented.

## E. Not verified (bench/purchase items)

Vendor ratings for F1/L1/D1/D2/D3/J1 (no datasheets cached); TLE2426 stability
curve values (graphics not in text extract); actual load currents; Teensy SAI
max BCK (NXP datasheet not cached); RV1 terminal orientation; SW1 replacement
part choice; MSP2834 module internals; enclosure boss depth.
