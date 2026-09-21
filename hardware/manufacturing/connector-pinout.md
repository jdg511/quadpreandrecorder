# Connector pinout (Rev C, 2026-09-08)

Rev C changes from Rev B: an internal LiPo battery (J10) with a USB charger and a two-button soft-power latch; the 9 V barrel moved from the front wall to the
REAR-LEFT wall; a USB-C receptacle (J9) was added on the rear wall for 5 V
power, SD-card file transfer and firmware updates; the pad toggle (SW1) and
the headphone volume pot (RV1) are gone (both are screen/firmware controls
now); the display is the LCDWiki **MSP3526** 3.5-inch capacitive module; the
line output passes through a mute relay (K1). Everything else is unchanged.

## J2 — ambisonic microphone RJ45/CAT6 jack (left wall)

Shielded 8P8C jack, Amphenol RJHSE-5380. The mating cable is a standard
shielded CAT6 cord with an 8P8C plug. Viewed looking into the jack:

| Pin | Net | Cable function |
|---:|---|---|
| 1 | FLU_RAW | Front-left-up hot (signal, carries the bias) |
| 2 | FLU_RAWC | Front-left-up cold (return / balanced minus) |
| 3 | FRD_RAW | Front-right-down hot |
| 6 | FRD_RAWC | Front-right-down cold |
| 4 | BLD_RAW | Back-left-down hot |
| 5 | BLD_RAWC | Back-left-down cold |
| 7 | BRU_RAW | Back-right-up hot |
| 8 | BRU_RAWC | Back-right-up cold |
| SH (shell) | CHASSIS | Cable shield; bonds to the metal shell at both ends |

Rev C3 (2026-09-12): the four cold pins are no longer hard-wired to GND.
Each pair now lands on its own input (RAW = hot, RAWC = cold), both legs get
the same 100R / 100 pF / PESD12VL1BA RF protection, and a CD4053 switch
(U4/U5 spare section, U15) decides what the cold leg does:

* **Electret mode** (bias set to 5 V or 9 V, the power-up default): the
  switch grounds the cold leg on the board, so the capsule's bias current
  has a low-impedance return exactly as in Rev C. The bias rides on the
  hot leg through 4.7k.
* **Dynamic / balanced mode** (bias off): the switch opens and the cold leg
  feeds the second half of a two-op-amp instrumentation stage (U16 + the
  existing U6 unit), so the pair is a true balanced input: +20.1 dB, CMRR
  (SPICE, worst-case 0.1 % resistors, 300 ohm source) 67 dB from 100 Hz to
  1 kHz, 58 dB at 20 kHz, 56 dB at 50 Hz with the coupling caps at their
  10 % limits; input noise 18.8 nV/sqrt(Hz), EIN -109 dBu. Any passive dynamic mic wired pin
  2 hot / pin 3 cold onto one pair works; nothing on the board applies a
  voltage in this mode.

The mic bias itself is one global setting for all four channels (off, 5 V
or 9 V from the touchscreen; Q6/Q8 high-side switches into the R67/C66
filter). Never choose 5 V or 9 V with a dynamic mic plugged in.

Do not tie the shield to any cold leg inside the microphone. The PCB couples
CHASSIS to circuit ground through 1 MOhm and 1 nF; `R5` (DNP) can bond it
directly if EMC testing calls for it.

## J1 — 9 V DC barrel (rear-left wall)

CUI PJ-102AH, 5.5 x 2.1 mm, centre positive, regulated 9 V / 1 A adapter.
Pin 1 = +9V_IN, pins 2/3 = GND. Protected by a 750 mA PTC and OR'd with the
USB input through a Schottky. Either input alone runs the unit; with both
connected the barrel supplies the load.

## J9 — USB-C (rear wall)

HRO TYPE-C-31-M-12 16-pin USB 2.0 receptacle. 5 V only: CC1/CC2 carry 5.1 k
pull-downs (a 5 V sink), so any charger, power bank or computer port works
and no PD negotiation is needed. The board boosts 5 V to 10.45 V and then
regulates a clean 9 V analog rail, so the recorder runs fully from USB
(about 400-450 mA at 5 V).

