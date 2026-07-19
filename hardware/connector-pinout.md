# Connector pinout

## J2 — ambisonic microphone DE-9 socket

Viewed looking into the mating face of the board-mounted female connector:

| Pin | Net | Cable function |
|---:|---|---|
| 1 | FLU_RAW | Front-left-up capsule signal |
| 6 | GND | Front-left-up capsule return |
| 2 | FRD_RAW | Front-right-down capsule signal |
| 7 | GND | Front-right-down capsule return |
| 3 | BLD_RAW | Back-left-down capsule signal |
| 8 | GND | Back-left-down capsule return |
| 4 | BRU_RAW | Back-right-up capsule signal |
| 9 | GND | Back-right-up capsule return |
| 5 | CHASSIS | Overall cable jacket/shield; bond to metal connector shell at both ends |

Do not connect pin 5 to any capsule return inside the microphone cable. The PCB
couples CHASSIS to circuit ground through 1 MOhm and 1 nF; `R5` can provide a
direct 0 Ohm bond only if EMC testing calls for it.

## J3 — TFT/touch header

| Pin | Function | Pin | Function |
|---:|---|---:|---|
| 1 | +5 V module input | 8 | TFT backlight through 100 Ohm |
| 2 | GND | 9 | SPI MISO |
| 3 | TFT chip select | 10 | Touch SPI clock |
| 4 | TFT reset | 11 | Touch chip select |
| 5 | TFT data/command | 12 | Touch SPI MOSI |
| 6 | TFT SPI MOSI | 13 | Touch SPI MISO |
| 7 | TFT SPI clock | 14 | Touch interrupt |

The header matches a common 14-pin ILI9341/XPT2046 convention, not a formal
module standard. Verify every pin against the purchased display before fitting
it. Do not connect a 3.3 V-only module to pin 1 without adapting the supply.
