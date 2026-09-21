# Requirements and assumptions (Rev C, 2026-09-08)

## Required behavior

- Capture four two-terminal electret capsules arranged as a vertical first-order
  ambisonic tetrahedron.
- Bring four signal/return pairs and one overall cable shield into one
  board-mounted 9-contact connector.
- Apply one matched -10 dB pad to all four channels, switched from the
  touchscreen/firmware (Rev C; Rev A/B used a panel toggle).
- Provide matched low-noise JFET-input gain with a maximum total gain between
  40 dB and 60 dB. One knob changes all four channels together.
- Convert four channels simultaneously at 192 kHz and 24 bits or better.
- Record four mono WAV files to microSD. Recording set `n` is named
  `FLUn.wav`, `FRDn.wav`, `BLDn.wav`, and `BRUn.wav`.
- Display four input meters and recorder state on a small TFT touchscreen.
- Decode the four-channel vertical-tetrahedral signal to stereo binaural audio
  in real time.
- Provide a board-mounted 1/4-inch stereo line output (with a relay mute
  that engages while a USB host is attached, to break ground loops) and a
  board-mounted 1/8-inch stereo headphone output with a digitally controlled
  headphone volume (encoder / touchscreen).
- Fit a standard Hammond enclosure on a two-layer PCB with board-mounted user
  connectors and controls.
- Run from either a 9 V barrel adapter or 5 V USB-C; expose the SD card over
  USB (MTP) and accept firmware updates over the same USB-C port.
- Run 5–6 hours from an internal rechargeable battery, charged over USB-C,
  switched on and off by holding RECORD and the encoder push together.
- Provide two internal test headers (analog and digital/control) for bench
  debugging. (Rev A specified these as panel-mounted DB-25 sockets; Rev B
  replaced them with internal 2x13, 2.54 mm headers — see the Rev B note
  below.)

## Decisions (Rev C column supersedes)

