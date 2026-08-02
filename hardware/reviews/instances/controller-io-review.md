# Controller and I/O pin-level review — QuadPreRecorder Rev A

Scope: U8 Teensy 4.1, J3 TFT header, SW1/SW2/SW3, D4/D5 LEDs, J6/J7 DB-25 debug,
J2 chassis network. Source of truth: `/home/claude/review/pinmap.json`
(cross-validated against routed PCB, 0 mismatches). Design-intent docs:
`firmware/README.md`, `hardware/connector-pinout.md`, `hardware/architecture.md`,
prior reviews in `hardware/reviews/` (re-verified, not trusted).

Teensy 4.1 peripheral pin constraints are taken from the PJRC public pinout
(from reviewer knowledge, no cached datasheet — residual uncertainty is flagged
per-row as manual_review where it matters).

---

## 1. U8 Teensy 4.1 — power pins

| Pin | Net | Expected / check | Verdict |
|---|---|---|---|
| VIN | /TEENSY_VIN | Fed from +5V buck (TPS62160, ~4.98 V) via D3 SS14 (A=+5V, K=VIN), C46 10 uF local. VIN ~4.55–4.7 V after Vf; within Teensy 3.6–5.5 V VIN range. Diode orientation blocks USB 5 V from back-feeding the board +5V rail. | pass |
| 3V3A | /+3V3_D | Teensy 3.3 V regulator output sources the board digital 3.3 V rail (PCM1864 DVDD/IOVDD, PCM5102A DVDD, all logic pull-ups, J7 pin 3). Load estimate ~40–60 mA on top of Teensy's own draw; inside the ~250 mA module budget but unmeasured. | manual_review |
| 3V3B | /+3V3_D | Second 3.3 V pad tied to same rail. | pass |
| GND1/GND2/GND3 | /GND | All grounds tied to GND. | pass |
| VUSB link | (not in netlist — internal to module) | With barrel power applied, VIN ~4.6 V appears on the module VUSB net through the factory VIN–VUSB link and hence on the USB connector VBUS (back-feed into an attached host). D3 mitigates rail conflict but does NOT remove the need to cut the VIN–VUSB pad before simultaneous 9 V barrel + USB use, exactly as `power-path-review.md` states. Not verifiable from netlist (on-module trace). | warning / manual_review |

## 2. U8 Teensy 4.1 — peripheral pin capability vs firmware README

Teensy 4.1 fixed hardware assignments used for checking: SAI1 (I2S1): MCLK1=23,
BCLK1=21, LRCLK1=20, RX data IN1=8, TX OUT1A=7. SAI2 (I2S2): OUT2=2, LRCLK2=3,
BCLK2=4, MCLK2=33. LPSPI4 (SPI): MOSI=11, MISO=12, SCK=13, CS=10. Wire (I2C0):
SDA=18, SCL=19. All digital pins are GPIO/interrupt capable.

