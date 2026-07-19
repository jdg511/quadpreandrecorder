# Rev A schematic and PCB review

## Scope

Reviewed the DE-9 input and shield strategy, four electret bias/protection
paths, ganged pad, OPA1654 gain stages, PCM1864 ADC, Teensy interfaces, TFT
header, PCM5102A DAC, TPA6132A2 headphone path, controls, power tree, PCB
parity, and Hammond/TFT geometry.

## Automated results

| Check | Result |
|---|---|
| KiCad ERC | 0 errors, 0 warnings |
| KiCad PCB DRC | 0 violations |
| Unconnected PCB pads | 0 |
| Schematic/PCB parity | 0 issues |
| Copper layers | 2 |
| Board envelope | 110.0 x 84.5 mm |

Silkscreen overlap, edge-clipping, and solder-mask clipping checks are ignored
in the project because the compact board intentionally relies on fabrication
clipping and the separate assembly drawings. No copper, solder-mask bridge,
courtyard, hole, or connectivity error class is suppressed.

## Design checks

- Four channels are component-identical from capsule bias through ADC input.
- The pad ratio is 33/(68+33) = 0.3267, or -9.72 dB nominal. The analog mux
  chooses rather than shorts the direct and attenuated paths.
- OPA1654 non-inverting gain is 1 + 90.9/10 = 10.09, or 20.08 dB nominal.
- The PCM1864 common software PGA produces the requested one-control matched
  gain. The planned total range is about 8 to 52 dB before the pad.
- Four 100 Ohm/10 nF ADC input filters are identical and placed at U7.
- ADC and DAC serial nets have 33 Ohm source/endpoint damping.
- The headphone amp's internally generated HPVDD/HPVSS nodes are only
  bypassed, and its outputs are ground-centered for the TRS jack.
- DE-9 pin 5 is CHASSIS, not audio ground; four return pins independently reach
  PCB GND.

## Open prototype items

- Firmware, actual microphone bias requirements, display pin order, enclosure
  cutouts, acoustic A-to-B/binaural coefficients, SD sustained-write behavior,
  ADC clocking, analog noise, and thermal behavior are not proven by ERC/DRC.
- The two-layer routing is fully connected and rule-clean, but first-article
  measurements remain mandatory before a production quantity.

Disposition: release as Rev A prototype manufacturing data, not as a validated
production design.
