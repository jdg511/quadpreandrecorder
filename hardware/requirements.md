# Rev A requirements and assumptions

## Required behavior

- Capture four two-terminal electret capsules arranged as a vertical first-order
  ambisonic tetrahedron.
- Bring four signal/return pairs and one overall cable shield into one
  board-mounted 9-contact connector.
- Apply one mechanically controlled, matched -10 dB pad to all four channels.
- Provide matched low-noise JFET-input gain with a maximum total gain between
  40 dB and 60 dB. One knob changes all four channels together.
- Convert four channels simultaneously at 192 kHz and 24 bits or better.
- Record four mono WAV files to microSD. Recording set `n` is named
  `FLUn.wav`, `FRDn.wav`, `BLDn.wav`, and `BRUn.wav`.
- Display four input meters and recorder state on a small TFT touchscreen.
- Decode the four-channel vertical-tetrahedral signal to stereo binaural audio
  in real time.
- Provide a board-mounted 1/4-inch stereo line output and a board-mounted
  1/8-inch stereo headphone output with a dedicated stereo volume control.
- Fit a standard Hammond enclosure on a two-layer PCB with board-mounted user
  connectors and controls.

## Rev A decisions

| Item | Rev A implementation |
|---|---|
| Microphone connector | Female right-angle DE-9, four pairs plus shield |
| DE-9 pinout | 1 FLU signal, 6 FLU return, 2 FRD signal, 7 FRD return, 3 BLD signal, 8 BLD return, 4 BRU signal, 9 BRU return, 5 shield/chassis |
| Capsule bias | Individually filtered +9 V bias through 4.7 kOhm; returns join quiet analog ground at the input |
| Pad | Four matched 68 kOhm/33 kOhm dividers selected by two CD4053B triple SPDT analog muxes and one panel switch; 9.7 dB nominal |
| JFET stage | One OPA1654 quad FET-input op amp, 20 dB fixed analog gain |
| Gain control | PCM1864 four-channel PGA, programmed equally from one EC11 encoder; total range 8 dB to 52 dB including ADC PGA and fixed stage |
| ADC | PCM1864, four simultaneous channels, 192 kHz, 24-bit TDM output |
| Controller | Teensy 4.1 module, 600 MHz Cortex-M7, native 4-bit SDIO microSD, two I2S/TDM ports |
| DAC | PCM5102A stereo I2S DAC, operated at 48 kHz or higher |
| Headphones | TPA6132A2 DirectPath stereo amplifier after a dual 10 kOhm audio-taper volume pot |
| Display | 2.8-inch SPI ILI9341 plus XPT2046 resistive touch, 14-pin 2.54 mm header |
| Power | Regulated 9 VDC, center-positive barrel input; on-board 5 V buck and low-noise 3.3 V analog rail |
| Enclosure | Hammond 1590BB2, maximum PCB envelope 110.33 x 84.83 mm |
| PCB | 110.0 x 84.5 mm; two copper layers; 1.6 mm FR-4; 1 oz copper; 0.20 mm minimum track; 0.15 mm minimum clearance; 0.40 mm finished via drill |

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
- Confirm the purchased display's 14-pin order and mounting-hole pattern before
  drilling the enclosure. Low-cost ILI9341 modules are not mechanically
  standardized.
- Confirm the selected DE-9 cable-end gender before ordering the board.
- Benchmark the selected microSD card at four simultaneous 192 kHz/24-bit
  streams before a long recording session.
- Validate the real microphone geometry and binaural decoder with acoustic
  measurements; no fixed generic HRTF can guarantee an individualized result.
