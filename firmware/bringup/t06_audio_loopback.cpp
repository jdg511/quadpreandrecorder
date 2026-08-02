// t06_audio_loopback.cpp — bring-up test 6: the whole audio path
//
// Vendor: Illicit Apothecary
//
// WHAT IT PROVES
//   - The Teensy generates MCLK, BCLK and LRCLK at the right frequencies.
//   - The PCM1864 accepts them and reaches its RUN state.
//   - All four capsule channels arrive, in the right order, with sensible
//     levels and no channel stuck at zero or full scale.
//   - GPIO0 really is working as DOUT2, which is the one thing that makes
//     192 kHz four-channel possible on this board.
//   - The PCM5102A and the TPA6132A2 make sound.
//
// WHAT TO DO
//   Plug the microphone in. Open the serial monitor. You get a live
//   four-channel level display. Then:
//
//     1. Speak, or scratch each capsule in turn with a fingertip. Watch
//        which meter moves. Write down which physical capsule moves which
//        meter -- that is the ONLY way to confirm the FLU/FRD/BLD/BRU
//        mapping, and everything downstream depends on it being right.
//
//     2. Press 't' to send a test tone to the line and headphone outputs.
//        START WITH THE VOLUME POT DOWN AND HEADPHONES OFF YOUR EARS.
//        Press 'h' to enable the headphone amplifier, then bring the pot up.
//
//     3. Press 'l' for a live monitor: the raw W (omni) sum of all four
//        capsules straight to the DAC, no binaural processing. If you can
//        hear yourself, the whole analogue-to-digital-to-analogue chain works.
//
// KEYS
//   t  test tone on / off        l  live omni monitor on / off
//   h  headphone amplifier       m  DAC mute
//   +/- ADC gain                 c  clock status
//   z  zero / reset the meters
//
// SAFETY
//   The DAC starts muted and the headphone amplifier starts off, exactly as
//   the real firmware does. Nothing makes sound until you ask for it.

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "qpr_board.h"
#include "qpr_config.h"
#include "qpr_pcm1864.h"
#include "qpr_sai.h"

using namespace qpr;

static Pcm1864       adc;
static SaiCapture    capture;
static SaiMonitorOut monitor;

static volatile uint32_t peak[cfg::kChannels] = { 0, 0, 0, 0 };
static volatile uint64_t sumsq[cfg::kChannels] = { 0, 0, 0, 0 };
static volatile uint32_t nsamp = 0;
static volatile uint32_t blocks = 0;

// The most recent decimated omni sample, for the live-monitor mode.
static volatile float g_omni_ring[512];
static volatile uint32_t g_omni_w = 0;
static volatile uint32_t g_omni_r = 0;

static bool tone_on = false;
static bool live_on = false;
static bool hp_on = false;
static float gain_db = 0.0f;

static void onCapture(const Frame4* f, uint32_t n) {
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    uint32_t pk = peak[c];
    uint64_t ss = sumsq[c];
    for (uint32_t i = 0; i < n; i++) {
      const int32_t v = f[i].ch[c];
      const uint32_t a = (uint32_t)(v < 0 ? -v : v);
      if (a > pk) pk = a;
      ss += (uint64_t)((int64_t)v * (int64_t)v);
    }
    peak[c] = pk;
    sumsq[c] = ss;
  }
  nsamp += n;
  blocks++;

  // Crude 4:1 decimation by averaging, good enough to hear yourself.
  for (uint32_t i = 0; i + 4 <= n; i += 4) {
    float acc = 0.0f;
    for (uint32_t k = 0; k < 4; k++) {
      acc += (float)(f[i + k].ch[0] + f[i + k].ch[1] +
                     f[i + k].ch[2] + f[i + k].ch[3]);
    }
    const uint32_t w = g_omni_w;
    g_omni_ring[w] = acc * (1.0f / (16.0f * 8388608.0f));
    g_omni_w = (w + 1) & 511;
  }
}