| Teensy pin | Net (pinmap) | firmware/README.md claim | Capability check | Verdict |
|---:|---|---|---|---|
| 2 | /DAC_DIN | DAC data | OUT2 = I2S2 TX data. Correct fixed pin. | pass |
| 3 | /DAC_LRCLK | DAC LRCLK | LRCLK2. Correct. | pass |
| 4 | /DAC_BCLK | DAC BCLK | BCLK2. Correct. | pass |
| 5 | /TOUCH_RST | **"Touch CS"** | Net is TOUCH_RST (FT6336G capacitive touch = I2C device with RST/INT, no chip select). Hardware is self-consistent; the firmware README label is stale (describes the old SPI/XPT2046 touch). GPIO use is valid either way. | **fail (documentation)** |
| 6 | /TFT_RST | TFT reset | GPIO. | pass |
| 8 | /ADC_TDM | ADC TDM data | IN1 = I2S1/SAI1 RX data — correct and the only TDM-in data pin option for SAI1 data line 0. | pass |
| 9 | /TFT_DC | TFT D/C | GPIO. | pass |
| 10 | /TFT_CS | TFT CS | CS/GPIO. | pass |
| 11/12/13 | /SPI_MOSI, /SPI_MISO, /SPI_SCK | SPI | LPSPI4 fixed pins. Correct. | pass |
| 18/19 | /I2C_SDA, /I2C_SCL | I2C SDA/SCL | Wire fixed pins; 4.7 k pull-ups (R44/R45) to +3V3_D present; shared by PCM1864 (addr pins MS/AD, MD0 grounded) and FT6336G on J3. | pass |
| 20/21/23 | /ADC_LRCLK, /ADC_BCLK, /ADC_MCLK | ADC LRCLK/BCLK/MCLK | LRCLK1/BCLK1/MCLK1 — correct SAI1 master-clock-out set for PCM1864 in slave mode. | pass |
| 22 | /TOUCH_IRQ | Touch IRQ | GPIO, interrupt capable. | pass |
| 28 | /REC_BUTTON | Record button | GPIO. | pass |
| 29/30/31 | /GAIN_A, /GAIN_B, /GAIN_PUSH | Encoder A/B/push | GPIO, interrupt capable. | pass |
| 32 | /PAD_SENSE | Pad sense | GPIO input; fed by 100k/47k divider (see SW1). | pass |
| 33 | /HP_ENABLE | Headphone enable | GPIO. Note pin 33 is also MCLK2; unused as MCLK because PCM5102A SCK (U9 pin 12) is grounded → DAC internal PLL from BCK. Consistent. | pass |
| 34 | /DAC_MUTE | DAC mute | GPIO → R61 100R → U9 XSMT (pin 17). See finding F4 on default state. | pass |
| 35 | /REC_LED | Record LED | GPIO → R55 1k → D5. ~1.4 mA, well within pad drive. | pass |
| 0,1,7,14–17,24–27,36–41 | unconnected | Not claimed | Explicit no-connects (incl. OUT1A pin 7 unused — no I2S1 TX, consistent with monitor path on I2S2). | pass |

No net is wired to a Teensy pin that cannot perform the claimed peripheral
function. The only mismatch is the README's pin-5 label (documentation).

## 3. J3 — MSP2834 TFT/CTP 14-pin header

Checked against `connector-pinout.md` J3 table and the LCDWiki MSP2834
(ILI9341 + FT6336G) module pin order from reviewer knowledge.

| Pin | Net (pinmap) | connector-pinout.md | Verdict |
|---:|---|---|---|
| 1 | /+5V | +5 V module input | pass |
| 2 | /GND | GND | pass |
| 3 | /TFT_CS | TFT chip select | pass |
| 4 | /TFT_RST | TFT reset | pass |
| 5 | /TFT_DC | TFT data/command | pass |
| 6 | /SPI_MOSI | TFT SPI MOSI | pass |
| 7 | /SPI_SCK | TFT SPI clock | pass |
| 8 | /TFT_LED | Backlight through 100 Ohm | pass — R56 100R fitted, +5V → R56 → pin 8 |
| 9 | /SPI_MISO | SPI MISO | pass |
| 10 | /I2C_SCL | CTP/I2C clock | pass |
| 11 | /TOUCH_RST | CTP reset | pass |
| 12 | /I2C_SDA | CTP/I2C data | pass |
| 13 | /TOUCH_IRQ | CTP interrupt | pass |
| 14 | unconnected | Display SD CS, DNP/NC in Rev A | pass |

Backlight sanity: if the module's LED pin feeds the white backlight LEDs
directly, I ≈ (5.0 − ~3.0 V) / 100R ≈ 20 mA — electrically safe, possibly
below full brightness for a 2.8-inch backlight (typ. 40–60 mA class); if the
module has an on-board backlight transistor, 100R is simply a base/gate feed
and also safe. Either way no overcurrent hazard. Backlight is hardwired
always-on from +5V with no MCU dimming — intentional per docs.
Verdict: pass, with manual_review on purchased-module internals (the pinout doc
itself mandates verifying the module revision).

Note: FT6336G I2C (nets on pins 10/12) is pulled up to +3V3_D — 3.3 V logic on
a +5 V-powered module is the normal MSP2834 arrangement (on-board 3.3 V LDO),
but confirm with the purchased module (manual_review, low risk).

## 4. SW1 / SW2 / SW3 — controls

