# Rev C control model (hardware changes the firmware must absorb)

Written 2026-09-08 against the Rev C schematic (`tools/generate_schematic.py`).
Rev C removes two physical controls (pad toggle SW1, volume pot RV1) and adds
USB-C, a line-out mute relay, an I2C headphone amplifier and a capacitive
touchscreen. This file is the contract between the board and `lib/qpr_ui`.

## Battery and soft power (added 2026-09-08)

| Teensy pin | Net | Notes |
|---:|---|---|
| 24 | `KEEP_ON` output | High holds the boost converter enabled through D15. LOW at reset. Assert only after the power-on hold (below); drop it to power off. |
| 16 | `BAT_SENSE` analog in | 1 M / 1 M divider from VBAT: 4.20 V reads 2.10 V (ADC ~651/1023 at 3.3 V ref). Read with a slow sample rate; the 100 nF cap holds the node. |
| 17 | `CHG_STAT_N` input | BQ24074 /CHG, open drain, 100 k pull-up: LOW = charging, HIGH = done / not charging. |
| 25 | `PGOOD_N` input | BQ24074 /PGOOD: LOW = valid USB input present. |

Hardware: a 1S LiPo (906090, 5000 mAh, with PCM) on J10. The BQ24074 charges it from USB only at 0.74 A (about 7 h from empty; it thermally self-throttles). The 9 V barrel powers the unit but does not charge. Battery feeds the boost through D14; the unit runs down to about VBAT 3.0 V electrically.

**Power-on (battery, no external power).** Holding RECORD and the encoder push together turns the boost converter on in hardware (Q3/Q4 in series pull BOOST_EN high). The Teensy boots within ~300 ms. Firmware then:
1. Reads both buttons. If either is released before **2.0 s** have elapsed since boot, do nothing — the rails collapse when the user lets go (KEEP_ON is still low).
2. At 2.0 s held: set `KEEP_ON` HIGH, show the boot screen, continue normal start-up. Ignore both buttons until both have been released (so the hold does not also trigger RECORD or an encoder mode change).

**Power-off.** While running, RECORD + encoder push held for 2.0 s: stop any take in progress and close the files, save settings, show "Powering off", set `KEEP_ON` LOW. On battery the unit dies when the buttons are released. On USB or barrel power BOOST_EN is held by D16/D17, so instead enter standby: backlight off, DAC and HP amp muted, wait for the combo again to wake. Any single button keeps its normal function; only the combination is the power gesture.