| Pin(s) | Net | Function |
|---|---|---|
| A4, A9, B4, B9 | VBUS | 5 V in, 1.1 A PTC (F2) then OR-ing Schottky (D10) |
| A5 / B5 | USB_CC1 / USB_CC2 | 5.1 k to GND each |
| A6, B6 | USB_DP | D+ (through USBLC6-2SC6 ESD) to TP1 |
| A7, B7 | USB_DM | D- (through USBLC6-2SC6 ESD) to TP2 |
| A8, B8 | — | SBU, no connect |
| A1, A12, B1, B12 | GND | |
| SH | CHASSIS | Shell; same 1 MOhm / 1 nF bond as the RJ45 shell |

**Data path.** The Teensy 4.1's USB-device D+/D- are only available on its
micro-B connector and on two small pads on its underside (PJRC pinout card,
"USB Device": VUSB, D-, D+, next to pins 0/GND). Rev C brings J9's D+/D- to
two 2 mm pads on the board's BOTTOM side (TP1 = D+, TP2 = D-, just west of the
Teensy socket, about 18 mm from the SD end) so that two short wires (aim for
under 20 mm, kept together) join them to the Teensy pads before the Teensy is
plugged into its sockets. GND is shared through the socket pins. Never plug a
cable into the Teensy's own micro-B while J9 is in use — they are the same
two signals. Cut the Teensy's VIN-VUSB link (the board powers VIN from +5V).

**Firmware behaviour.** VBUS_SENSE (Teensy pin 15, 100 k / 47 k divider,
1.6 V at 5 V) tells the screen which supply is present. When the Teensy
enumerates as a USB device (a computer, not a charger, is attached) the
firmware energises the line-out mute relay K1 and shows a warning, because
computer ground + line-out ground = ground loop; a charger or power bank
never mutes. The user can override on screen. USB also carries MTP (SD card
appears as a drive) and Teensy Loader firmware updates.

## J3 — LCDWiki MSP3526 TFT / capacitive-touch socket

1 x 14 female socket (Sullins PPTC141LFBN-RC, 8.5 mm). The module's own male
header plugs into it; the module rides on 11 mm M3 standoffs (socket 8.5 mm
+ header body 2.5 mm — measure the real module before ordering standoffs).
Pin 1 is at the REAR end of the socket (board Y = 19.24), pin 14 toward the
front (Y = 52.26), socket at X = 25.0.

| Pin | Module name | Net | Pin | Module name | Net |
|---:|---|---|---:|---|---|
| 1 | VCC | +5V | 8 | LED | TFT_LED (100 Ohm from +5V) |
| 2 | GND | GND | 9 | SDO (MISO) | SPI_MISO |
| 3 | LCD_CS | TFT_CS (Teensy 10) | 10 | CTP_SCL | I2C_SCL (Teensy 19) |
| 4 | LCD_RST | TFT_RST (Teensy 7) | 11 | CTP_RST | CTP_RST (Teensy 14) |
| 5 | LCD_RS (D/C) | TFT_DC (Teensy 9) | 12 | CTP_SDA | I2C_SDA (Teensy 18) |
| 6 | SDI (MOSI) | SPI_MOSI (Teensy 11) | 13 | CTP_INT | TOUCH_IRQ (Teensy 22) |
| 7 | SCK | SPI_SCK (Teensy 13) | 14 | SD_CS | no connect |

Module facts (LCDWiki spec CR2023-MI2434 V1.0): 3.5-inch IPS 320 x 480,
ST7796U over 4-wire SPI, FT6336U capacitive touch over I2C, VCC 5.0 V with
on-board level conversion (3.3 V logic OK), backlight 95 mA, PCB 98.0 x 55.5
mm, mounting holes 92.0 x 49.5 mm (3.0 mm in from each edge, 3.2 mm), header
2.0 mm in from the left short edge. Verify the purchased module against this
before drilling the lid.

## J10 — battery (bottom side, front-right)

