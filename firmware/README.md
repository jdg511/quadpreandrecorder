# QuadPreRecorder firmware

**Illicit Apothecary** — firmware for the four-channel ambisonic electret
preamp and 192 kHz recorder.

Four electret capsules in a vertical tetrahedron → OPA1654 preamps → PCM1864
ADC → Teensy 4.1 → four mono 24-bit WAV files on microSD, plus a real-time
binaural monitor out of a PCM5102A.

---

## If you have never touched this before, read this bit

There are two things in this folder:

1. **The firmware** — C++ that runs on the Teensy 4.1 on your board.
2. **A simulator** — Python that runs on your computer and lets you *hear* the
   binaural monitor before the board exists.

You do not need to understand the C++ to use either one.

### Hearing the monitor today, with no hardware

```
cd sim
python3 simulate_binaural.py --scene orbit --out orbit.wav
```

Put on headphones and play `orbit.wav`. A click train circles your head twice.
That is the exact decode and HRTF maths the Teensy will run — same
coefficients, same sample rates. If you want to change how it sounds, change
it here first, where you get an answer in half a second instead of a reflash.

Other scenes: `--scene flyover`, `--scene corners`, `--scene static`.

### Running the firmware without a board

```
cd test/host
python3 run_tests.py
```

This compiles the **real firmware source** — the DSP and the recorder,
unmodified — for your computer and runs it. It checks that the monitor DSP
produces the same audio as the Python model (sample for sample), and that the
four-stream recorder survives a simulated microSD stall without losing
sample-alignment between the channels. See [test/README.md](test/README.md).

It cannot test anything electrical. That is what `bringup/` is for.

### Putting firmware on the board

