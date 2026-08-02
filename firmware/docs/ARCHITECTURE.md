# Firmware architecture

**Illicit Apothecary — QuadPreRecorder Rev A**

---

## The problem this shape solves

Four channels at 192 kHz / 24-bit is 2.304 MB/s of file payload that must go to
a microSD card without a single sample being lost, while a second audio stream
runs out of a DAC and a touchscreen redraws itself, on one 600 MHz core.

microSD cards stall. Not often, and not for long, but a card that averages
20 MB/s will occasionally pause for 50–200 ms doing internal housekeeping, and
during that pause the ADC does not stop producing samples. Everything below is
arranged around absorbing those pauses.

---

## Execution levels

Priorities are ARM NVIC values: **lower number preempts higher**.

```
priority 96    SAI1 RX DMA interrupt                         every 1.333 ms
               deinterleave 256 frames from the DMA buffer
               -> pack 24-bit into four recorder rings
               -> copy the block into the DSP FIFO
               -> update peak/RMS meters
               ~25 us of a 1333 us period. No allocation, no file I/O,
               no blocking, no division.

priority 112   SAI2 TX DMA interrupt                         every 1.333 ms
               move one rendered stereo block into the DAC buffer,
               or silence if none is ready. Then pend the DSP.

priority 208   software interrupt: the monitor DSP
               decimate 4:1 -> A-format to B-format -> 8 binaural FIRs
               -> limiter. HARD CPU BUDGET of 50% of one block period.

thread level   loop()
               SD writes, controls, display, serial console
```

The ordering is the design. The capture interrupt outranks everything, so a
slow SD write or an expensive DSP block can never delay it. The DSP outranks
thread level so the monitor stays smooth while the card is being written — but
it carries a hard cycle budget, because priority 208 still preempts thread
mode, and a DSP that ran long without a budget would starve the SD writer and
destroy the take. An over-budget DSP yields, the monitor glitches, and the
recording is untouched. That trade is deliberate and it only goes one way.

---

## Data flow

```
        4 capsules
            |
      OPA1654 preamps, switched -10 dB pad
            |
        PCM1864 --- I2C 0x4A: clocks, gain, format
          |    \
       DOUT   DOUT2                (two data lines, 2 channels each)
          |      |
    Teensy pin 8  pin 6
          \      /
        SAI1 RX, 2 data lines, FIFO-combined
            |
      eDMA ping-pong, 2 x 256 frames x 4 words, in OCRAM
            |
   [capture ISR] deinterleave -> Frame4 { FLU, FRD, BLD, BRU }
       /         |            \
      /          |             \
 4 x 72 KiB   3-slot FIFO    peak/RMS
 packed-24    of Frame4      accumulators
 rings        blocks              |
    |            |                |
[loop()]     [DSP ISR]        [display]
 SdFat        decimate 4:1
 24 KiB       A -> B (4x4 matrix)
 chunks       8 FIRs x 128 taps
    |         limiter
    |            |
 4 mono      3-slot stereo ring
 WAV files       |
             [SAI2 TX ISR] -> eDMA -> PCM5102A -> line out / TPA6132A2
```

---

## Clocking

One audio PLL feeds both serial ports:

```
PLL4 = 24 MHz x 32.768 = 786.432 MHz          (DIV_SELECT 32, NUM 7680, DENOM 10000)

SAI1 root = PLL4 / (PRED 4 x PODF 8)  = 24.576 MHz = MCLK = 128 fs -> PCM1864 SCKI
  BCLK    = MCLK / 2                  = 12.288 MHz = 64 fs
  LRCLK   = BCLK / 64                 = 192.000 kHz

SAI2 root = PLL4 / (PRED 4 x PODF 16) = 12.288 MHz = 256 fs
  BCLK    = root / 4                  =  3.072 MHz = 64 fs
  LRCLK   = BCLK / 64                 =  48.000 kHz
```

