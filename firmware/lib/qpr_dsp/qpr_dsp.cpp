// qpr_dsp.cpp — monitor path implementation
// Vendor: Illicit Apothecary

#include "qpr_dsp.h"
#include "qpr_coeffs.h"
#include <SdFat.h>
#include <math.h>
#include <string.h>

namespace qpr {
namespace {

constexpr uint32_t kNIn   = cfg::kDmaFramesPerHalf;         // 256 @ 192 kHz
constexpr uint32_t kNOut  = cfg::kMonitorBlockSamples;      // 64  @ 48 kHz
constexpr uint32_t kM     = cfg::kDecimationFactor;         // 4
constexpr uint32_t kDecTaps  = coeffs::kDecimatorTaps;
constexpr uint32_t kHrtfTaps = coeffs::kHrtfTaps;

static_assert(kHrtfTaps == cfg::kHrtfTaps,
              "qpr_coeffs.h was generated for a different tap count than "
              "qpr_config.h expects -- rerun sim/build_hrtf.py --taps N");
static_assert(coeffs::kMonitorRateHz == cfg::kMonitorRateHz,
              "coefficient table monitor rate does not match qpr_config.h");

// Pick the anti-alias filter designed for THIS capture rate. Using the 192 kHz
// table on a 96 kHz stream would put the cutoff at 10 kHz and let everything
// between 28 and 48 kHz fold straight into the audible band.
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
constexpr const float* kDecimFir = coeffs::kDecimatorFir4;
static_assert(cfg::kDecimationFactor == 4, "192 kHz mode must decimate by 4");
#else
constexpr const float* kDecimFir = coeffs::kDecimatorFir2;
static_assert(cfg::kDecimationFactor == 2, "96 kHz mode must decimate by 2");
#endif
static_assert(kNIn % kM == 0, "capture block must divide by the decimation factor");
static_assert(kDecTaps % 2 == 0, "symmetric folding assumes an even tap count");

// --- capture block FIFO between the audio ISR and the DSP ISR ---------------
constexpr uint32_t kFifoSlots = 3;
DMAMEM Frame4 g_fifo[kFifoSlots][kNIn];
volatile uint32_t g_fifo_w = 0, g_fifo_r = 0;
volatile bool g_fifo_full[kFifoSlots] = { false, false, false };

// --- filter state ----------------------------------------------------------
// Decimator history: (taps - 1) carried samples plus one block of new ones.
DMAMEM float g_dec_hist[cfg::kChannels][kDecTaps - 1 + kNIn];
// B-format history for the binaural stage.
DMAMEM float g_bin_hist[4][kHrtfTaps - 1 + kNOut];
// Working buffers.
DMAMEM float g_a_format[cfg::kChannels][kNOut];
DMAMEM float g_b_format[4][kNOut];
// Live copy of the binaural filters, so an SD-loaded set can replace them.
DMAMEM float g_binaural[4][2][kHrtfTaps];

inline float clampf(float v, float lo, float hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

// Direct-form FIR, 4-way unrolled. Written out rather than calling CMSIS-DSP
// so the coefficient ordering is unambiguous: coef[0] multiplies the newest
// sample, which is the ordinary convolution y[n] = sum h[k] x[n-k].
inline float firDot(const float* __restrict newest_backwards,
                    const float* __restrict coef, uint32_t taps) {
  float a0 = 0.0f, a1 = 0.0f, a2 = 0.0f, a3 = 0.0f;
  uint32_t k = 0;
  for (; k + 4 <= taps; k += 4) {
    a0 += newest_backwards[-(int32_t)(k + 0)] * coef[k + 0];
    a1 += newest_backwards[-(int32_t)(k + 1)] * coef[k + 1];
    a2 += newest_backwards[-(int32_t)(k + 2)] * coef[k + 2];
    a3 += newest_backwards[-(int32_t)(k + 3)] * coef[k + 3];
  }
  for (; k < taps; k++) a0 += newest_backwards[-(int32_t)k] * coef[k];
  return (a0 + a1) + (a2 + a3);
}

}  // namespace

// ===========================================================================
// MonitorDsp
// ===========================================================================
void MonitorDsp::begin() {
  memset(g_dec_hist, 0, sizeof(g_dec_hist));
  memset(g_bin_hist, 0, sizeof(g_bin_hist));
  memcpy(g_binaural, coeffs::kBinauralFir, sizeof(g_binaural));
  static_assert(sizeof(g_binaural) == 4 * 2 * kHrtfTaps * sizeof(float), "");
  measured_ = false;
  dropped_ = starved_ = 0;
  limiter_env_ = 0.0f;
  limiter_gain_ = 1.0f;
  tone_on_ = false;
  tone_phase_ = 0;
  setReferenceTone(false, cfg::kRefToneDbfs);
  setOutputTrimDb(cfg::kOutputTrimDb);
  g_fifo_w = g_fifo_r = 0;
  for (uint32_t i = 0; i < kFifoSlots; i++) g_fifo_full[i] = false;
}

void MonitorDsp::setOutputTrimDb(float db) {
  output_trim_db_ = clampf(db, cfg::kOutputTrimMinDb, cfg::kOutputTrimMaxDb);
  output_trim_lin_ = powf(10.0f, output_trim_db_ / 20.0f);
}

void MonitorDsp::setReferenceTone(bool on, float dbfs) {
  tone_dbfs_ = clampf(dbfs, -60.0f, -1.0f);
  tone_amp_ = powf(10.0f, tone_dbfs_ / 20.0f);
  tone_phase_ = 0;
  // The tone bypasses the limiter, so its envelope goes stale while the tone
  // runs. Reset it here or the first block after the tone stops would be
  // gain-reduced by whatever the limiter last saw.
  limiter_env_ = 0.0f;
  limiter_gain_ = 1.0f;
  tone_on_ = on;
}

float MonitorDsp::lineLoadLossDb(float external_ohms) {
  // R62 in series, then RV1 (always across the node) in parallel with
  // whatever is plugged in. An open jack is modelled as a very large load.
  const float ext = external_ohms > 1.0f ? external_ohms : 1.0e9f;
  const float load = (cfg::kLineInternalLoadOhms * ext) /
                     (cfg::kLineInternalLoadOhms + ext);
  const float ratio = load / (load + cfg::kLineSeriesOhms);
  return 20.0f * log10f(ratio);
}

float MonitorDsp::dbfsToLineVrms(float dbfs, float external_ohms) {
  const float at_dac = cfg::kDacFullScaleVrms * powf(10.0f, dbfs / 20.0f);
  return at_dac * powf(10.0f, lineLoadLossDb(external_ohms) / 20.0f);
}

float MonitorDsp::dbfsToLineDbu(float dbfs, float external_ohms) {
  // 0 dBu is 0.7746 Vrms.
  return 20.0f * log10f(dbfsToLineVrms(dbfs, external_ohms) / 0.7745967f);
}

float MonitorDsp::limiterGainDb() const {
  return 20.0f * log10f(limiter_gain_ > 1e-6f ? limiter_gain_ : 1e-6f);
}

void MonitorDsp::pushCaptureBlock(const Frame4* frames, uint32_t count) {
  const uint32_t w = g_fifo_w;
  if (g_fifo_full[w]) { dropped_++; return; }
  const uint32_t n = count < kNIn ? count : kNIn;
  memcpy(g_fifo[w], frames, n * sizeof(Frame4));
  if (n < kNIn) memset(&g_fifo[w][n], 0, (kNIn - n) * sizeof(Frame4));
  g_fifo_full[w] = true;
  g_fifo_w = (w + 1) % kFifoSlots;
}

void MonitorDsp::decimate(const float* in, uint32_t n_in, float* out, uint8_t ch) {
  float* hist = g_dec_hist[ch];
  const uint32_t carry = kDecTaps - 1;

  memcpy(hist + carry, in, n_in * sizeof(float));

  // Linear-phase symmetry: h[k] == h[taps-1-k], so fold the pairs and do half
  // the multiplies. 192 taps become 96 per output sample.
  const float* h = kDecimFir;
  const uint32_t half = kDecTaps / 2;
  const uint32_t n_out = n_in / kM;

  for (uint32_t j = 0; j < n_out; j++) {
    const float* newest = hist + carry + j * kM;   // x[n]
    float acc = 0.0f;
    for (uint32_t k = 0; k < half; k++) {
      const float a = newest[-(int32_t)k];
      const float b = newest[-(int32_t)(kDecTaps - 1 - k)];
      acc += (a + b) * h[k];
    }
    out[j] = acc;
  }

  memmove(hist, hist + n_in, carry * sizeof(float));
}

void MonitorDsp::render(float* left, float* right, uint32_t count) {
  const uint32_t t0 = ARM_DWT_CYCCNT;
  const uint32_t n = count < kNOut ? count : kNOut;

  // --- 0. Calibration tone -------------------------------------------------
  // Deliberately bypasses the binaural chain, the output trim AND the limiter,
  // so the level at the jack is exactly tone_dbfs_ and can be used to set gain
  // staging on whatever the line output is feeding. It still consumes a
  // capture block so the FIFO does not back up and start reporting drops.
  const uint32_t r = g_fifo_r;
  if (tone_on_) {
    // Keep the pipeline moving: discard one capture block if one is waiting.
    if (g_fifo_full[r]) {
      g_fifo_full[r] = false;
      g_fifo_r = (r + 1) % kFifoSlots;
    }
    // 1 kHz at 48 kHz is exactly 48 samples per cycle, so the tone is
    // bit-periodic and its amplitude is exact.
    const uint32_t period =
        (uint32_t)(cfg::kMonitorRateHz / (uint32_t)cfg::kRefToneHz);
    for (uint32_t i = 0; i < n; i++) {
      const float ph = 2.0f * (float)M_PI * (float)tone_phase_ / (float)period;
      const float v = tone_amp_ * sinf(ph);
      left[i] = v;
      right[i] = v;
      if (++tone_phase_ >= period) tone_phase_ = 0;
    }
    return;
  }

  if (!g_fifo_full[r]) {
    starved_++;
    memset(left, 0, n * sizeof(float));
    memset(right, 0, n * sizeof(float));
    return;
  }
  const Frame4* src = g_fifo[r];

  // --- 1. int24 to float, then anti-alias and decimate --------------------
  {
    // Reuse the decimator history tail as scratch for the float conversion.
    static DMAMEM float scratch[kNIn];
    for (uint8_t c = 0; c < cfg::kChannels; c++) {
      for (uint32_t i = 0; i < kNIn; i++) {
        scratch[i] = (float)src[i].ch[c] * (1.0f / 8388608.0f);
      }
      decimate(scratch, kNIn, g_a_format[c], c);
    }
  }
  g_fifo_full[r] = false;
  g_fifo_r = (r + 1) % kFifoSlots;

  // --- 2. A-format to B-format --------------------------------------------
  // kAtoB is row-major [bformat][capsule], capsule order FLU, FRD, BLD, BRU,
  // which is exactly the order cfg::Channel enumerates.
  for (uint32_t b = 0; b < 4; b++) {
    const float m0 = coeffs::kAtoB[b * 4 + 0];
    const float m1 = coeffs::kAtoB[b * 4 + 1];
    const float m2 = coeffs::kAtoB[b * 4 + 2];
    const float m3 = coeffs::kAtoB[b * 4 + 3];
    float* dst = g_b_format[b];
    for (uint32_t i = 0; i < kNOut; i++) {
      dst[i] = m0 * g_a_format[cfg::CH_FLU][i] + m1 * g_a_format[cfg::CH_FRD][i] +
               m2 * g_a_format[cfg::CH_BLD][i] + m3 * g_a_format[cfg::CH_BRU][i];
    }
  }

  // --- 3. Eight convolutions: each B-format channel into each ear ---------
  // Bound every write by n, not kNOut: the caller owns those buffers and may
  // legitimately ask for a shorter block.
  for (uint32_t i = 0; i < n; i++) { left[i] = 0.0f; right[i] = 0.0f; }

  const uint32_t carry = kHrtfTaps - 1;
  for (uint32_t b = 0; b < 4; b++) {
    float* hist = g_bin_hist[b];
    memcpy(hist + carry, g_b_format[b], kNOut * sizeof(float));
    const float* hl = g_binaural[b][0];
    const float* hr = g_binaural[b][1];
    for (uint32_t i = 0; i < n; i++) {
      const float* newest = hist + carry + i;
      left[i]  += firDot(newest, hl, kHrtfTaps);
      right[i] += firDot(newest, hr, kHrtfTaps);
    }
    memmove(hist, hist + kNOut, carry * sizeof(float));
  }

  // --- 4. Monitor gain and peak limiter ------------------------------------
  const float thresh = powf(10.0f, cfg::kLimiterThresholdDbfs / 20.0f);
  // One-pole envelope follower, written as  env += a * (peak - env).
  //
  // `a` is computed with expm1f rather than as (1 - expf(x)). For a 120 ms
  // release at 48 kHz the coefficient is 0.9998264, and subtracting that from
  // 1.0f in float32 throws away most of the significant digits: the resulting
  // time constant is out by 1.6e-4 relative. expm1f computes the small
  // quantity directly and keeps full precision. Inaudible at 120 ms, but it
  // gets worse the longer the release, and there is no reason to be wrong.
  const float a_atk =
      -expm1f(-1.0f / (cfg::kLimiterAttackMs * 0.001f * cfg::kMonitorRateHz));
  const float a_rel =
      -expm1f(-1.0f / (cfg::kLimiterReleaseMs * 0.001f * cfg::kMonitorRateHz));

  for (uint32_t i = 0; i < n; i++) {
    float l = left[i] * output_trim_lin_;
    float rr = right[i] * output_trim_lin_;
    const float pk = fabsf(l) > fabsf(rr) ? fabsf(l) : fabsf(rr);
    const float a = (pk > limiter_env_) ? a_atk : a_rel;
    limiter_env_ += a * (pk - limiter_env_);
    // One gain applied to both ears, so limiting can never move the image.
    limiter_gain_ = (limiter_env_ > thresh) ? (thresh / limiter_env_) : 1.0f;
    left[i]  = clampf(l * limiter_gain_, -1.0f, 1.0f);
    right[i] = clampf(rr * limiter_gain_, -1.0f, 1.0f);
  }

  const uint32_t cycles = ARM_DWT_CYCCNT - t0;
  const float budget = (float)F_CPU_ACTUAL * (float)kNOut / (float)cfg::kMonitorRateHz;
  const float pct = 100.0f * (float)cycles / budget;
  cpu_percent_ += 0.05f * (pct - cpu_percent_);   // gentle smoothing
}

bool MonitorDsp::loadHrtfFromSd(FsVolume* vol, char* reason, size_t reason_len) {
  auto fail = [&](const char* msg) {
    if (reason) snprintf(reason, reason_len, "%s", msg);
    return false;
  };
  if (!vol) return fail("no SD card mounted; using the built-in HRTF");

  FsFile f;
  if (!f.open(vol, cfg::kHrtfFileName, O_RDONLY)) {
    return fail("no HRTF.BIN on the card; using the built-in HRTF");
  }

  struct __attribute__((packed)) Header {
    char     magic[4];
    uint32_t version, rate, taps, channels, ears, rsv0, rsv1;
  } h;
  if (f.read(&h, sizeof(h)) != (int)sizeof(h)) {
    f.close();
    return fail("HRTF.BIN is truncated; using the built-in HRTF");
  }
  if (memcmp(h.magic, "QPRH", 4) != 0) {
    f.close();
    return fail("HRTF.BIN has a bad signature; using the built-in HRTF");
  }
  if (h.version != 1) {
    f.close();
    return fail("HRTF.BIN version is not supported; using the built-in HRTF");
  }
  if (h.rate != cfg::kMonitorRateHz) {
    f.close();
    if (reason) snprintf(reason, reason_len,
                         "HRTF.BIN is %lu Hz, firmware needs %lu Hz",
                         (unsigned long)h.rate, (unsigned long)cfg::kMonitorRateHz);
    return false;
  }
  if (h.channels != 4 || h.ears != 2) {
    f.close();
    return fail("HRTF.BIN has the wrong shape; using the built-in HRTF");
  }
  if (h.taps > kHrtfTaps) {
    f.close();
    if (reason) snprintf(reason, reason_len,
                         "HRTF.BIN has %lu taps, firmware is built for %lu -- "
                         "rerun build_hrtf.py --taps %lu",
                         (unsigned long)h.taps, (unsigned long)kHrtfTaps,
                         (unsigned long)kHrtfTaps);
    return false;
  }

  // Load into a staging copy so a short read cannot leave half a filter set
  // in the live table.
  static DMAMEM float staging[4][2][kHrtfTaps];
  memset(staging, 0, sizeof(staging));
  for (uint32_t b = 0; b < 4; b++) {
    for (uint32_t e = 0; e < 2; e++) {
      const int want = (int)(h.taps * sizeof(float));
      if (f.read(staging[b][e], want) != want) {
        f.close();
        return fail("HRTF.BIN is shorter than its header claims");
      }
    }
  }
  f.close();

  __disable_irq();
  memcpy(g_binaural, staging, sizeof(g_binaural));
  memset(g_bin_hist, 0, sizeof(g_bin_hist));
  __enable_irq();

  measured_ = true;
  if (reason) snprintf(reason, reason_len,
                       "loaded HRTF.BIN (%lu taps) from the card",
                       (unsigned long)h.taps);
  return true;
}

// ===========================================================================
// Meters
// ===========================================================================
void Meters::reset() {
  // Same critical section as read(): accumulate() runs in the priority-96
  // capture interrupt and does a read-modify-write of the 64-bit sum of
  // squares. Clearing it unprotected can leave sumsq_ and count_ describing
  // different spans of audio, which shows up as an RMS reading above 0 dBFS.
  __disable_irq();
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    peak_[c] = 0; sumsq_[c] = 0; clip_ms_[c] = 0;
  }
  count_ = 0;
  __enable_irq();
  for (uint8_t c = 0; c < cfg::kChannels; c++) held_peak_[c] = -120.0f;
  last_read_ms_ = millis();
}

void Meters::accumulate(const Frame4* frames, uint32_t count) {
  // Full-scale for a 24-bit sample is 2^23. Anything at or above 2^23 - 8 has
  // effectively hit the ADC rail.
  constexpr int32_t kClipLevel = 8388600;
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    uint32_t pk = peak_[c];
    uint64_t ss = sumsq_[c];
    bool clipped = false;
    for (uint32_t i = 0; i < count; i++) {
      int32_t v = frames[i].ch[c];
      uint32_t a = (uint32_t)(v < 0 ? -v : v);
      if (a > pk) pk = a;
      ss += (uint64_t)((int64_t)v * (int64_t)v);
      if ((int32_t)a >= kClipLevel) clipped = true;
    }
    peak_[c] = pk;
    sumsq_[c] = ss;
    if (clipped) clip_ms_[c] = millis();
  }
  count_ += count;
}