Install [VS Code](https://code.visualstudio.com/) and the **PlatformIO IDE**
extension, then open this folder. The blue bar at the bottom has an
environment picker and an upload arrow. Pick an environment, press the arrow.

From a terminal instead:

```
pio run -e app -t upload      # the real firmware
pio device monitor            # watch what it says
```

**On a brand new board, do not flash `app` first.** Flash the bring-up tests
in order — `t01_power`, `t02_i2c`, `t03_controls`, `t04_sdbench`,
`t05_display`, `t06_audio` — and read [docs/BRINGUP.md](docs/BRINGUP.md).
Each test proves one subsystem and tells you, in plain language, which
component to look at when it fails. Debugging a bad solder joint through the
full firmware is miserable; debugging it through a fifty-line test is not.

---

## Environments

| Environment | What it is |
|---|---|
| `app` | The firmware. 192 kHz, four channels, dual-line I2S. |
| `app_96k_tdm` | Same firmware at 96 kHz over single-line TDM. Fallback if the 192 kHz path misbehaves on real silicon. |
| `t01_power` | Boots, blinks, checks every control pin's idle level. |
| `t02_i2c` | Scans I2C, configures the PCM1864, verifies registers. |
| `t03_controls` | Button, encoder direction and detents, pad switch. |
| `t04_sdbench` | **Run this before trusting any card.** Sustained four-stream write test with worst-case stall reporting. |
| `t05_display` | TFT colour/orientation, touch calibration targets. |
| `t06_audio` | Clocks, ADC lock, live four-channel levels, test tone, live monitor. |

## Layout

```
platformio.ini          build configuration, one environment per target
src/main.cpp            the application
bringup/                six standalone hardware tests
lib/qpr_board/          pin map (from the netlist) and build-time config
lib/qpr_pcm1864/        PCM1864 ADC driver
lib/qpr_sai/            SAI1 four-channel capture, SAI2 monitor output
lib/qpr_recorder/       four-stream WAV writer
lib/qpr_dsp/            decimator, ambisonic decode, binaural render, meters
lib/qpr_dsp/qpr_coeffs.h  GENERATED — do not edit, run sim/build_hrtf.py
lib/qpr_ui/             display, touch, front-panel controls
sim/                    the Python simulator and coefficient generator
test/host/              host test harness: runs the real firmware natively
docs/                   bring-up runbook, architecture, calibration
```

## Using it

**Front panel**

- **RECORD button** — short press starts/stops. Long press (when stopped)
  clears the meters.
- **Encoder** — turn for gain, 1 dB per detent, all four channels together.
  Press the shaft to toggle the headphone amplifier.
- **PAD switch** — mechanical, −9.7 dB ahead of the preamps. The firmware
  reads it and folds it into the displayed total gain.
- **Touchscreen** — RECORD/STOP, HP on/off, output trim ±. Tapping the meters
  clears the peak holds.
- **Volume knob (RV1)** — headphones only. The line output is unaffected by it.

**Both outputs are binaural.** There is one DSP chain and one DAC; the signal
splits in the analog domain after the reconstruction filter — one copy straight
to the 1/4 inch line jack, the other through the volume knob into the
TPA6132A2 and out the 1/8 inch jack. The `OUT` trim on screen is digital and
therefore moves both; the knob moves only the headphones. Press `o` on the
serial console for a 1 kHz reference tone at a known voltage to set line levels
by.

**Serial console** (115200 baud) has everything the panel does, plus `s` for
a full status dump and `c` for the ADC's own view of the clocks. Press `?`.

**Files** land on the card as `FLU001.WAV`, `FRD001.WAV`, `BLD001.WAV`,
`BRU001.WAV` — one take, four mono 24-bit files at the capture rate. The next
take number is one higher than the highest number found on *any* of the four
prefixes, so an interrupted set can never be overwritten.

## The numbers that matter

| | |
|---|---|
| Capture | 192 kHz, 24-bit, 4 simultaneous channels |
| File payload | 2.304 MB/s total (576 kB/s per channel) |
| SD buffer slack | 128 ms per channel (3 × 24 KiB rings) |
| Monitor | 48 kHz stereo, exactly capture ÷ 4, no resampling |
| Binaural | 8 FIRs × 128 taps, ~25% of one Cortex-M7 |
| Clock source | one 786.432 MHz audio PLL feeds both SAI blocks |
| Gain range | −2 dB to +52 dB total (pad in), +8 to +52 dB (pad out) |

The capture and monitor rates come from the same PLL with integer dividers, so
the monitor is exactly one quarter of the capture rate forever. There is no
asynchronous sample-rate conversion anywhere and nothing to drift.

## What has and has not been proven

**Verified here, by running the actual code:**

- Every environment compiles clean for Teensy 4.1 and fits in flash and RAM.
- The real `qpr_dsp.cpp` was run natively and produces the same audio as the
  Python model to 4.5e-07, correlation 1.000000000 — both linear and 12 dB
  into the limiter. So tuning on the desktop describes the box.
- The real `qpr_recorder.cpp` was run against injected microSD stalls. A
  100 ms stall is absorbed at 78% buffer; a 400 ms stall loses exactly 273 ms
  (400 − 128) and loses it **collectively**, leaving all four files the same
  length and sample-aligned end to end.
- Everything it wrote opens in ffprobe as `pcm_s24le, 192000 Hz, mono`.
- The ambisonic maths passes its own self-test suite. The simulator produces
  correct localisation cues — ILD +7.4 dB, ITD 354 µs for a hard-left source.
- Every PCM1864 register value was checked against the TI datasheet.

Those tests found three real bugs: stale take numbering after `stop()`, and
the limiter's release coefficient losing precision in float32. Both fixed.

**Not verified, because it needs the board:** everything electrical — SAI
registers, eDMA, clock generation, I2C to the ADC, the display, the analog
path. The SAI sequences follow PJRC's proven IMXRT paths but with the sample
rate, word width and DMA element size changed, and no oscilloscope has been
near them. The 96 kHz TDM fallback is the least-exercised path in the project;
its frame-sync polarity is a judgement call, flagged in the source.

Read [docs/BRINGUP.md](docs/BRINGUP.md) before you power the board.