Every division is exact. The monitor rate is therefore *exactly* the capture
rate divided by four, permanently. There is no asynchronous sample-rate
conversion in this design and nothing that can drift apart over a long take —
the decimator is a fixed 4:1 integer ratio and that is all it ever has to be.

The PCM1864's own clock-error detector accepts SCK/LRCK ratios of 128 or 256 at
192 kHz (TI SLAS831D Table 16), so 128 fs is legal; 128 fs was chosen over
256 fs because 24.576 MHz is a considerably friendlier signal to route on a
two-layer board than 49.152 MHz.

### Why two data lines instead of TDM

The obvious way to get four channels down one wire is TDM. The PCM1864 cannot
do it here: **its TDM frame is fixed at 256 BCK**, so four channels at 192 kHz
would need a 49.152 MHz bit clock, and the part's own I/O tops out around
25 MHz for TDM.

So the ADC runs in ordinary I2S with two channels per data line, and its GPIO0
pin is retasked as a second data output (`GPIO0_FUNC = 101`, register 0x10).
Each line carries 12.288 MHz. The Teensy's SAI1 receives both into
FIFO-combined RX data lines 0 and 1, and one eDMA channel reads them
alternately using an 8-byte circular source window.

Single-line 4-channel TDM remains available as a 96 kHz fallback
(`pio run -e app_96k_tdm`). It has never been run against real silicon.

---

## Channel identity

Fixed by the PCB and not negotiable in firmware:

| Capsule | PCM1864 input | ADC pair | Data line | Teensy pin |
|---|---|---|---|---|
| FLU front-left-up | VINL1 (pin 3) | ADC1 L | DOUT | 8 |
| FRD front-right-down | VINR1 (pin 4) | ADC1 R | DOUT | 8 |
| BLD back-left-down | VINL2 (pin 1) | ADC2 L | DOUT2 | 6 |
| BRU back-right-up | VINR2 (pin 2) | ADC2 R | DOUT2 | 6 |

The DMA writes each frame as four words in the order
`[DOUT.L, DOUT2.L, DOUT.R, DOUT2.R]` — that is, `FLU, BLD, FRD, BRU` — because
the source address alternates between the two data registers. The capture ISR
reorders them into `Frame4` in FLU/FRD/BLD/BRU order once, and everything
downstream sees the sensible order.

**No A-to-B-format matrix is ever applied to the recorded files.** They are raw
capsule signals. The decode is monitor-only, so every calibration decision —
capsule geometry, the correction filters, the HRTF — stays correctable after
the fact.

---

## The recorder

Four independent lock-free single-producer/single-consumer rings, 72 KiB each
(3 × 24 KiB write chunks), holding packed 24-bit little-endian bytes. 72 KiB at
576 kB/s is **128 ms** of slack per channel.

24576 bytes is the chunk size because it is simultaneously a multiple of 512
(the SD block size) and of 3 (a packed 24-bit sample). Get either wrong and
every write straddles a block boundary.

`service()` always drains the fullest channel first, so one lagging file cannot
push another into overrun.

**Overruns are collective.** If any one ring cannot accept the incoming block,
the block is dropped from all four. This matters more than it looks: the four
rings do not drain evenly, so a per-channel drop would let one file keep a
block the others lost, permanently time-shifting it by 1.33 ms. Four files that
are each individually fine but mutually misaligned decode to a smeared,
rotated sound field — a failure that is both catastrophic and invisible. A gap
in all four is far better, and the firmware reports exactly how many
milliseconds went missing.

### File format

One mono 24-bit WAV per capsule. Audio data always begins at byte 512:

```
  0   'RIFF' <size> 'WAVE'                 12
 12   'JUNK' 28   <reserved for ds64>      36
 48   'fmt ' 16   <PCM, mono, 24-bit>      24
 72   'JUNK' 424  <padding>               432
504   'data' <size>                          8
512   audio
```