void Meters::read(Reading* out) {
  const uint32_t now = millis();
  const float dt = (float)(now - last_read_ms_) * 0.001f;
  last_read_ms_ = now;

  uint32_t pk[cfg::kChannels];
  uint64_t ss[cfg::kChannels];
  uint32_t n;
  uint32_t clip[cfg::kChannels];

  __disable_irq();
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    pk[c] = peak_[c];  peak_[c] = 0;
    ss[c] = sumsq_[c]; sumsq_[c] = 0;
    clip[c] = clip_ms_[c];
  }
  n = count_; count_ = 0;
  __enable_irq();

  constexpr float kFullScale = 8388608.0f;
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    const float peak_lin = (float)pk[c] / kFullScale;
    const float inst = peak_lin > 1e-7f ? 20.0f * log10f(peak_lin) : -120.0f;

    // Peak hold with a linear decay, so a transient stays visible.
    const float decayed = held_peak_[c] - cfg::kMeterDecayDbPerSec * dt;
    held_peak_[c] = inst > decayed ? inst : decayed;
    if (held_peak_[c] < -120.0f) held_peak_[c] = -120.0f;
    out->peak_dbfs[c] = held_peak_[c];

    if (n > 0) {
      const float mean_sq = (float)((double)ss[c] / (double)n);
      const float rms = sqrtf(mean_sq) / kFullScale;
      out->rms_dbfs[c] = rms > 1e-7f ? 20.0f * log10f(rms) : -120.0f;
    } else {
      out->rms_dbfs[c] = -120.0f;
    }
    out->clipped[c] = (clip[c] != 0) && (now - clip[c] < cfg::kClipHoldMs);
  }
}

}  // namespace qpr
