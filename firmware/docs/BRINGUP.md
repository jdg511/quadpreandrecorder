# Bring-up runbook

**Illicit Apothecary — QuadPreRecorder Rev A**

This is the order to do things in the first time you power a board. Each step
proves one thing. Do not skip ahead: the whole point is that when something is
wrong, you find out while only one subsystem is in play.

Budget an evening. Most of it is step 4 running unattended.

---

## Before power

Do these with a multimeter, board unpowered and unpopulated of the Teensy if
you can:

- [ ] Continuity from the barrel jack ring to GND, tip to F1.
- [ ] No short between +9V and GND, +5V and GND, +3V3_D and GND, +3V3_A and GND.
- [ ] The Teensy socket is not fitted backwards.
- [ ] **Cut the VIN–VUSB pad on the underside of the Teensy 4.1** if you will
      ever have the barrel jack and USB connected at the same time. D3 stops
      USB back-feeding the board, but it does not stop ~4.6 V from the board
      reaching the USB VBUS pin and thence your computer.

Then apply 9 V with **no Teensy fitted** and check the rails at the regulators:
+5 V from the TPS62160, +3V3_A from the TPS7A20. If either is wrong, stop here.

---

## Step 1 — `t01_power`

**Proves:** the Teensy boots, USB serial works, the record LED works, and every
control input idles where the schematic says it should.

```
pio run -e t01_power -t upload
pio device monitor
```

The red RECORD LED blinks once a second. Serial prints a report every two
seconds; every line should say `ok`.

Then press the record button and turn the encoder while watching. The report
should change.

**If nothing appears on serial at all**, the Teensy is not running. Work back:
9 V present → F1 → D1/D2 → TPS62160 +5 V → D3 → Teensy VIN.

**If a control input reads LOW when it should be HIGH**, that input is shorted
to ground or its 10 kΩ pull-up is missing (R50 record, R51/R52 encoder A/B,
R53 encoder push).

**If HP_ENABLE or DAC_MUTE report HIGH**, stop. Something is driving them and
the outputs are not silent at power-up. Do not put on headphones.

---

## Step 2 — `t02_i2c`

**Proves:** the I2C bus, and that the PCM1864 is alive and configurable —
including the one register write (`GPIO0_FUNC = DOUT2`) that the entire
192 kHz four-channel scheme depends on.

You should see `0x4A` (the ADC) and, if the display is plugged in, `0x38`
(touch). Then a list of register tests, all `ok`.

**The clock status at the end will report errors. That is correct.** Nothing
is generating audio clocks yet; the part sits in its clock-waiting state until
step 6.

**If nothing is found**, check R44/R45 (4.7 kΩ pull-ups to +3V3_D) and that
3.3 V is actually at U7 pins 13 and 14.

**If `0x4A` is missing but `0x38` is present**, the ADC has a power or solder
problem. Check AVDD (pin 8), DVDD (13), IOVDD (14), and that pins 25 (MS/AD)
and 26 (MD0) are both grounded — those two are what put the part in I2C mode
at address 0x4A.

**If readbacks mismatch**, the bus is marginal. Drop `Wire.setClock` to 100000
in the test and try again; if that fixes it, look at bus capacitance.

---

## Step 3 — `t03_controls`

**Proves:** the switches and the encoder, including direction.

Follow the prompts. The test prints PASS for each control once you have
exercised it enough.

**The one to watch:** turning the encoder *clockwise* must report `+1`. If it
reports `-1`, A and B are swapped — either swap the wires or swap `GAIN_A` and
`GAIN_B` in `lib/qpr_board/qpr_board.h`.

**One physical detent must produce exactly one count.** If you get four counts
per detent, the encoder is not a 4-edge-per-detent type; change the divisor in
`Controls::poll()`.

---

## Step 4 — `t04_sdbench`

**This is the most important test in the set. Do not shorten it.**

Everything else on this board either works or obviously does not. A marginal
microSD card fails silently, mid-take, months from now.

Put in the card you actually intend to record on. Flash. Let it run for
**longer than your longest intended recording**. Ten minutes tells you almost
nothing. An hour tells you something. If you plan to record onto a half-full
card, test on a half-full card — they get slower as they fill.

The test writes four files at exactly the rate the recorder does, and reports:

- **sustained MB/s** — must exceed 2.304 MB/s with margin. Necessary, not
  sufficient.
- **worst single write** — this is the number that matters. The firmware has
  128 ms of buffer per channel. A card that averages 20 MB/s but pauses for
  300 ms doing internal garbage collection will drop samples.

| Verdict | What to do |
|---|---|
| PASS | Good. Note the worst-case figure so you can spot it degrading later. |
| MARGINAL | It fits, but a long take is a gamble. Get a better card, or raise `kRingChunksPerChannel` in `qpr_config.h` and rebuild — RAM2 has about 145 KiB spare, enough for one more chunk per channel. |
| FAIL | Do not record on this card. |

Press `q` to stop; it deletes its temporary files.

Cards that generally do well at this: the "high endurance" and V30/A2 dashcam
and surveillance grades. Cards that generally do badly: anything bundled free
with something else, and anything whose sustained-write figure the maker does
not publish.

---

## Step 5 — `t05_display`

**Proves:** the ILI9341 panel, its orientation, and the FT6336G touch
controller.

Three stages: colour bars, five touch targets, then free-draw.

**A note on Teensy pin 5.** It is `TOUCH_RST`, not a chip select. Some older
notes in this project called it "TOUCH_CS", left over from an earlier resistive
XPT2046 design. The Rev A part is an FT6336G, which is I2C with reset and
interrupt lines and no chip select. Firmware that drives pin 5 as a chip select
holds the controller in reset and it never answers.