| Item | Rev A implementation |
|---|---|
| Microphone connector | Shielded 8P8C (RJ45/CAT6) jack, Amphenol RJHSE-5380, four twisted pairs plus shell |
| RJ45 pinout | Pins 1/2 FLU signal/return, 3/6 FRD signal/return, 4/5 BLD signal/return, 7/8 BRU signal/return; shell = CHASSIS (shield) |
| Capsule bias | Individually filtered +9 V bias through 4.7 kOhm; returns join quiet analog ground at the input |
| Pad | Four matched 68 kOhm/33 kOhm dividers selected by two CD4053B triple SPDT analog muxes; 9.7 dB nominal. Rev C: PAD_SELECT (0/9 V) driven by a 2N7002 level shifter from Teensy GPIO with a 10 k pull-up so power-up = direct |
| JFET stage | One OPA1654 quad FET-input op amp, 20 dB fixed analog gain |
| Gain control | PCM1864 four-channel PGA, programmed equally from one EC11 encoder; total range 8 dB to 52 dB including ADC PGA and fixed stage |
| ADC | PCM1864, four simultaneous channels, 192 kHz, 24-bit TDM output |
| Controller | Teensy 4.1 module, 600 MHz Cortex-M7, native 4-bit SDIO microSD, two I2S/TDM ports |
| DAC | PCM5102A stereo I2S DAC, operated at 48 kHz or higher |
| Headphones | Rev C: TPA6130A2 DirectPath stereo amplifier with I2C volume (-59.5..+4 dB, 64 steps) and software mute, fed from LINE_L/R; no pot. (Rev A/B: TPA6132A2 after a dual 10 kOhm pot) |
| Display | Rev C: LCDWiki MSP3526 3.5-inch IPS 320x480, ST7796U over SPI, FT6336U capacitive touch over I2C, 14-pin 2.54 mm header into a female socket on the board, 11 mm standoffs. (Rev B specified the MSP3520, whose touch is actually resistive/XPT2046) |
| Debug connectors | None (Rev C3). The Rev B internal 2x13 test headers J6/J7 were removed because they dragged every analog node across the board beside every clock; probe at component pads |
| Power | Rev C: 9 VDC centre-positive barrel (rear wall) OR 5 V USB-C (rear wall), Schottky OR'd into a TPS61175 boost (10.45 V, 1.2 MHz) feeding a TPS7A4701 ultralow-noise LDO for the 9 V analog rail and the TPS62160 5 V buck; low-noise 3.3 V analog LDO unchanged. USB draw ~400-450 mA at 5 V |
| Battery | 1S LiPo 906090 5000 mAh pouch with PCM on J10 (JST-PH), on the box floor under the right half. BQ24074 linear power-path charger from USB only: 0.74 A charge (ISET 1.2 k), 1.5 A input limit (ILIM 1.1 k, VIN-DPM), TS 10 k, no safety timer, thermal throttling. Battery feeds the boost through D14; ~6-7 h runtime |
| Soft power | RECORD + encoder push held together enable the TPS61175 (Q3/Q4 P-MOSFETs in series from VBAT to BOOST_EN); firmware latches KEEP_ON (Teensy 24) after 2 s; USB (D16) or barrel (D17) force the boost on. Switch nets are isolated from the Teensy inputs by D18/D19 so an unpowered Teensy cannot hold the latch |
| Line-out mute | Omron G6K-2F-Y DPDT signal relay between the reconstruction filter and J4; de-energised = audio passes, energised = jack grounded. Firmware mutes only while a USB host is enumerated (ground-loop protection) and shows a warning with an override |
| USB data | J9 D+/D- wired (two short wires) to the Teensy 4.1 underside USB-Device pads via TP1/TP2; MTP exposes the SD card, Teensy Loader updates firmware |
| Enclosure | Hammond 1590XX (since Rev B); Rev C walls: rear = SD slot + 9 V barrel + USB-C, left = mic RJ45, right = phones, front = line out; lid = display, record button, gain encoder |
| PCB | 138.0 x 114.0 mm, matching the 1590XX's official max PCB envelope, 12 mm corner chamfers; two copper layers; 1.6 mm FR-4; 1 oz copper; 0.20 mm minimum track; 0.15 mm minimum clearance; 0.40 mm finished via drill |

## Signal convention

The channel names are treated as physical capsule identities, not Ambisonic
B-format channels:

- `FLU`: front-left-up
- `FRD`: front-right-down
- `BLD`: back-left-down
- `BRU`: back-right-up

The exact tetrahedral A-format-to-B-format matrix, microphone polarity, capsule
azimuth/elevation, equalization, and binaural HRTF set are firmware calibration
data. Rev A preserves channel identity and simultaneous sampling so those
coefficients can be corrected without changing the PCB.

## Prototype confirmations required

- Confirm the microphone really presents four independent two-wire electret
  capsules. A balanced capsule or shared-return microphone requires a different
  input and bias network.
- Confirm each capsule's permitted bias voltage/current and polarity before
  connecting the microphone.
- Confirm the purchased LCDWiki MSP3526 display's 14-pin order, header
  position, pin length and 92.0 x 49.5 mm mounting-hole pattern before
  drilling the enclosure and ordering standoffs.
- Verify the soft-power latch: with no external power the unit must stay
  off until both buttons are held, and the BQ24074 case temperature while
  charging in the closed box.
- Verify the relay K1 NC/NO sense at bring-up (line out must pass audio with
  the coil de-energised) and the TPS61175 compensation with a load step.
- Confirm the two USB D+/D- wires to the Teensy underside pads enumerate at
  480 Mbit/s (fall back to full-speed in firmware if not).
- Confirm the mating CAT6 cable/plug (shielded, 8P8C) against the RJHSE-5380 jack before ordering the board.
- Benchmark the selected microSD card at four simultaneous 192 kHz/24-bit
  streams before a long recording session.
- Validate the real microphone geometry and binaural decoder with acoustic
  measurements; no fixed generic HRTF can guarantee an individualized result.
