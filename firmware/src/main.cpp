// main.cpp — QuadPreRecorder application firmware
//
// Vendor: Illicit Apothecary
// Target: Teensy 4.1 on the QuadPreRecorder Rev A board
//
// Four-channel ambisonic electret recorder with a real-time binaural monitor.
//
// WHAT RUNS WHERE (this is the part that keeps the audio clean):
//
//   priority 96   SAI1 RX DMA interrupt, every 1.33 ms
//                   deinterleave 256 frames -> pack into the recorder rings
//                   -> copy to the DSP FIFO -> update the meters
//                 Nothing here allocates, blocks, or touches the SD card.
//
//   priority 112  SAI2 TX DMA interrupt, every 1.33 ms
//                   pull one rendered monitor block into the DAC buffer
//
//   priority 208  software interrupt: the monitor DSP
//                   decimate -> A-to-B -> 8 binaural FIRs -> limiter
//                 Preempted by both audio interrupts, so a slow DSP block can
//                 glitch the monitor but can never drop a recorded sample.
//
//   thread level  loop(): SD writes, controls, display, serial console
//
// FIRST TIME ON A NEW BOARD: flash the bringup/ tests first, in order. See
// docs/BRINGUP.md. This firmware assumes the hardware already works.

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>

#include "qpr_config.h"
#include "qpr_board.h"
#include "qpr_pcm1864.h"
#include "qpr_sai.h"
#include "qpr_recorder.h"
#include "qpr_dsp.h"
#include "qpr_controls.h"
#include "qpr_display.h"
#include "qpr_touch.h"

using namespace qpr;

// ---------------------------------------------------------------------------
// Subsystems
// ---------------------------------------------------------------------------
static Pcm1864       g_adc;
static SaiCapture    g_capture;
static SaiMonitorOut g_monitor_out;
static Recorder      g_recorder;
static MonitorDsp    g_dsp;
static Meters        g_meters;
static Controls      g_controls;
static Display       g_display;
static TouchFt6336   g_touch;

static char  g_status[48] = "";
static float g_gain_db = cfg::kPgaDefaultDb;
static bool  g_hp_enabled = false;
static bool  g_stream_ok = false;
static uint32_t g_boot_ms = 0;

static void setStatus(const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(g_status, sizeof(g_status), fmt, ap);
  va_end(ap);
  Serial.println(g_status);
}

// ---------------------------------------------------------------------------
// Capture interrupt. Order matters: the recorder first, because dropping a
// recorded sample is the only unrecoverable failure here.
// ---------------------------------------------------------------------------
static void onCaptureBlock(const Frame4* frames, uint32_t count) {
  g_recorder.pushFrames(frames, count);
  g_dsp.pushCaptureBlock(frames, count);
  g_meters.accumulate(frames, count);
}

static void onMonitorBlock(float* left, float* right, uint32_t count) {
  g_dsp.render(left, right, count);
}

// ---------------------------------------------------------------------------
// Gain
// ---------------------------------------------------------------------------
static void applyGain(float db) {
  if (db < cfg::kPgaMinDb) db = cfg::kPgaMinDb;
  if (db > cfg::kPgaMaxDb) db = cfg::kPgaMaxDb;
  g_gain_db = g_adc.setGainDb(db);
}

// Total gain from capsule to ADC full scale, for the serial console.
static float totalGainDb() {
  return board::FIXED_PREAMP_GAIN_DB + g_gain_db +
         (g_controls.padEngaged() ? board::PAD_ATTENUATION_DB : 0.0f);
}

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------
static void startRecording() {
  if (g_recorder.recording()) return;
  if (!g_recorder.cardMounted() && !g_recorder.begin()) {
    setStatus("no SD card");
    return;
  }
  if (!g_recorder.start()) {
    setStatus("start failed: %s", Recorder::errorName(g_recorder.lastError()));
    return;
  }
  board::setRecordLed(true);
  setStatus("recording take %03lu", (unsigned long)g_recorder.takeNumber());
}

static void stopRecording() {
  if (!g_recorder.recording()) return;
  const uint32_t take = g_recorder.takeNumber();
  const float secs = g_recorder.elapsedSeconds();
  const float peak = g_recorder.peakBufferUse();
  const uint32_t over = g_recorder.overrunCount();
  const uint64_t lost = g_recorder.framesDropped();
  g_recorder.stop();
  board::setRecordLed(false);
  if (over) {
    setStatus("take %03lu: %lu gaps, %.0f ms LOST", (unsigned long)take,
              (unsigned long)over,
              (double)(1000.0 * lost / cfg::kSampleRateHz));
  } else {
    setStatus("take %03lu: %.1f s, buffer peak %.0f%%", (unsigned long)take,
              (double)secs, (double)(peak * 100.0f));
  }
}

