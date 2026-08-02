# Datasheet summary and IC audit

This review records the constraints applied to Rev A. Cached source PDFs are
under `hardware/datasheets/`; the schematic `Datasheet` fields point to the
vendor documents.

| Ref | Device | Supply / key limits | Rev A application check |
|---|---|---|---|
| U1 | TPS62160DGKR | 3–17 V input, adjustable 0.9–6 V output, 1 A buck | 9 V input; 680 kOhm/130 kOhm feedback gives about 4.98 V; 2.2 uH and 44 uF output capacitance; EN tied high; PG pulled up |
| U2 | TPS7A2033PDBVR | 1.6–6 V input, 300 mA low-noise 3.3 V LDO | 5 V input; 1 uF input and 4.7 uF output; supplies the analog 3.3 V rail |
| U3 | TLE2426IDR | Precision rail splitter from a single supply | 9 V input; VREF is about 4.5 V; noise-reduction and 47 uF/100 nF output bypassing fitted |
| U4/U5 | CD4053BPWR | Triple SPDT analog mux; address levels referenced to VSS/VDD | 0/9 V panel select; VEE=VSS=GND; four sections choose direct or matched -9.7 dB paths; unused section pins are NC and inhibit is low |
| U6 | OPA1654AIPWR | Quad low-noise JFET-input audio op amp; 4.5–36 V supply | 9 V single supply around 4.5 V VREF; four identical non-inverting stages, 10 kOhm/90.9 kOhm, 20.1 dB nominal |
| U7 | PCM1864DBTR | Four-channel audio ADC; up to 192 kHz; software PGA and TDM | Four single-ended inputs; AVDD/DVDD/IOVDD 3.3 V; LDO, VREF, and MICBIAS bypassing follows data sheet; 33 Ohm clock/data damping at IC |
| U8 | PJRC Teensy 4.1 | 600 MHz Cortex-M7; native microSD over SDIO; 3.3 V logic | Bottom-mounted module; SAI/TDM for ADC and I2S for DAC; SPI display/touch; I2C ADC control; barrel-to-VIN isolation diode fitted |
| U9 | PCM5102APWR | 32-bit stereo DAC, up to 384 kHz, ground-centered DirectPath output | 3.3 V analog/digital rails; charge-pump/LDO capacitors fitted; 33 Ohm I2S damping; line output and volume pot fed directly |
| U10 | TPA6132A2RTER | 2.3–5.5 V DirectPath stereo headphone amp; selectable gain | VDD=5 V; G0 high/G1 low selects 0 dB; single-ended positive inputs grounded; HPVDD is only bypassed, never externally powered; EN pulled down |

## Pin-completeness notes

- Every supply and ground pin on U1–U10 is assigned in the exported netlist.
- PCM1864 unused GPIO, oscillator, mode, and extra differential input pins are
  explicit no-connects; MS/AD and MD0 are grounded for the selected controlled
  mode/address.
- PCM5102A format pins are strapped for I2S operation and mute is pulled to a
  defined state.
- TPA6132A2 thermal pad is grounded. G0/G1 are hard-strapped for 0 dB and EN has
  a 100 kOhm shutdown pull-down.
- Teensy accessible but unused GPIO pins are explicit no-connects in the custom
  symbol, avoiding accidental hidden-net assumptions.

## Review limitations

The structured schematic parser used during review can misidentify unitized
symbols and custom-module ground pins. Its findings were checked against the
raw KiCad schematic, the exported netlist, ERC, and PCB parity. Those KiCad
artifacts are authoritative.
