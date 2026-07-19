# Firmware contract

The PCB is designed for a custom Teensy 4.1 firmware target. Firmware is not a
stock Teensy Audio Library sketch: four-channel 192 kHz capture requires custom
SAI/TDM DMA and native SDIO buffering.

## Required pipeline

1. Configure PCM1864 over I2C for four single-ended inputs, slave clocks,
   192 kHz, 24-bit samples in four 32-bit TDM slots, and identical PGA values.
2. Receive blocks using DMA into ping-pong buffers. Never perform file I/O in
   the audio interrupt.
3. Deinterleave into four preallocated RF64/WAV-compatible mono streams named
   `FLUn.wav`, `FRDn.wav`, `BLDn.wav`, and `BRUn.wav`. Scan all four prefixes at
   boot and choose one plus the highest numeric suffix seen on any matching
   file, so a partial/corrupt prior set can never be overwritten.
4. Write through SdFat/native SDIO using large aligned buffers and periodic
   header updates. On stop, flush all streams and patch RIFF/data sizes.
5. Derive peak/RMS meters from the same sample blocks and update the TFT at a
   much lower priority/rate than DMA and SD writes.
6. Convert the calibrated tetrahedral A-format signals to B-format, decimate
   from 192 kHz to 48 kHz, convolve with left/right HRTFs, limit, and transmit
   stereo I2S to PCM5102A.
7. Hold `DAC_MUTE` and `HP_ENABLE` inactive until the DAC stream is stable.

## Channel identity

TDM slots and files must stay ordered `FLU`, `FRD`, `BLD`, `BRU`. Do not apply
an A-format-to-B-format matrix to the recorded files; decoding is monitor-only
so the raw recordings remain correctable.

## Hardware pin assignment

| Teensy pin | Function |
|---:|---|
| 2 | DAC data |
| 3 | DAC LRCLK |
| 4 | DAC BCLK |
| 5 | Touch CS |
| 6 | TFT reset |
| 8 | ADC TDM data |
| 9 | TFT D/C |
| 10 | TFT CS |
| 11/12/13 | SPI MOSI/MISO/SCK |
| 18/19 | I2C SDA/SCL |
| 20/21/23 | ADC LRCLK/BCLK/MCLK |
| 22 | Touch IRQ |
| 28 | Record button |
| 29/30/31 | Gain encoder A/B/push |
| 32 | Pad sense |
| 33 | Headphone enable |
| 34 | DAC mute |
| 35 | Record LED |

## Non-negotiable validation

Sustained writing must be tested with the exact microSD card for longer than the
longest intended session. Four packed 24-bit streams require 2.304 MB/s of file
payload; 32-bit DMA words move 3.072 MB/s internally. A fast average card can
still have long erase/program pauses, so preallocation and measured worst-case
latency matter more than its printed speed class.