static void setHeadphones(bool on) {
  g_hp_enabled = on;
  board::setHeadphoneAmp(on);
}

// ---------------------------------------------------------------------------
// Line-level calibration tone.
//
// Both jacks carry the same signal, so this tone appears on the line output
// and the headphones together. Turn the headphone amplifier OFF, or the RV1
// knob down, before using it for any length of time.
// ---------------------------------------------------------------------------
static void toggleReferenceTone() {
  const bool on = !g_dsp.referenceToneActive();
  g_dsp.setReferenceTone(on);
  if (on) {
    const float dbfs = g_dsp.referenceToneDbfs();
    Serial.println();
    Serial.printf("REFERENCE TONE ON: %.0f Hz at %.0f dBFS\n",
                  (double)cfg::kRefToneHz, (double)dbfs);
    Serial.printf("  at the 1/4in line jack (J4): %.3f Vrms  =  %+.1f dBu\n",
                  (double)MonitorDsp::dbfsToLineVrms(dbfs),
                  (double)MonitorDsp::dbfsToLineDbu(dbfs));
    Serial.printf("  for reference, 0 dBFS would be %.2f Vrms = %+.1f dBu\n",
                  (double)MonitorDsp::dbfsToLineVrms(0.0f),
                  (double)MonitorDsp::dbfsToLineDbu(0.0f));
    Serial.printf("  (assumes a %.0f kohm line input; RV1 loads the node too)\n",
                  (double)(cfg::kLineAssumedExternalOhms / 1000.0f));
    Serial.printf("  into 600 ohms instead you would lose %.1f dB -- and so "
                  "would\n  the headphones, because the split is before RV1\n",
                  (double)(MonitorDsp::lineLoadLossDb(cfg::kLineAssumedExternalOhms) -
                           MonitorDsp::lineLoadLossDb(600.0f)));
    Serial.println(F("  Set the receiving device so this reads -20 dBFS on its"));
    Serial.println(F("  meters. The tone bypasses the trim and the limiter, so"));
    Serial.println(F("  the level is exact. Press 'o' again to stop."));
    Serial.println(F("  NOTE: this is also on the headphones. Turn RV1 down."));
    setStatus("REF TONE %.0f dBFS = %+.1f dBu", (double)dbfs,
              (double)MonitorDsp::dbfsToLineDbu(dbfs));
  } else {
    setStatus("reference tone off");
  }
}

// ---------------------------------------------------------------------------
// Serial console. Everything the front panel can do, plus the diagnostics
// that do not fit on a 2.8-inch screen.
// ---------------------------------------------------------------------------
static void printHelp() {
  Serial.println();
  Serial.println(F("QuadPreRecorder - Illicit Apothecary"));
  Serial.println(F("  r        start/stop recording"));
  Serial.println(F("  + / -    gain up / down 1 dB"));
  Serial.println(F("  [ / ]    output trim down / up 1 dB (BOTH jacks)"));
  Serial.println(F("  o        1 kHz reference tone for setting line level"));
  Serial.println(F("  h        toggle the headphone amplifier"));
  Serial.println(F("  m        toggle the DAC mute"));
  Serial.println(F("  s        status"));
  Serial.println(F("  c        ADC clock status"));
  Serial.println(F("  ?        this help"));
}