**Gauge and cutoff.** Show a battery icon from `BAT_SENSE` (4.2 V full, 3.5 V ~20 %, 3.3 V empty), a plug icon when `PGOOD_N` is low, and a charging bolt while `CHG_STAT_N` is low. At VBAT ≤ 3.3 V with no external power: warn; at ≤ 3.2 V perform the power-off sequence (the pack's PCM would otherwise cut at ~2.5 V mid-write).

## Pin changes vs Rev B

| Teensy pin | Rev B | Rev C | Notes |
|---:|---|---|---|
| 5 | — | `LINE_MUTE` output | High = energise relay K1 = line out muted (jack tips grounded). Default LOW at boot. |
| 14 | — | `CTP_RST` output | FT6336U reset, active low. Hold low >= 5 ms at boot, then high, wait 300 ms before first I2C access. |
| 15 | — | `VBUS_SENSE` analog in | 100 k / 47 k divider: 5 V VBUS reads ~1.60 V (ADC ~496/1023 at 3.3 V ref). > 1.0 V = USB power present. |
| 24 | `TOUCH_CS` | `KEEP_ON` output | Soft-power latch hold (see above). |
| 32 | `PAD_SENSE` input | `PAD_CTRL` output | High = Q1 on = PAD_SELECT pulled low = pad IN (-9.7 dB). Low/floating = direct. Set before un-muting the DAC at boot. |
| 22 | `TOUCH_IRQ` | `TOUCH_IRQ` | Now the FT6336U INT (active low on touch). |
| 33 | `HP_ENABLE` | `HP_ENABLE` | Now the TPA6130A2 /SD pin (high = amp powered). 100 k pull-down. |

## Devices on the I2C bus (Wire, pins 18/19, 3.3 V pull-ups)

| Device | Address | Use |
|---|---|---|
| PCM1864 ADC | as before | PGA gain, clocks |
| FT6336U touch | 0x38 | Touch points (same driver family as the Rev A FT6336G; Adafruit FT6206-style register map) |
| TPA6130A2 headphone amp | 0x60 | Reg 0x01: HP_EN_L/R (bits 7,6), mode bits; Reg 0x02: MUTE_L/R (bits 7,6) + 6-bit volume (0 = -59.5 dB .. 63 = +4 dB). |

Display driver: ST7796U over SPI (`ST7796_t3` / the `ILI9488_t3` family with
the ST7796 init table); 320 x 480, `SPI_SCK`/`MOSI`/`MISO`, `TFT_CS` 10,
`TFT_DC` 9, `TFT_RST` 7. Backlight is hard-wired on.

## Encoder behaviour

- Default: the encoder is **GAIN only** (1 dB per detent, all four channels
  via the PCM1864 PGA), exactly as Rev B. A short press does nothing unless a
  second mode is enabled.
- Settings > Encoder: three toggles — **Mic gain** (always on, cannot be
  disabled), **HP volume**, **Line trim**. A short press cycles through the
  *enabled* modes; the current mode shows as an icon/label next to the value
  the knob is changing. A long press (>= 600 ms) always jumps back to GAIN.
- **HP volume** mode writes the TPA6130A2 volume register (64 steps, one per
  detent). Turning below the bottom step sets MUTE and drops `HP_ENABLE`
  (amp powered down, icon shows HP OFF). The first detent up re-enables it.
- **Line trim** mode moves the digital OUT trim (both outputs, as in Rev B).
- Touchscreen equivalents remain: HP on/off + HP volume slider, OUT trim ±.

## Pad

- `PAD` is a touchscreen toggle (and optionally a long-press item). Firmware
  keeps the state in the settings file and applies it *before* the DAC and
  headphone amp are un-muted at boot.
- The displayed total gain folds the pad in exactly as Rev B did with the
  switch sense.

## Headphone amplifier on/off

- `HP_ENABLE` (pin 33) high powers the TPA6130A2; low is shutdown (~0.4 uA).
  This is a mute/no-hiss convenience, not a battery saver — there is no
  battery. Show a small HP icon: ON (volume value), OFF (crossed).

## USB-C, power source and the line-out mute

- `VBUS_SENSE` > 1.0 V: USB power present. Show a USB plug icon; with no
  USB power show a barrel icon (9 V adapter). Both present: barrel wins
  electrically; show both.
- USB **host enumerated** (Teensy `usb_configuration` != 0 / `USBDevice`
  configured event): a computer is attached, its ground is now tied to ours,
  and a line-out cable to an interface on the same computer forms a loop.
  Firmware:
  1. sets `LINE_MUTE` high (relay K1 grounds the 1/4-inch tips),
  2. shows a persistent banner: **"LINE OUT MUTED — computer connected
     (ground loop). Tap to un-mute anyway."**,
  3. keeps headphones working (they are not muted),
  4. on override, drops `LINE_MUTE` and changes the banner to a small
     warning icon until the host disconnects.
- Charger / power bank (VBUS present, never enumerates): never mutes.
- USB disconnect: `LINE_MUTE` low, banner cleared.
- MTP: expose the SD card as a drive (`MTP_Teensy`). Recording is blocked
  while a host has the card mounted; show "USB file transfer" state.
- Firmware update: standard Teensy Loader over the same cable.

## Boot order

1. `PAD_CTRL`, `LINE_MUTE`, `HP_ENABLE`, `KEEP_ON` = LOW (outputs), `CTP_RST` low; start the 2 s power-on hold timer (battery) — see Battery and soft power.
2. Load settings (pad, HP volume, encoder modes, last gain).
3. Bring up display, release `CTP_RST`, init touch.
4. Apply pad, ADC gain, DAC un-mute, then HP amp volume + enable.
5. Start USB, register the configured/disconnect callbacks that drive the
   mute logic above.