| Item | Wiring found | Check | Verdict |
|---|---|---|---|
| SW1 pad select (SPDT slide) | Common (pin 2/B) = /PAD_SELECT; throws = /GND (pin 1) and /+9V (pin 3). PAD_SELECT drives CD4053 address pins U4.10/11 and U5.10/11 (VDD = 9 V logic) and J7 pin 21. | 0/9 V levels correct for CD4053 with VDD=9 V. During break-before-make transit, PAD_SELECT is weakly defined low via R42+R43 (147k to GND) — brief, acceptable. | pass |
| PAD_SENSE divider | /PAD_SELECT → R42 100k → /PAD_SENSE → R43 47k → GND; C33 100nF to GND; U8 pin 32. | 9 V × 47/147 = 2.88 V high level (safe < 3.3 V, > 2.31 V VIH); 0 V low. Divider current 61 uA. RC τ ≈ 3.2 ms — fine for a static sense. 9 V can never reach the Teensy pin. | pass |
| SW2 record button | SW2 pin 1 = /REC_BUTTON → R50 10k pull-up to +3V3_D, C47 100nF to GND; SW2 pin 2 = GND; U8 pin 28; J7 pin 22. | External pull-up present (not internal-pullup reliant); RC debounce τ = 1 ms. Cap discharged directly through contacts (no series R) — standard, minor contact-wear only. | pass |
| SW3 EC11 encoder | A = /GAIN_A (R51 10k→3V3_D, C48 10nF→GND), B = /GAIN_B (R52 10k, C49 10nF), C = GND, S1 = /GAIN_PUSH (R53 10k, C50 100nF), S2 = GND. | C common to GND: correct. External pull-ups on all three inputs. A/B RC τ = 100 us — appropriate for quadrature (does not blur fast detent edges); push τ = 1 ms. | pass |
| Firmware dependency | All four inputs are active-low with hardware pull-ups; firmware may use plain INPUT mode. No dependency on internal pull-ups. | noted | pass (manual_review only for firmware to not enable conflicting pull-downs) |

## 5. D4 / D5 LEDs

| Ref | Circuit | Current estimate | Verdict |
|---|---|---|---|
| D4 POWER BLUE | +5V → R54 2.2k → D4 → GND (always on) | (5.0 − ~2.9 Vf)/2.2k ≈ 0.95 mA | pass (deliberately dim indicator; modern blue 0603 visible at ~1 mA — cosmetic judgement only) |
| D5 RECORD RED | U8 pin 35 (/REC_LED, 3.3 V) → R55 1k → D5 → GND; also on J7 pin 24 | (3.3 − ~1.9 Vf)/1k ≈ 1.4 mA | pass (well under RT1062 pad drive; brightness adequate for red) |

## 6. J6 — analog debug DB-25 (all 25 pins vs connector-pinout.md)

| Pin | Net (pinmap) | Doc | Verdict |
|---:|---|---|---|
| 1 | /GND | GND | pass |
| 2 | /CHASSIS | CHASSIS | pass |
| 3 | /+9V | +9V | pass |
| 4 | /VREF | VREF | pass |
| 5 | /FLU_RAW | FLU_RAW | pass |
| 6 | /FLU_AC | FLU_AC | pass |
| 7 | /FLU_PAD | FLU_PAD | pass |
| 8 | /FLU_PRE | FLU_PRE | pass |
| 9 | /FLU_ADC | FLU_ADC | pass |
| 10 | /FRD_RAW | FRD_RAW | pass |
| 11 | /FRD_AC | FRD_AC | pass |
| 12 | /FRD_PAD | FRD_PAD | pass |
| 13 | /FRD_PRE | FRD_PRE | pass |
| 14 | /FRD_ADC | FRD_ADC | pass |
| 15 | /BLD_RAW | BLD_RAW | pass |
| 16 | /BLD_AC | BLD_AC | pass |
| 17 | /BLD_PAD | BLD_PAD | pass |
| 18 | /BLD_PRE | BLD_PRE | pass |
| 19 | /BLD_ADC | BLD_ADC | pass |
| 20 | /BRU_RAW | BRU_RAW | pass |
| 21 | /BRU_AC | BRU_AC | pass |
| 22 | /BRU_PAD | BRU_PAD | pass |
| 23 | /BRU_PRE | BRU_PRE | pass |
| 24 | /BRU_ADC | BRU_ADC | pass |
| 25 | /GND | GND | pass |

25/25 match. Note (info): pin 3 exposes unfused +9 V on an external connector —
documented and intended for bring-up, but a shorted debug lead bypasses only F1
upstream; acceptable for a debug port, keep leads short as the doc says.