static void printStatus() {
  Meters::Reading mr;
  g_meters.read(&mr);

  Serial.println();
  Serial.printf("state        : %s\n",
                g_recorder.recording() ? "RECORDING" : "idle");
  Serial.printf("uptime       : %.1f s\n", (millis() - g_boot_ms) / 1000.0);
  Serial.printf("capture      : %lu Hz, %lu blocks, %lu overruns, ISR max %lu us\n",
                (unsigned long)cfg::kSampleRateHz,
                (unsigned long)g_capture.blocksCaptured(),
                (unsigned long)g_recorder.overrunCount(),
                (unsigned long)g_capture.maxIsrMicros());
  Serial.printf("clocks       : MCLK %lu Hz, BCLK %lu Hz, LRCLK %lu Hz\n",
                (unsigned long)SaiCapture::mclkHz(),
                (unsigned long)SaiCapture::bclkHz(),
                (unsigned long)SaiCapture::lrclkHz());
  Serial.printf("gain         : PGA %+.1f dB, pad %s, total %+.1f dB\n",
                (double)g_gain_db, g_controls.padEngaged() ? "IN" : "out",
                (double)totalGainDb());
  Serial.printf("output trim  : %+.1f dB, DSP %.1f%% CPU, %s HRTF, "
                "%lu dropped, %lu starved, %lu underruns\n",
                (double)g_dsp.outputTrimDb(), (double)g_dsp.cpuPercent(),
                g_dsp.usingMeasuredHrtf() ? "measured" : "modelled",
                (unsigned long)g_dsp.dropped(), (unsigned long)g_dsp.starved(),
                (unsigned long)g_monitor_out.underruns());
  if (g_monitor_out.dspOverBudget()) {
    Serial.printf("               ! DSP hit its CPU budget %lu times -- the "
                  "monitor is over-configured. Lower cfg::kHrtfTaps.\n",
                  (unsigned long)g_monitor_out.dspOverBudget());
  }
  Serial.printf("outputs      : one binaural render -> DAC -> splits after "
                "R62/R63\n");
  Serial.printf("               J4 line out (fixed) | RV1 knob -> TPA6132A2 "
                "-> J5 headphones\n");
  Serial.printf("               0 dBFS at J4 = %.2f Vrms = %+.1f dBu; limiter "
                "ceiling %.0f dBFS = %+.1f dBu\n",
                (double)MonitorDsp::dbfsToLineVrms(0.0f),
                (double)MonitorDsp::dbfsToLineDbu(0.0f),
                (double)cfg::kLimiterThresholdDbfs,
                (double)MonitorDsp::dbfsToLineDbu(cfg::kLimiterThresholdDbfs));
  Serial.printf("headphones   : amp %s, DAC %s%s\n",
                g_hp_enabled ? "ON" : "off",
                digitalReadFast(pins::DAC_MUTE) ? "unmuted" : "MUTED",
                g_dsp.referenceToneActive() ? ", REFERENCE TONE ON" : "");
  if (g_recorder.cardMounted()) {
    Serial.printf("card         : take %03lu next, %.1f GB free, %.0f min left\n",
                  (unsigned long)(g_recorder.lastTakeOnCard() + 1),
                  g_recorder.freeSpaceBytes() / 1e9,
                  (double)(g_recorder.remainingSeconds() / 60.0f));
    Serial.printf("buffers      : peak %.0f%%, longest write %lu us\n",
                  (double)(g_recorder.peakBufferUse() * 100.0f),
                  (unsigned long)g_recorder.maxWriteMicros());
    if (g_recorder.framesDropped()) {
      Serial.printf("               ! %.1f ms of audio lost to overruns -- "
                    "all four files share the same gaps\n",
                    (double)(1000.0 * g_recorder.framesDropped() /
                             cfg::kSampleRateHz));
    }
  } else {
    Serial.println(F("card         : not mounted"));
  }
  Serial.print(F("levels       :"));
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    Serial.printf("  %s %+6.1f/%+6.1f%s", cfg::kChannelNames[c],
                  (double)mr.peak_dbfs[c], (double)mr.rms_dbfs[c],
                  mr.clipped[c] ? " CLIP" : "");
  }
  Serial.println(F("   (peak/rms dBFS)"));
}

static void printClockStatus() {
  Pcm1864::ClockStatus cs{};
  if (g_adc.readClockStatus(&cs) != Pcm1864::Status::Ok) {
    Serial.println(F("PCM1864 did not answer on I2C"));
    return;
  }
  Serial.printf("PCM1864 state: %s\n", Pcm1864::stateName(cs.state));
  Serial.printf("  SCK ratio  : %s\n", Pcm1864::sckRatioName(cs.sck_ratio_code));
  Serial.printf("  BCK ratio  : %s\n", Pcm1864::bckRatioName(cs.bck_ratio_code));
  Serial.printf("  errors     : SCK %d BCK %d LRCK %d\n",
                cs.sck_error, cs.bck_error, cs.lrck_error);
  Serial.printf("  halts      : SCK %d BCK %d LRCK %d\n",
                cs.sck_halt, cs.bck_halt, cs.lrck_halt);
}

