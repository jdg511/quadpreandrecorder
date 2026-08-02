# Host tests — running the firmware without the firmware

**Illicit Apothecary — QuadPreRecorder Rev A**

You asked whether the *firmware* could be simulated, not just the ambisonic
maths. Partly, yes — and the part that can be is the part where bugs hide.

```
cd test/host
python3 run_tests.py
```

One command, no `make` required — it finds your C++ compiler (g++, clang++ or
MSVC's `cl`), builds, and runs everything. Works on Windows, macOS and Linux.

That compiles the **real firmware source files** — `qpr_dsp.cpp`,
`qpr_recorder.cpp`, `qpr_coeffs.cpp`, unmodified — for your desktop, against a
small shim that stands in for the Arduino and SdFat headers. Then it runs
them and checks what they actually do.

Nothing in `shim/` reimplements firmware logic. If a test passes, it passed
against the same code the Teensy executes.

---

## What it proves

### 1. The monitor DSP is the same filter you tuned by ear

`compare_firmware_to_model.py` builds a three-second four-channel test signal,
quantises it to 24 bits exactly as the ADC would, and pushes it through both:

- `build/test_dsp`, which links the real `MonitorDsp`
- `sim/simulate_binaural.py`'s model

then compares them sample for sample. Two cases: linear, and driven 12 dB into
the limiter so its state machine gets exercised.

```
worst difference   4.502e-07
correlation (L)    1.000000000
PASS
```

This is the test that makes `sim/simulate_binaural.py` meaningful. Without it,
"the desktop simulator runs the same maths" is a claim. With it, it is a
measurement.

It has already earned its keep: it caught the limiter's release coefficient
losing precision. `1.0f - expf(-1/(0.12*48000))` cancels away most of its
significant digits in float32, putting the release time constant out by
1.6e-4. Now computed with `expm1f`, which is 10× more accurate. Inaudible at
120 ms — but the error grows with the release time, and there was no reason to
be wrong.

### 2. The recorder survives a microSD stall without silently ruining the take

`test_recorder.cpp` drives the real `Recorder` the way `main.cpp` does —
`pushFrames()` from the "capture interrupt", `service()` from the "main loop" —
with the capture side clocked by a **virtual clock**, not by loop iterations.
That distinction is the whole test: when a write blocks for 400 ms, the ADC
does not wait, and 300 blocks of audio become due the instant the write
returns.

Every sample carries its own frame number and channel tag, so a desynchronised
channel is proven, not guessed at.

| Case | Result |
|---|---|
| healthy card | 384000 frames in, 384000 out, buffer peak 33% |
| 100 ms stall | absorbed, buffer peak 78%, nothing lost |
| 400 ms stall | 52480 frames lost = 273 ms, which is exactly 400 − 128 |

The 400 ms case is the important one. It checks that the loss is
**collective**: all four files the same length, same gaps, sample-aligned end
to end. A per-channel drop would leave four individually-valid files that are
time-shifted against each other — which decodes to a smeared, rotated sound
field and is completely inaudible as a fault. That is the bug two independent
reviewers flagged, and this test is what keeps it fixed.

It also caught a second, smaller one: `lastTakeOnCard()` was stale after
`stop()`, so the display offered an already-used take number as "next".

### 3. The WAV files are real files

The suite runs `ffprobe` over everything the recorder wrote. All of it comes
back `pcm_s24le, 192000 Hz, mono`, with the overrun take correctly 1.727 s
instead of 2.000 s on all four channels.

---

## What it cannot prove

Everything electrical, which is most of the risk:

- SAI register configuration, MCLK/BCLK/LRCLK generation
- eDMA descriptors, the FIFO-combined two-data-line capture
- I2C to the PCM1864, and whether GPIO0 really becomes DOUT2
- Real interrupt preemption and real timing
- The display, the touch controller, the analog path

A cycle-accurate i.MX RT model would cover some of that and still tell you
nothing about a cold solder joint on R69. The bring-up tests in `bringup/` are
the answer to those, on the board. See [docs/BRINGUP.md](../docs/BRINGUP.md).

---

## Layout

```
test/host/
  run_tests.py                  build + run everything, one command
  shim/Arduino.h                virtual clock, memory attributes, Serial
  shim/SdFat.h, .cpp            stdio-backed SD with injectable write stalls
  test_dsp.cpp                  runs the real MonitorDsp on a raw file
  test_recorder.cpp             runs the real Recorder against stalls
  compare_firmware_to_model.py  firmware vs Python, sample for sample
```

Needs a C++ compiler and `python3` with `numpy`. `ffmpeg` is optional and only
used for the last check.

**Getting a compiler on Windows:** the simplest route is MSYS2 —
install it, then `pacman -S mingw-w64-x86_64-gcc`, and run `run_tests.py` from
the MinGW64 shell. Alternatively install "Build Tools for Visual Studio" and
run from a Developer Command Prompt; `run_tests.py` detects `cl` and uses it.

## Adding a case

The stall injector is the useful knob:

```cpp
hostsd::setWriteCost(300);              // a healthy card, microseconds
hostsd::injectStall(93, 400000);        // write #93 takes 400 ms
```

`checkTake()` already asserts alignment, accounting and equal length, so a new
scenario is usually three lines.