The padding is not decoration. It makes every subsequent write land on an SD
block boundary. The `JUNK` chunk at offset 12 is exactly the size of an RF64
`ds64` chunk, so when a file passes 4 GiB the final header is rewritten in
place as RF64 with no data movement.

Files are preallocated (one hour by default) so the FAT stays out of the write
path, and truncated to their real length on stop. The in-progress header is
refreshed every 5 seconds, so a file orphaned by a power cut is still playable
up to the last refresh.

Take numbering scans *all four* prefixes and takes the highest number seen plus
one — an interrupted set where `FLU007` exists but `BRU007` does not can
therefore never be overwritten.

---

## The monitor DSP

```
4 ch @ 192 kHz int24
   |  192-tap anti-alias FIR, decimate 4:1
   |  (linear phase, so the symmetric taps are folded: 96 multiplies per output)
4 ch @ 48 kHz float                       A-format
   |  4x4 matrix
W, X, Y, Z @ 48 kHz                       B-format, SN3D, order W X Y Z
   |  8 FIRs of 128 taps
L, R @ 48 kHz
   |  peak limiter, one gain applied to both ears
PCM5102A
```

The eight binaural filters are pre-baked. Each one is the sum, over eight
virtual loudspeakers on the vertices of a cube, of that speaker's ambisonic
decode gain times its HRIR — plus the A-format correction folded in. So the
cost is eight convolutions regardless of how many virtual speakers went into
the design, and the MCU never computes an HRTF.

**All of these coefficients come from `sim/build_hrtf.py`.** The firmware
contains no DSP design code at all, which is what makes the desktop simulator
meaningful: `sim/simulate_binaural.py` runs the identical numbers. If you tune
it on your laptop and it sounds right, it will sound the same on the box.

The anti-alias filter targets attenuation above 28 kHz rather than at 24 kHz,
because decimating 192 → 48 folds 24 + f down to 24 − f. Content at 24 kHz
folds to itself and nobody can hear it; content at 44 kHz folds to 4 kHz and
everybody can. Measured stopband from 28 kHz up: −90 dB.

A measured HRTF set can replace the built-in analytic one at boot by putting
`HRTF.BIN` on the card (generate it with `build_hrtf.py --sofa ... --bin`).
It is validated against the firmware's tap count and rate and rejected with an
explanation rather than loaded blind.

---

## Outputs — one binaural render, split in the analog domain

There is exactly **one** DSP chain, **one** DAC, and **one** binaural signal.
It carries the full decode: capsules → decimate → B-format → 8 binaural FIRs →
limiter. Both jacks get that same signal. Nothing is monitored in mono, and
nothing bypasses the binaural render.

The split is analog and happens after the reconstruction filter, traced from
the routed netlist:

```
PCM5102A OUTL (U9.6) ──R62 470R──┬── LINE_L ──┬── J4 tip     1/4" LINE OUT
                                 │            │              (fixed level)
                            C67 2.2nF         │
                              to GND          └── RV1 pin 1   top of the
                                                   │          10k audio-taper
                                              RV1 pin 2       volume pot
                                                   │  (wiper)
                                              C57 680nF
                                                   │
                                              TPA6132A2 INL- (U10.1)
                                                   │
                                              OUTL (U10.16) ──R65 10R──
                                                   J5 tip  1/8" HEADPHONES
```

Right channel is identical through R63 / C68 / RV1 pins 4-5 / C58 / U10.4 /
U10.5 / R66.

This is exactly the arrangement you would design on purpose: the expensive
part (the binaural render) happens once, upstream of the split, and the two
outputs differ only in what happens to them afterwards.

### What controls what

| Control | Line out (J4) | Headphones (J5) |
|---|---|---|
| RV1 knob | no effect | yes — this is the headphone volume |
| Output trim (`[` `]`, touch ± ) | yes | yes |
| HP enable (encoder press, `h`, touch HP) | no effect | mutes/unmutes the amp |
| DAC mute (`m`) | yes | yes |