static void serviceSerial() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'r':
        g_recorder.recording() ? stopRecording() : startRecording();
        break;
      case '+': case '=':
        applyGain(g_gain_db + 1.0f);
        setStatus("gain %+.1f dB", (double)g_gain_db);
        break;
      case '-': case '_':
        applyGain(g_gain_db - 1.0f);
        setStatus("gain %+.1f dB", (double)g_gain_db);
        break;
      case ']':
        g_dsp.setOutputTrimDb(g_dsp.outputTrimDb() + 1.0f);
        setStatus("output %+.0f dB (line + HP)", (double)g_dsp.outputTrimDb());
        break;
      case '[':
        g_dsp.setOutputTrimDb(g_dsp.outputTrimDb() - 1.0f);
        setStatus("output %+.0f dB (line + HP)", (double)g_dsp.outputTrimDb());
        break;
      case 'o': toggleReferenceTone(); break;
      case 'h': setHeadphones(!g_hp_enabled); break;
      case 'm': board::setDacMuted(digitalReadFast(pins::DAC_MUTE) != 0); break;
      case 's': printStatus(); break;
      case 'c': printClockStatus(); break;
      case '?': printHelp(); break;
      default: break;
    }
  }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
void setup() {
  g_boot_ms = millis();
  ARM_DEMCR |= ARM_DEMCR_TRCENA;      // cycle counter, used for CPU timing
  ARM_DWT_CTRL |= ARM_DWT_CTRL_CYCCNTENA;

  board::configureControlPins();      // HP amp off, DAC muted, LED off
  Serial.begin(115200);

  Wire.begin();
  Wire.setClock(400000);

  g_display.begin();
  g_display.splash("booting", "");

  // --- ADC ----------------------------------------------------------------
  Pcm1864::Status st = g_adc.begin(
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
      Pcm1864::Format::DualI2S
#else
      Pcm1864::Format::Tdm4Ch
#endif
  );
  if (st != Pcm1864::Status::Ok) {
    char msg[180];
    snprintf(msg, sizeof(msg),
             "The PCM1864 ADC did not configure: %s. Run the t02_i2c bring-up "
             "test. Check the 3V3 rails, R44/R45 pull-ups, and that U7 pins 25 "
             "and 26 are grounded.", Pcm1864::statusName(st));
    Serial.println(msg);
    g_display.fatal("ADC NOT FOUND", msg);
    // Keep running: the console still works, and the display shows why.
  }

  // --- DSP and coefficient tables -----------------------------------------
  g_dsp.begin();
  g_meters.reset();
  g_controls.begin();

  // --- SD card -------------------------------------------------------------
  if (g_recorder.begin()) {
    char reason[80];
    g_dsp.loadHrtfFromSd(g_recorder.volume(), reason, sizeof(reason));
    Serial.println(reason);
  } else {
    Serial.println(F("no SD card: recording is unavailable, monitoring still works"));
  }

  // --- touch ---------------------------------------------------------------
  if (!g_touch.begin(cfg::kTftRotation)) {
    Serial.println(F("touch controller did not answer; front-panel controls "
                     "still work"));
  }

  // --- audio clocks --------------------------------------------------------
  // Start capture first so the ADC sees its clocks, then check that it locked
  // before allowing any sound out of the DAC.
  g_capture.begin(onCaptureBlock);
  delay(20);

  if (st == Pcm1864::Status::Ok) {
    st = g_adc.waitUntilRunning(300);
    if (st != Pcm1864::Status::Ok) {
      Pcm1864::ClockStatus cs{};
      g_adc.readClockStatus(&cs);
      char msg[200];
      snprintf(msg, sizeof(msg),
               "The ADC has clocks but will not run: %s. It reports state '%s', "
               "SCK %s, BCK %s. Check R46/R48/R47 and the SCKI trace.",
               Pcm1864::statusName(st), Pcm1864::stateName(cs.state),
               Pcm1864::sckRatioName(cs.sck_ratio_code),
               Pcm1864::bckRatioName(cs.bck_ratio_code));
      Serial.println(msg);
      g_display.fatal("ADC CLOCK ERROR", msg);
    } else {
      g_stream_ok = true;
    }
  }

  applyGain(cfg::kPgaDefaultDb);
  g_monitor_out.begin(onMonitorBlock);

  // Only now is it safe to let audio out. The PCM5102A powers up muted through
  // R60's pull-down; this is the first time anything raises DAC_MUTE.
  delay(50);
  if (g_stream_ok) {
    board::setDacMuted(false);
  } else {
    Serial.println(F("DAC left muted because the capture stream is not healthy"));
  }

  Serial.printf("\nQuadPreRecorder ready - Illicit Apothecary\n");
  Serial.printf("capture %lu Hz / 24-bit / 4 ch, monitor %lu Hz\n",
                (unsigned long)cfg::kSampleRateHz,
                (unsigned long)cfg::kMonitorRateHz);
  printHelp();

  g_display.forceRedraw();
  if (g_stream_ok) setStatus("ready");
}