## 7. J7 — digital/control debug DB-25 (all 25 pins vs connector-pinout.md)

| Pin | Net (pinmap) | Doc | Verdict |
|---:|---|---|---|
| 1 | /GND | GND | pass |
| 2 | /+5V | +5V | pass |
| 3 | /+3V3_D | +3V3_D | pass |
| 4 | /ADC_MCLK | ADC_MCLK | pass |
| 5 | /ADC_BCLK | ADC_BCLK | pass |
| 6 | /ADC_LRCLK | ADC_LRCLK | pass |
| 7 | /ADC_TDM | ADC_TDM | pass |
| 8 | /DAC_BCLK | DAC_BCLK | pass |
| 9 | /DAC_LRCLK | DAC_LRCLK | pass |
| 10 | /DAC_DIN | DAC_DIN | pass |
| 11 | /DAC_MUTE | DAC_MUTE | pass |
| 12 | /I2C_SDA | I2C_SDA | pass |
| 13 | /I2C_SCL | I2C_SCL | pass |
| 14 | /SPI_SCK | SPI_SCK | pass |
| 15 | /SPI_MOSI | SPI_MOSI | pass |
| 16 | /SPI_MISO | SPI_MISO | pass |
| 17 | /TFT_CS | TFT_CS | pass |
| 18 | /TFT_DC | TFT_DC | pass |
| 19 | /TOUCH_RST | **TOUCH_CS** "Touch controller chip select" | **fail (documentation)** — actual net is TOUCH_RST; no TOUCH_CS net exists anywhere in the design |
| 20 | /TOUCH_IRQ | TOUCH_IRQ | pass |
| 21 | /PAD_SELECT | PAD_SELECT | pass — but note this is a 0/9 V-swing signal on an otherwise 3.3/5 V connector; doc calls it "logic" without stating the 9 V level (warning, see F3) |
| 22 | /REC_BUTTON | REC_BUTTON | pass |
| 23 | /HP_ENABLE | HP_ENABLE | pass |
| 24 | /REC_LED | REC_LED | pass |
| 25 | /GND | GND | pass |

The debug taps on the serial audio nets sit on the Teensy side of the 33R
dampers (R46–R49, R57–R59), so probe capacitance is partially isolated from the
codec pins — correct side for a debug tap.

## 8. J2 / chassis network

| Item | Found | Expected (connector-pinout.md / architecture.md) | Verdict |
|---|---|---|---|
| J2 pins 1–4 | FLU/FRD/BLD/BRU_RAW | Capsule signals per doc | pass |
| J2 pins 6–9 | /GND ×4 | Independent capsule returns to PCB GND | pass |
| J2 pin 5 | /CHASSIS | CHASSIS, not audio ground | pass |
| C12 | 1nF 1kV C0G, CHASSIS↔GND, fitted | 1 nF coupling | pass |
| R4 | 1M, CHASSIS↔GND, fitted | 1 MOhm bleed | pass |
| R5 | 0R, CHASSIS↔GND, **DNP confirmed in schematic** (`(dnp yes)` on R5 symbol; R4/C12 fitted) | Optional 0R EMC bond, DNP by default | pass |
| Other CHASSIS members | D6–D9 PESD12VL1BA (input RAW→CHASSIS) and C13–C16 100pF (MIC nodes→CHASSIS), J6 pin 2 | Entry-point RF/ESD returns to shield node — consistent with the "controlled coupling at entry" strategy | pass |
| J2 shell | Footprint `DSUB-9_Socket_Horizontal_...EdgePinOffset9.40mm` has no shell/mounting-hole pads in the netlist; shell bond to CHASSIS relies on mechanical contact with the metal enclosure at the panel, as architecture.md describes | manual_review (mechanical — verify shell-to-enclosure contact at assembly; if the connector floats on standoffs the shell is bonded only via the mating cable) | manual_review |

## 9. Findings