The digital trim is upstream of the DAC, so it necessarily moves both. That is
a hardware fact, not a firmware choice — there is one converter. The UI calls
it **OUT**, not "monitor", for exactly this reason.

RV1 is wired as a plain divider with its top at `LINE_L` and its bottom at
ground, so it presents a constant 10 kΩ across the line node regardless of
knob position. Turning the headphones up and down moves the line output by
roughly a quarter of a dB, from the wiper loading alone.

### Levels

PCM5102A full scale is **2.1 Vrms**, ground-centred, with no DC blocking
capacitors (the DirectPath charge pump makes the output bipolar around ground).
R62/R63 and the loading then apply:

| External load on J4 | Loss | 0 dBFS | −1 dBFS (limiter ceiling) | −20 dBFS tone |
|---|---|---|---|---|
| nothing plugged in | −0.40 dB | 2.01 Vrms, +8.3 dBu | 1.79 V, +7.3 dBu | 0.201 V, −11.7 dBu |
| 10 kΩ line input | −0.78 dB | 1.92 Vrms, +7.9 dBu | 1.71 V, +6.9 dBu | 0.192 V, −12.1 dBu |
| 600 Ω input | −5.25 dB | 1.15 Vrms, +3.4 dBu | 1.02 V, +2.4 dBu | 0.115 V, −16.6 dBu |

**A 600 Ω line input costs about 4.5 dB on the headphones too**, because the
split is upstream of the volume pot. If you have to drive a low-impedance
input, expect to make it up on the knob.

Digital full scale lands near +8 dBu, so this is a prosumer-level output: hot
for a −10 dBV consumer input, a little shy of a +4 dBu pro input's nominal.
Press `o` on the serial console for a 1 kHz reference tone at a known level to
set the receiving device by; it bypasses the trim and the limiter, so the
number is exact.

---

## Meters

Peak and RMS are accumulated in the **capture** interrupt at the full 192 kHz
rate, not from the decimated monitor stream. Ultrasonic content can overload
the ADC while being completely invisible below 24 kHz; a meter that only sees
the monitor path would show you a clean signal on a clipped recording.

Peak hold decays linearly at 20 dB/s. Clip indication holds for 2 seconds.

---

## Testing

`test/host/` compiles the real `qpr_dsp.cpp` and `qpr_recorder.cpp` natively
and runs them: DSP output compared against the Python model sample for sample,
and the recorder driven against injected SD write stalls with a virtual clock,
so a stalled write really does back up the ring the way it would on hardware.
`python3 run_tests.py` in that directory. See [../test/README.md](../test/README.md).

The limiter is written as `env += a * (peak - env)` with `a` from `expm1f`
rather than `1.0f - expf(x)`. The latter cancels away most of its significant
digits in float32 for a long time constant — at a 120 ms release it put the
coefficient out by 1.6e-4 relative. The equivalence test is what surfaced it.

## Things deliberately not done

- **No CMSIS-DSP.** `arm_fir_f32` links fine on this platform, but its
  coefficient ordering (time-reversed or not) is documented inconsistently
  across versions, and getting it backwards would produce filters that are
  wrong in a way that still sounds like audio. The hand-written FIR is
  perhaps 30% slower and unambiguous.
- **No frequency-domain convolution.** Overlap-save would cut the binaural
  cost by roughly 10×, and is the right answer if you ever want 512-tap
  individualised HRTFs. It is more code with more ways to be subtly wrong, and
  128 taps direct already fits.
- **No Teensy Audio Library.** It is fixed at 44.1 kHz, 128-sample blocks of
  int16. Its IMXRT SAI and DMA sequences were used as the reference for this
  code; the library itself is not linked.
- **No PSRAM.** The Teensy 4.1 PSRAM pads may or may not be populated. All
  buffers fit in the 512 KiB of OCRAM with about 145 KiB spare.