// ---------------------------------------------------------------------------
// Main loop. The SD writer gets the most attention; everything else is rate
// limited so it cannot starve it.
// ---------------------------------------------------------------------------
void loop() {
  // 1. SD writing, as often as possible.
  g_recorder.service();

  const uint32_t now = millis();

  // 2. Controls.
  static uint32_t last_ctrl_ms = 0;
  if (now != last_ctrl_ms) {
    last_ctrl_ms = now;
    g_controls.poll();

    if (g_controls.takeRecordPress()) {
      g_recorder.recording() ? stopRecording() : startRecording();
    }
    if (g_controls.takeRecordLongPress() && !g_recorder.recording()) {
      g_meters.reset();
      setStatus("meters cleared");
    }
    const int32_t detents = g_controls.takeEncoderDelta();
    if (detents != 0) {
      applyGain(g_gain_db + detents * cfg::kGainDbPerDetent);
      setStatus("gain %+.1f dB (total %+.1f dB)",
                (double)g_gain_db, (double)totalGainDb());
    }
    if (g_controls.takeEncoderPress()) {
      setHeadphones(!g_hp_enabled);
      setStatus("headphones %s", g_hp_enabled ? "on" : "off");
    }
    if (g_controls.padChanged()) {
      setStatus("pad %s (total %+.1f dB)",
                g_controls.padEngaged() ? "IN" : "out", (double)totalGainDb());
    }
  }

  // 3. Touch, only when the controller says something is happening.
  static uint32_t last_touch_ms = 0;
  static bool touch_was_down = false;
  if (now - last_touch_ms >= 30) {
    last_touch_ms = now;
    if (g_touch.present() && g_touch.interruptAsserted()) {
      const TouchFt6336::Point p = g_touch.read();
      if (p.pressed && !touch_was_down) {
        touch_was_down = true;
        switch (g_display.hitTest(p.x, p.y)) {
          case UiHit::RecordStop:
            g_recorder.recording() ? stopRecording() : startRecording();
            break;
          case UiHit::HeadphoneToggle:
            setHeadphones(!g_hp_enabled);
            break;
          case UiHit::MonitorUp:
            g_dsp.setOutputTrimDb(g_dsp.outputTrimDb() + 1.0f);
            setStatus("output %+.0f dB (line + HP)",
                      (double)g_dsp.outputTrimDb());
            break;
          case UiHit::MonitorDown:
            g_dsp.setOutputTrimDb(g_dsp.outputTrimDb() - 1.0f);
            setStatus("output %+.0f dB (line + HP)",
                      (double)g_dsp.outputTrimDb());
            break;
          case UiHit::MeterReset:
            g_meters.reset();
            break;
          default: break;
        }
      }
    } else {
      touch_was_down = false;
    }
  }

  // 4. Display, at the configured rate.
  static uint32_t last_ui_ms = 0;
  if (now - last_ui_ms >= 1000 / cfg::kMeterUpdateHz) {
    last_ui_ms = now;
    UiState s;
    s.recording   = g_recorder.recording();
    s.card_ok     = g_recorder.cardMounted();
    s.take        = g_recorder.recording() ? g_recorder.takeNumber()
                                           : g_recorder.lastTakeOnCard();
    s.elapsed_s   = g_recorder.elapsedSeconds();
    s.remaining_s = g_recorder.remainingSeconds();
    s.buffer_use  = g_recorder.peakBufferUse();
    s.overruns    = g_recorder.overrunCount();
    s.lost_ms     = (uint32_t)(1000ull * g_recorder.framesDropped() /
                               cfg::kSampleRateHz);
    s.gain_db     = g_gain_db;
    s.pad_engaged = g_controls.padEngaged();
    s.hp_enabled  = g_hp_enabled;
    s.output_trim_db = g_dsp.outputTrimDb();
    s.ref_tone = g_dsp.referenceToneActive();
    s.dsp_cpu_pct = g_dsp.cpuPercent();
    s.measured_hrtf = g_dsp.usingMeasuredHrtf();
    s.status_line = g_status;
    g_meters.read(&s.meters);
    g_display.update(s);
  }

  // 5. Console.
  serviceSerial();

  // 6. Watch for the one failure that silently ruins a take.
  static uint32_t last_overrun_seen = 0;
  if (g_recorder.overrunCount() != last_overrun_seen) {
    last_overrun_seen = g_recorder.overrunCount();
    setStatus("BUFFER OVERRUN x%lu - card too slow",
              (unsigned long)last_overrun_seen);
  }
  if (last_overrun_seen && g_recorder.recording()) {
    board::setRecordLed((now / 100) & 1);   // fast blink = trouble
  }
}