| ID | Severity | Confidence | Item | Finding | Evidence |
|---|---|---|---|---|---|
| F1 | medium | high | firmware/README.md pin 5 | Firmware pin map labels Teensy pin 5 "Touch CS"; the net is /TOUCH_RST and the Rev A touch controller (FT6336G) is I2C with a reset pin, not SPI with CS. Firmware written to the README would toggle the touch reset as a chip select and hold the CTP in reset. | pinmap.json U8 pin 5 = /TOUCH_RST → J3 pin 11 (CTP reset); no TOUCH_CS net in the 149-net design; firmware/README.md line 39 |
| F2 | medium | high | connector-pinout.md J7 pin 19 | Doc lists pin 19 as TOUCH_CS "Touch controller chip select"; actual net is /TOUCH_RST. Documentation fail (same stale SPI-touch assumption as F1). | pinmap.json J7 pin 19 = /TOUCH_RST; connector-pinout.md line 100 |
| F3 | low | high | architecture.md / J7 pin 21 | architecture.md mermaid block says "ILI9341/XPT2046 touchscreen" (resistive SPI) while the Rev A target is ILI9341/FT6336G capacitive I2C (per README/connector-pinout and the wired nets). Also, J7 pin 21 (PAD_SELECT) is a 0/9 V signal described only as "pad select logic" — a user probing the "digital" connector may assume 3.3 V. Doc cleanup items. | architecture.md line 11; pinmap.json SW1.3 = /+9V, SW1.2 = /PAD_SELECT = J7.21 |
| F4 | low | medium | U9 XSMT default / reviews/datasheet-summary.md | DAC_MUTE_IC (PCM5102A XSMT) has R60 10k pull-UP to +3V3_D, so the DAC defaults to un-muted before firmware drives U8 pin 34. Safe against floating-input, and clock-error auto-mute plus HP_ENABLE's 100k pull-down (amp off) limit audible impact, but the line output can pop when I2S clocks start if firmware does not assert mute first; a pull-down would match the "hold mute until stream stable" intent with zero firmware dependence. Prior review's "mute is pulled to a defined state" is true but the chosen state is un-mute. | pinmap.json R60 (10k: +3V3_D↔/DAC_MUTE_IC), R61 (100R series), U9 pin 17; R64 100k HP_ENABLE→GND; firmware/README.md item 7 |
| F5 | low | medium | U8 VIN/VUSB | D3 (SS14, +5V→VIN) prevents USB 5 V from back-feeding the board rail, but with barrel power applied ~4.6 V still reaches the USB connector VBUS through the module's internal VIN–VUSB link; the documented requirement to cut the link before simultaneous barrel+USB use stands and cannot be verified from the netlist (on-module trace). | pinmap.json D3 (A=/+5V, K=/TEENSY_VIN), C46 10uF; power-path-review.md sequencing note |
| F6 | low | medium | +3V3_D budget | Teensy 3.3 V regulator sources PCM1864 DVDD/IOVDD, PCM5102A DVDD, all pull-ups and J7 pin 3. Estimated ~40–60 mA of external load — plausible within the module budget but unmeasured; prior review already requires bench confirmation. | pinmap.json U8 3V3A/3V3B = /+3V3_D; U7 pins 13/14, U9 pin 20 on /+3V3_D |
| F7 | info | medium | J3 pin 8 backlight | R56 100R from +5V hardwires the backlight on; ~20 mA if the module LED pin is a direct LED feed (safe, possibly not full brightness), harmless if the module has an on-board driver. No dimming control. Verify against the purchased MSP2834 revision. | pinmap.json R56 (+5V↔/TFT_LED), J3 pin 8 |
| F8 | info | high | D4 | Power LED runs at ~0.95 mA (2.2k from 5 V, blue). Visible but dim; cosmetic choice only. | pinmap.json R54 2.2k, D4 |

## 10. Not verified / limitations

- Teensy 4.1 pin-peripheral assignments (I2S1/I2S2/SPI/I2C fixed pins) checked
  from reviewer knowledge of the PJRC pinout, not a cached datasheet; the
  matches are exact and self-consistent, but treat the capability column as
  high-confidence rather than document-verified.
- On-module facts are unverifiable from the netlist: the VIN–VUSB link (F5),
  Teensy 3.3 V regulator current headroom (F6), and USB VBUS behavior.
- MSP2834 module internals (backlight drive topology, on-board 3.3 V LDO for
  the FT6336G, exact 14-pin order of the purchased revision) — the design's own
  doc mandates verifying the purchased module.
- PCM5102A XSMT polarity/behavior on clock loss recalled from the TI datasheet,
  not a cached copy (F4 confidence: medium).
- Mechanical shell-to-enclosure chassis bonding of J2/J6/J7 (no shell pads in
  netlist).