**If the backlight is on but the screen is black**, check J3 pins 3/5/6/7/9 and
the reset on Teensy pin 7.

**If the backlight is off entirely**, check R56 (100 Ω from +5V to J3 pin 8).
The backlight is hardwired on; there is no software dimming.

**If touch never answers**, confirm the module you bought actually has
capacitive touch. Some MSP2834 revisions ship with resistive XPT2046 touch,
which will never appear at I2C address 0x38. The recorder works fine without
it — the button and encoder do everything.

**If the touch axes are swapped or mirrored**, fix the rotation mapping in
`TouchFt6336::read()`.

---

## Step 6 — `t06_audio`

**Proves:** the whole audio chain.

Plug the microphone in. Leave the headphone volume pot down and headphones off
your ears to start — this test can make sound, but only when you ask it to.

### 6a. Does the ADC lock?

On boot the test starts the clocks and waits for the PCM1864 to reach its RUN
state. It should say `ADC is RUNNING`, and the clock report should read:

```
generated MCLK   24576000 Hz  (128 x fs)
generated BCLK   12288000 Hz  (64 x fs)
generated LRCLK    192000 Hz
ADC sees SCK     128 fs
ADC sees BCK     64 fs
ADC state        RUN
```

If the ADC does not reach RUN, the Teensy is generating clocks the ADC is not
receiving. Check R46 (MCLK), R48 (BCLK), R47 (LRCLK) — all 33 Ω — and the SCKI
trace to U7 pin 15. The "ADC sees" lines tell you which clock is missing.

### 6b. Which capsule is which?

This is the step people skip and regret.

Scratch each capsule in turn with a fingertip and watch which of the four
meters moves. Write it down. You are confirming that:

```
FLU  front-left-up      PCM1864 VINL1  ADC1 L  DOUT  left slot   Teensy pin 8
FRD  front-right-down   PCM1864 VINR1  ADC1 R  DOUT  right slot  Teensy pin 8
BLD  back-left-down     PCM1864 VINL2  ADC2 L  DOUT2 left slot   Teensy pin 6
BRU  back-right-up      PCM1864 VINR2  ADC2 R  DOUT2 right slot  Teensy pin 6
```

If BLD and BRU show nothing at all while FLU and FRD work, DOUT2 is not
arriving: check R69 (33 Ω) and the trace from U7 pin 22 to Teensy pin 6. That
is the single most likely failure on this board, because DOUT2 is the one
signal doing something unusual.

**If the mapping is wrong, do not fix it by rewiring the microphone.** Fix it
by reordering the capsule directions in `sim/qpr_ambisonics.py`
(`CAPSULE_DIRECTIONS`), regenerating the coefficients, and rebuilding. Then the
recorded files still carry honest capsule identities and the decode follows.

### 6c. Does anything come out?

Press `t` for a 440 Hz test tone. It goes to the line output immediately.
Then press `h` to enable the headphone amplifier and bring the volume pot up
slowly.

Press `l` for a live monitor — the raw omni sum of all four capsules straight
to the DAC, **no binaural processing**. This is a diagnostic, not what the
product does: the real firmware always sends the full binaural render. All you
are proving here is that the analogue → digital → analogue chain passes audio.

Both the line jack and the headphone jack should carry whatever you play. They
come from the same DAC and split after R62/R63, so if one works and the other
does not, the fault is in the branch, not in the firmware: check RV1, C57/C58
and the TPA6132A2 for a dead headphone side, or J4 and C67/C68 for a dead line
side.

---

## Step 7 — the real firmware

```
pio run -e app -t upload
```

Watch the boot output. It tells you what it found and what it could not.

First take: record thirty seconds of something with obvious direction — walk
around the microphone talking. Then check on a computer:

- Four files, `FLU001.WAV` through `BRU001.WAV`, all exactly the same length.
- All four open as 192 kHz, 24-bit, mono.
- The channel with the most energy changes as you walked around.

Then render them through the simulator and listen:

```
cd sim
python3 simulate_binaural.py --input FLU001.WAV FRD001.WAV BLD001.WAV BRU001.WAV --out take001.wav
```

If the binaural render puts you back in the room, the whole system works. If
the directions are rotated or mirrored, the capsule mapping from step 6b is
wrong — go fix `CAPSULE_DIRECTIONS`, not the microphone.

Then read [CALIBRATION.md](CALIBRATION.md) for how to make it sound right
rather than merely correct.

---

## When something goes wrong later

The firmware reports its own health. Press `s` on the serial console:

| Reading | Meaning |
|---|---|
| `buffers: peak N%` | How full the SD rings got. Under 50% is comfortable. Sustained above 80% means the card is marginal. |
| `longest write` | The worst SD stall this session. Compare against the 128 ms budget. |
| `overruns` non-zero | Samples were lost. **All four files share the same gaps** — the writer drops a block from all four channels or none, so the take stays sample-aligned. The status line reports how many milliseconds went missing. |
| `starved` climbing | The DSP is not being fed. Usually means the capture stream stopped. |
| `DSP hit its CPU budget` | The monitor is over-configured. Lower `cfg::kHrtfTaps` and regenerate coefficients. |
| `capture ISR max` | Should be well under the 1333 µs block period. |
| `outputs` | Reminds you which control moves what, and prints the real line-jack voltage for 0 dBFS. |

Press `o` for a 1 kHz reference tone at a known level, to set gain staging on
whatever the line output feeds. It is on the headphones too — turn RV1 down.

The record LED blinks fast during a take if an overrun has occurred.
