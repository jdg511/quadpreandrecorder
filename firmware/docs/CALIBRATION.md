# Calibration

**Illicit Apothecary — QuadPreRecorder Rev A**

Getting the recorder *correct* is bring-up. Getting it to *sound right* is
this. Everything here is a number you can change without touching the PCB,
because the recorded files are raw capsule signals and every decode decision
happens downstream.

Work in the simulator. It runs the identical maths in half a second instead of
a reflash.

---

## The one command

```
cd sim
python3 build_hrtf.py --taps 128 --radius 0.015
pio run -e app -t upload
```

`build_hrtf.py` writes `lib/qpr_dsp/qpr_coeffs.h` and `.cpp`. The firmware
compiles them in. It also runs the maths self-test first and refuses to
generate anything if that fails.

To hear a change before flashing it, pass the same options to the simulator:

```
python3 simulate_binaural.py --radius 0.021 --scene orbit --out test.wav
```

---

## 1. Capsule geometry — do this first

Everything else is fine tuning; this one is either right or the image is
wrong.

### Which capsule is which

Confirmed in bring-up step 6b: scratch each capsule and see which meter moves.
The firmware's fixed order is `FLU, FRD, BLD, BRU`, and that order is welded to
the PCM1864 input wiring. If your physical microphone does not match, **do not
rewire it** — change the direction vectors in `sim/qpr_ambisonics.py`:

```python
CAPSULE_DIRECTIONS = np.array([
    [+_S, +_S, +_S],  # FLU  front left  up
    [+_S, -_S, -_S],  # FRD  front right down
    [-_S, +_S, -_S],  # BLD  back  left  down
    [-_S, -_S, +_S],  # BRU  back  right up
])
```

Coordinates: **x forward, y left, z up**. Azimuth counter-clockwise from front,
so +90° is the listener's left.

The A-to-B matrix is *derived* from this array, not hard-coded, so changing it
propagates correctly. Rerun `python3 qpr_ambisonics.py` — the self-test
verifies the round trip.

### Capsule radius

```
--radius 0.015          # metres, default 15 mm
```

Measure from the array centre to a capsule diaphragm. This sets the transition
frequency of the A-format correction, `f_t = c / (2πr)` — about 3.6 kHz at
15 mm. Getting it wrong tilts the whole balance between the omni component and
the directional components, which sounds like the image being either
claustrophobically narrow (radius too small) or vague and boomy (too large).

It is the single number that most affects how the monitor sounds. Measure it
properly.

---

## 2. A-format correction

A tetrahedral array cannot resolve a pressure gradient at low frequency,
because the capsules are too close together relative to the wavelength. The
X/Y/Z components are therefore under-represented below `f_t`, and the textbook
correction is a +6 dB/octave boost — which, left unbounded, is +∞ at DC.

Two parameters bound it, in `a_format_correction()`:

```python
lf_shelf_hz  = 80.0     # below this the boost stops rising
max_boost_db = 18.0     # and it never exceeds this
```

Raise `lf_shelf_hz` if the monitor rumbles. Lower `max_boost_db` if wind or
handling noise dominates. To hear what the correction is doing at all, render
with and without:

```
python3 simulate_binaural.py --scene corners --out with.wav
python3 simulate_binaural.py --scene corners --no-correction --out without.wav
```

**This is a model, not a measurement.** Real capsules have their own response,
the enclosure diffracts, and no array is perfectly symmetric. If you can get
the microphone in front of a measurement rig, replace this function's output
with the measured correction and everything downstream follows.

---

## 3. Gain

The chain is: capsule → OPA1654 fixed +20.1 dB → optional −9.7 dB pad →
PCM1864 PGA, −12 dB to +32 dB in 0.5 dB steps.

| Pad | Total range |
|---|---|
| out | +8.1 dB to +52.1 dB |
| in | −1.6 dB to +42.4 dB |

All four PGAs are moved by a single register write using the PCM1864's `LINK`
bit, so the four channels change together on one internal ramp. Four separate
writes would start their ramps microseconds apart, and channel-to-channel gain
mismatch is exactly what destroys an ambisonic array.

Automatic clipping suppression (`AGC_EN`) is **off and must stay off** — it
would act per channel and break the matching.

Aim for peaks around −12 dBFS on the loudest capsule. 24 bits gives you room;
clipping gives you nothing back.

To go above +32 dB, raise `kPgaMaxDb` in `qpr_config.h`. The part goes to
+40 dB but makes up the last 8 dB digitally, which costs noise floor. It is
there if you need it.

---

## 4. The HRTF

### The built-in one

An analytic spherical-head model: Woodworth ITD, Brown & Duda head shadow, a
pinna reflection whose delay tracks elevation and frontness, a pinna
high-frequency shelf that dims sources from behind, and a torso reflection at
about 1 ms.

Measured behaviour of the default set, through the full chain:

| Source | ILD | ITD | 5–15 kHz level |
|---|---|---|---|
| front | 0.0 dB | 0 µs | reference |
| hard left | +7.4 dB | −354 µs | −0.7 dB |
| hard right | −7.4 dB | +354 µs | −0.7 dB |
| behind | 0.0 dB | 0 µs | −1.4 dB |
| above | 0.0 dB | 0 µs | −1.2 dB |

Left/right is strong and unambiguous. Front/back and up/down are weak — 1–1.4 dB
of high-frequency shading and nothing else. That is honest: first-order
ambisonics plus a generic head has very little to work with there, and front/back
confusion in FOA binaural is a real, well-known limitation rather than a bug.

The 354 µs ITD is smaller than a real hard-left ITD (~650 µs) because the
max-rE decoder deliberately trades localisation sharpness for image stability.
Pass `--basic` if you want the sharper, less stable version.

### Using a measured set

```
pip install sofar
python3 build_hrtf.py --sofa MIT_KEMAR.sofa --taps 128 --bin HRTF.BIN
```

Copy `HRTF.BIN` to the root of the microSD card. The firmware loads it at boot
and says so; the display footer shows `hrtf meas` instead of `hrtf model`.

The file is validated against the firmware's tap count and monitor rate and
rejected with an explanation rather than loaded blind. If it says the tap count
is wrong, regenerate with `--taps` matching `cfg::kHrtfTaps`.

An individually-measured set will beat any model. A generic measured set
(KEMAR and similar) beats the analytic model mostly in externalisation and
elevation.

### Filter length

`--taps 128` is the default and costs about 25% of one core. 256 taps sounds
better with measured data and roughly doubles that. Check the real figure on
hardware — press `s` on the serial console and read `DSP N% CPU` — before
raising it. If the firmware reports `DSP hit its CPU budget`, it is too high;
the DSP will yield and glitch the monitor rather than starve the SD writer.

To change it, regenerate the coefficients *and* update `cfg::kHrtfTaps`; a
static assert catches the mismatch at compile time.

---

## 5. Decoder

```
--basic         plain projection decoder
(default)       max-rE weighting, g1 = 0.775
```

max-rE trades a little localisation sharpness for a much more stable image,
which is the right default for headphone monitoring. Basic is sharper and
more fragile. Try both on `--scene orbit`.

---

## 6. Line output level

Both jacks carry the same binaural render — the signal splits after R62/R63,
one copy to the 1/4 inch jack and one through the RV1 knob into the headphone
amplifier. So setting the line level is about matching whatever you plug into,
not about choosing what the line output "is".

Press `o` on the serial console. You get 1 kHz at −20 dBFS, which bypasses the
output trim and the limiter so the level at the jack is exact:

```
REFERENCE TONE ON: 1000 Hz at -20 dBFS
  at the 1/4in line jack (J4): 0.192 Vrms  =  -12.1 dBu
  for reference, 0 dBFS would be 1.92 Vrms = +7.9 dBu
```

Set the receiving device so its meters read −20 dBFS on that tone. Then digital
full scale here lines up with digital full scale there, and the limiter ceiling
at −1 dBFS gives you a hard, known maximum.

**Turn RV1 down first.** The tone is on the headphones too.

If the receiving device's input is too hot even at the bottom of its range,
lower `kOutputTrimDb` in `qpr_config.h` (or press `[` a few times). That trim
is digital and upstream of the DAC, so it moves the headphones with it — which
is fine, you have a knob for those.

### If you are driving something low-impedance

The table in [ARCHITECTURE.md](ARCHITECTURE.md#levels) has the numbers. Short
version: a 10 kΩ or higher input costs you 0.8 dB, a 600 Ω input costs 5.3 dB,
and the 600 Ω case takes the headphones down with it because the split is
before the volume pot. If that matters for your use, the fix is a buffer on
the line output in Rev B, not firmware.

## 7. Monitor limiter

In `qpr_config.h`:

```cpp
kLimiterThresholdDbfs = -1.0f;
kLimiterAttackMs      =  1.0f;
kLimiterReleaseMs     = 120.0f;
```

One gain envelope is applied to both ears together, so limiting can never move
the stereo image sideways. This affects the monitor only — the recorded files
never see it.

---

## Checking your work

The maths self-test runs automatically inside `build_hrtf.py`, but you can run
it alone:

```
cd sim && python3 qpr_ambisonics.py
```

It verifies that the capsule directions are a valid tetrahedron, that the
A-to-B matrix recovers the correct SN3D encoding from every test direction,
that the virtual speaker layout is a spherical 2-design, that encode-then-
decode preserves both pressure and velocity, that the HRIR has the right ear
leading for a right-hand source, and that the decimator's stopband is deep
enough where aliasing would be audible.

For a visual check:

```
python3 simulate_binaural.py --report plots.png
```

(needs matplotlib) — impulse responses and magnitude curves for all eight
binaural filters and the decimator, with the fold-back frequency marked.