static void onMonitor(float* l, float* r, uint32_t n) {
  static float phase = 0.0f;
  const float step = 2.0f * (float)M_PI * 440.0f / (float)cfg::kMonitorRateHz;
  for (uint32_t i = 0; i < n; i++) {
    float v = 0.0f;
    if (tone_on) {
      v += 0.2f * sinf(phase);
      phase += step;
      if (phase > 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
    }
    if (live_on) {
      const uint32_t r_i = g_omni_r;
      if (r_i != g_omni_w) {
        v += g_omni_ring[r_i] * 4.0f;
        g_omni_r = (r_i + 1) & 511;
      }
    }
    if (v >  0.95f) v =  0.95f;
    if (v < -0.95f) v = -0.95f;
    l[i] = v;
    r[i] = v;
  }
}

static void printMeters() {
  uint32_t pk[cfg::kChannels];
  uint64_t ss[cfg::kChannels];
  uint32_t n;
  __disable_irq();
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    pk[c] = peak[c]; peak[c] = 0;
    ss[c] = sumsq[c]; sumsq[c] = 0;
  }
  n = nsamp; nsamp = 0;
  __enable_irq();

  Serial.print(F("  "));
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    const float p = pk[c] / 8388608.0f;
    const float pdb = p > 1e-7f ? 20.0f * log10f(p) : -120.0f;
    const float rms = n ? sqrtf((float)((double)ss[c] / (double)n)) / 8388608.0f : 0.0f;
    const float rdb = rms > 1e-7f ? 20.0f * log10f(rms) : -120.0f;

    // A 20-character bar from -60 dBFS to 0 dBFS.
    char bar[21];
    int len = (int)((pdb + 60.0f) / 3.0f);
    if (len < 0) len = 0;
    if (len > 20) len = 20;
    for (int i = 0; i < 20; i++) bar[i] = i < len ? '#' : '.';
    bar[20] = 0;

    Serial.printf("%s [%s] %+6.1f/%+6.1f%s  ", cfg::kChannelNames[c], bar,
                  (double)pdb, (double)rdb, pk[c] >= 8388600 ? " CLIP" : "");
  }
  Serial.println();
}

static void printClocks() {
  Serial.println();
  Serial.printf("  generated MCLK  %9lu Hz  (%lu x fs)\n",
                (unsigned long)SaiCapture::mclkHz(),
                (unsigned long)(SaiCapture::mclkHz() / cfg::kSampleRateHz));
  Serial.printf("  generated BCLK  %9lu Hz  (%lu x fs)\n",
                (unsigned long)SaiCapture::bclkHz(),
                (unsigned long)(SaiCapture::bclkHz() / cfg::kSampleRateHz));
  Serial.printf("  generated LRCLK %9lu Hz\n",
                (unsigned long)SaiCapture::lrclkHz());

  Pcm1864::ClockStatus cs{};
  if (adc.readClockStatus(&cs) != Pcm1864::Status::Ok) {
    Serial.println(F("  the ADC stopped answering on I2C"));
    return;
  }
  Serial.printf("  ADC sees SCK    %s\n", Pcm1864::sckRatioName(cs.sck_ratio_code));
  Serial.printf("  ADC sees BCK    %s\n", Pcm1864::bckRatioName(cs.bck_ratio_code));
  Serial.printf("  ADC state       %s\n", Pcm1864::stateName(cs.state));
  Serial.printf("  errors  SCK %d  BCK %d  LRCK %d\n",
                cs.sck_error, cs.bck_error, cs.lrck_error);
  Serial.printf("  capture ISR max %lu us of a %lu us budget\n",
                (unsigned long)capture.maxIsrMicros(),
                (unsigned long)(1000000ull * cfg::kDmaFramesPerHalf /
                                cfg::kSampleRateHz));
  Serial.println();
}

