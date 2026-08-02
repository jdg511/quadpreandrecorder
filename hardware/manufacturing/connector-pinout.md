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

## J3 — LCDWiki MSP2834 TFT/capacitive-touch header

| Pin | Function | Pin | Function |
|---:|---|---:|---|
| 1 | +5 V module input | 8 | TFT backlight through 100 Ohm |
| 2 | GND | 9 | SPI MISO |
| 3 | TFT chip select | 10 | CTP/I2C clock |
| 4 | TFT reset | 11 | CTP reset |
| 5 | TFT data/command | 12 | CTP/I2C data |
| 6 | TFT SPI MOSI | 13 | CTP interrupt |
| 7 | TFT SPI clock | 14 | Display SD card CS, DNP/no-connect in Rev A |

The header targets the LCDWiki MSP2834 2.8-inch IPS SPI ILI9341 module with
FT6336G capacitive touch. Verify the purchased module revision before fitting
it. Do not connect a 3.3 V-only module to pin 1 without adapting the supply.

## J6 — analog debug DB-25 socket

This right-angle 25-pin D-sub socket is intended to protrude through the
enclosure wall for external breakout/probing during bring-up. Keep attached
leads short; these are high-impedance and audio-band nodes, not long cable
outputs.

| Pin | Net | Function |
|---:|---|---|
| 1 | GND | Circuit ground |
| 2 | CHASSIS | Shield/chassis node |
| 3 | +9V | Protected analog supply rail |
| 4 | VREF | 4.5 V audio reference |
| 5 | FLU_RAW | FLU input at DE-9 before RF resistor |
| 6 | FLU_AC | FLU AC-coupled/bias node |
| 7 | FLU_PAD | FLU selected pad/direct output |
| 8 | FLU_PRE | FLU OPA1654 preamp output |
| 9 | FLU_ADC | FLU ADC input node |
| 10 | FRD_RAW | FRD input at DE-9 before RF resistor |
| 11 | FRD_AC | FRD AC-coupled/bias node |
| 12 | FRD_PAD | FRD selected pad/direct output |
| 13 | FRD_PRE | FRD OPA1654 preamp output |
| 14 | FRD_ADC | FRD ADC input node |
| 15 | BLD_RAW | BLD input at DE-9 before RF resistor |
| 16 | BLD_AC | BLD AC-coupled/bias node |
| 17 | BLD_PAD | BLD selected pad/direct output |
| 18 | BLD_PRE | BLD OPA1654 preamp output |
| 19 | BLD_ADC | BLD ADC input node |
| 20 | BRU_RAW | BRU input at DE-9 before RF resistor |
| 21 | BRU_AC | BRU AC-coupled/bias node |
| 22 | BRU_PAD | BRU selected pad/direct output |
| 23 | BRU_PRE | BRU OPA1654 preamp output |
| 24 | BRU_ADC | BRU ADC input node |
| 25 | GND | Extra circuit ground/reference pin |

## J7 — digital/control debug DB-25 socket

This right-angle 25-pin D-sub socket exposes controller, display, ADC, DAC, and
control signals for firmware and board-level troubleshooting through the
enclosure wall.

| Pin | Net | Function |
|---:|---|---|
| 1 | GND | Circuit ground |
| 2 | +5V | 5 V rail |
| 3 | +3V3_D | Digital 3.3 V rail |
| 4 | ADC_MCLK | ADC master clock |
| 5 | ADC_BCLK | ADC bit clock |
| 6 | ADC_LRCLK | ADC word/select clock |
| 7 | ADC_TDM | ADC serial audio data |
| 8 | DAC_BCLK | DAC bit clock |
| 9 | DAC_LRCLK | DAC word/select clock |
| 10 | DAC_DIN | DAC serial audio data |
| 11 | DAC_MUTE | DAC mute control from Teensy |
| 12 | I2C_SDA | I2C data |
| 13 | I2C_SCL | I2C clock |
| 14 | SPI_SCK | TFT/touch SPI clock |
| 15 | SPI_MOSI | TFT/touch SPI MOSI |
| 16 | SPI_MISO | TFT/touch SPI MISO |
| 17 | TFT_CS | TFT chip select |
| 18 | TFT_DC | TFT data/command |
| 19 | TOUCH_RST | Touch controller reset (FT6336G is I2C; no chip select) |
| 20 | TOUCH_IRQ | Touch controller interrupt |
| 21 | PAD_DBG | Common -10 dB pad select level via 1 k series (0/9 V swing — NOT 3.3 V logic; do not drive) |
| 22 | REC_BUTTON | Record button input |
| 23 | HP_ENABLE | Headphone amplifier enable |
| 24 | REC_LED | Record LED drive |
| 25 | GND | Extra circuit ground/reference pin |