JST PH 2-pin (B2B-PH-K-S), pin 1 = VBAT (+), pin 2 = GND. Mates a 3.7 V
1S LiPo pouch, 906090 size (9 × 60 × 90 mm, 5000 mAh) **with its own
protection circuit (PCM)** and a JST-PH pigtail — check the pigtail's polarity
against the pin-1 marking, vendors are not consistent. The pouch lies on the
box floor under the right half of the board (x 80–140, y 15–105), clear of
the Teensy, held with foam tape. Charged from USB-C only (BQ24074, 0.74 A,
~7 h); the 9 V barrel runs the unit but does not charge. Runtime about
6–7 hours per charge at full brightness.

Power gesture on battery: hold RECORD + encoder push 2 s (on and off).

## TP1 / TP2 — USB data wire pads (bottom side)

TP1 = USB_DP, TP2 = USB_DM. 2.0 mm square pads at (56.5, 18.0) and
(56.5, 21.5), bottom side. Wire to the Teensy 4.1 underside "USB Device" D+
and D- pads (see J9).

## J6 / J7 test headers: removed in Rev C3 (2026-09-12)

The Rev B 2x13 analog and digital test headers are gone. They sat 6.5 mm apart
on the rear edge and forced all 20 analog stage nets and all 21 clock/bus nets
to cross the board side by side (audio-rule audit, check 2:
`hardware/reviews/audio-rules-check-revC2.md`). Probe any stage at its
component pads instead; every stage node has at least one 0603/1812 pad on
the top side of the channel rows. R68 (the 1 k PAD_DBG series protector)
went with them.

## TP3-TP14 probe pads (Rev C3, bottom side, 1.5 mm bare copper)

| Ref | Net | Position (mm) |
|---|---|---|
| TP8 | GND | 81.0, 36.5 |
| TP3 | ADC_MCLK | 84.5, 36.5 |
| TP4 | ADC_BCLK | 88.0, 36.5 |
| TP5 | ADC_LRCLK | 91.5, 36.5 |
| TP6 | ADC_TDM | 95.0, 36.5 |
| TP7 | ADC_DOUT2 | 98.5, 36.5 |
| TP13 | GND | 82.5, 42.2 |
| TP9 | DAC_BCLK | 86.5, 42.2 |
| TP10 | DAC_LRCLK | 90.5, 42.2 |
| TP11 | DAC_DIN | 94.5, 42.2 |
| TP12 | +3V3_DC | 84.0, 63.0 |
| TP14 | GND | 81.0, 59.5 |

The battery pouch lies under the right half of the board (x 80-140), so lift
it (or probe before fitting it) to reach the ADC and DAC rows.

## Teensy 4.1 pin map (Rev C)

| Pin | Net | Pin | Net |
|---:|---|---:|---|
| 2 | DAC_DIN | 22 | TOUCH_IRQ |
| 3 | DAC_LRCLK | 23 | ADC_MCLK |
| 4 | DAC_BCLK | 28 | REC_BUTTON |
| 5 | LINE_MUTE (K1 relay, high = mute) | 29 | GAIN_A |
| 6 | ADC_DOUT2 | 30 | GAIN_B |
| 7 | TFT_RST | 31 | GAIN_PUSH |
| 8 | ADC_TDM | 32 | PAD_CTRL (high = pad in) |
| 9 | TFT_DC | 33 | HP_ENABLE |
| 10 | TFT_CS | 34 | DAC_MUTE |
| 11 | SPI_MOSI | 35 | REC_LED |
| 12 | SPI_MISO | 36-40 | NAV_UP/DOWN/LEFT/RIGHT/PUSH (SW4, internal) |
| 13 | SPI_SCK | 14 | CTP_RST |
| 18 | I2C_SDA | 15 | VBUS_SENSE (analog, 1.6 V at 5 V) |
| 19 | I2C_SCL | 20 | ADC_LRCLK |
| 21 | ADC_BCLK | 24 | KEEP_ON (soft-power hold) |
| 16 | BAT_SENSE (VBAT/2) | 17 | CHG_STAT_N (charger /CHG) |
| 25 | PGOOD_N (charger /PGOOD) | 0 | MIC5_CTRL (high = 5 V mic bias) |
| 1 | MIC9_CTRL (high = 9 V mic bias) | 41 | COLD_CTRL (high = cold legs released, balanced/dynamic mode) |
| 26, 27 | unused | | |

I2C addresses on the shared bus: PCM1864 (ADR pin), FT6336U 0x38, TPA6130A2
0x60.