void setup() {
  board::configureControlPins();
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  ARM_DEMCR |= ARM_DEMCR_TRCENA;
  ARM_DWT_CTRL |= ARM_DWT_CTRL_CYCCNTENA;

  Wire.begin();
  Wire.setClock(400000);

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 6 of 6: AUDIO PATH"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
  Serial.println(F("Mode: dual-line I2S, 192 kHz, four channels."));
  Serial.println(F("      DOUT  (Teensy pin 8) carries FLU and FRD"));
  Serial.println(F("      DOUT2 (Teensy pin 6, via PCM1864 GPIO0) carries BLD and BRU"));
#else
  Serial.println(F("Mode: single-line TDM, 96 kHz, four channels (fallback)."));
#endif
  Serial.println();

  Serial.print(F("Configuring the ADC... "));
  Pcm1864::Status st = adc.begin(
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
      Pcm1864::Format::DualI2S
#else
      Pcm1864::Format::Tdm4Ch
#endif
  );
  Serial.println(Pcm1864::statusName(st));
  if (st != Pcm1864::Status::Ok) {
    Serial.println(F("Go back and run t02_i2c first."));
    while (true) { board::setRecordLed((millis() / 150) & 1); }
  }

  Serial.println(F("Starting the audio clocks..."));
  capture.begin(onCapture);
  delay(50);

  st = adc.waitUntilRunning(500);
  if (st != Pcm1864::Status::Ok) {
    Serial.printf("THE ADC DID NOT REACH ITS RUN STATE: %s\n",
                  Pcm1864::statusName(st));
    printClocks();
    Serial.println(F("Likely causes, in order:"));
    Serial.println(F("  - a broken or bridged clock trace: R46 (MCLK),"));
    Serial.println(F("    R48 (BCLK) or R47 (LRCLK), all 33 ohm"));
    Serial.println(F("  - SCKI (U7 pin 15) not reaching the part"));
    Serial.println(F("  - the ADC's 3.3 V rails sagging"));
  } else {
    Serial.println(F("ADC is RUNNING."));
  }

  monitor.begin(onMonitor);
  adc.setGainDb(gain_db);
  printClocks();

  Serial.println(F("Live levels below. Scratch each capsule in turn and note"));
  Serial.println(F("which meter moves -- that confirms the channel mapping."));
  Serial.println(F("Keys: t tone   l live monitor   h headphone amp   m mute"));
  Serial.println(F("      +/- gain   c clocks   z zero meters"));
  Serial.println();
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last >= 250) {
    last = millis();
    printMeters();
  }

  while (Serial.available()) {
    switch (Serial.read()) {
      case 't':
        tone_on = !tone_on;
        Serial.printf("\n>> 440 Hz test tone %s\n", tone_on ? "ON" : "off");
        if (tone_on) board::setDacMuted(false);
        break;
      case 'l':
        live_on = !live_on;
        Serial.printf("\n>> live omni monitor %s\n", live_on ? "ON" : "off");
        if (live_on) board::setDacMuted(false);
        break;
      case 'h':
        hp_on = !hp_on;
        board::setHeadphoneAmp(hp_on);
        Serial.printf("\n>> headphone amplifier %s%s\n", hp_on ? "ON" : "off",
                      hp_on ? "  (bring the volume pot up slowly)" : "");
        break;
      case 'm': {
        const bool muted = digitalReadFast(pins::DAC_MUTE) == 0;
        board::setDacMuted(!muted);
        Serial.printf("\n>> DAC %s\n", muted ? "unmuted" : "MUTED");
        break;
      }
      case '+': case '=':
        gain_db = adc.setGainDb(gain_db + 3.0f);
        Serial.printf("\n>> ADC gain %+.1f dB\n", (double)gain_db);
        break;
      case '-': case '_':
        gain_db = adc.setGainDb(gain_db - 3.0f);
        Serial.printf("\n>> ADC gain %+.1f dB\n", (double)gain_db);
        break;
      case 'c': printClocks(); break;
      case 'z':
        __disable_irq();
        for (uint8_t c = 0; c < cfg::kChannels; c++) { peak[c] = 0; sumsq[c] = 0; }
        nsamp = 0;
        __enable_irq();
        Serial.println(F("\n>> meters zeroed"));
        break;
      default: break;
    }
  }

  board::setRecordLed(tone_on || live_on);
}
