// qpr_dsp.h — the real-time monitor path: decimate, decode, render, limit
//
// Vendor: Illicit Apothecary
//
// Chain, exactly as sim/simulate_binaural.py runs it:
//
//   4 ch @ 192 kHz int24
//        |  anti-alias FIR (kDecimatorFir), decimate 4:1 -- linear phase, so
//        |  the implementation folds the symmetric taps and does half the work
//   4 ch @ 48 kHz float                                    (A-format)
//        |  4x4 matrix (kAtoB)
//   W, X, Y, Z @ 48 kHz                                    (B-format, SN3D)
//        |  8 FIRs (kBinauralFir): each B-format channel into each ear
//   L, R @ 48 kHz
//        |  peak limiter
//   PCM5102A
//
// Every coefficient comes from qpr_coeffs.h, which sim/build_hrtf.py generates.
// Nothing here is recomputed on the MCU, so the desktop simulator and the
// firmware cannot drift apart.
//
// Runs inside a low-priority software interrupt, below both audio DMA
// interrupts. If the DSP overruns its budget the monitor glitches; capture and
// SD writing are unaffected. cpuPercent() reports the real measured load --
// check it on hardware before raising kHrtfTaps.

#pragma once
#include <Arduino.h>
#include <SdFat.h>
#include "qpr_config.h"
#include "qpr_sai.h"

namespace qpr {

class MonitorDsp {
 public:
  // Loads the compiled-in coefficient set. Call once at boot.
  void begin();

  // Replaces the binaural filters with a set read from the SD card.
  // Returns false and leaves the built-in set in place if the file is
  // missing, malformed, or generated for a different tap count / rate.
  // `reason` receives a human-readable explanation either way.
  bool loadHrtfFromSd(FsVolume* vol, char* reason, size_t reason_len);
  bool usingMeasuredHrtf() const { return measured_; }

  // --- capture interrupt context ------------------------------------------
  // Hands one capture block to the DSP. Non-blocking: if the DSP has fallen
  // behind, the block is dropped and dropped() increments.
  void pushCaptureBlock(const Frame4* frames, uint32_t count);

  // --- DSP interrupt context ----------------------------------------------
  // Produces one monitor block. Emits silence if no capture block is waiting.
  void render(float* left, float* right, uint32_t count);

  // --- telemetry -----------------------------------------------------------
  uint32_t dropped()    const { return dropped_; }
  uint32_t starved()    const { return starved_; }
  // Fraction of one CPU spent inside render(), 0..100.
  float    cpuPercent() const { return cpu_percent_; }
  // Most recent limiter gain reduction, in dB (0 = not limiting).
  float    limiterGainDb() const;

  // Digital trim on the rendered stereo pair. This is the LAST thing before
  // the DAC, and the DAC feeds both jacks, so it moves the line output and
  // the headphone output together. The RV1 knob is the headphone-only
  // control; it sits after the split, in the analog domain.
  void setOutputTrimDb(float db);
  float outputTrimDb() const { return output_trim_db_; }

  // Calibration tone on both outputs. Bypasses the binaural chain, the output
  // trim AND the limiter, so the level at the jack is exactly what you ask
  // for: -20 dBFS gives 0.21 Vrms, which is -11.3 dBu.
  void setReferenceTone(bool on, float dbfs = cfg::kRefToneDbfs);
  bool referenceToneActive() const { return tone_on_; }
  float referenceToneDbfs() const { return tone_dbfs_; }
  // Expected RMS at the 1/4 inch jack for a given digital level. Starts from
  // the PCM5102A's 2.1 Vrms full scale and applies the R62/R63 series
  // resistor loaded by RV1 in parallel with `external_ohms`.
  static float dbfsToLineVrms(float dbfs,
                              float external_ohms = cfg::kLineAssumedExternalOhms);
  static float dbfsToLineDbu(float dbfs,
                             float external_ohms = cfg::kLineAssumedExternalOhms);
  // Loss from the DAC pin to the jack, in dB, for a given external load.
  static float lineLoadLossDb(float external_ohms);

 private:
  void decimate(const float* in, uint32_t n_in, float* out, uint8_t ch);

  bool  measured_ = false;
  volatile uint32_t dropped_ = 0;
  volatile uint32_t starved_ = 0;
  float cpu_percent_ = 0.0f;
  float output_trim_db_ = 0.0f;
  float output_trim_lin_ = 1.0f;
  bool  tone_on_ = false;
  float tone_dbfs_ = cfg::kRefToneDbfs;
  float tone_amp_ = 0.0f;
  uint32_t tone_phase_ = 0;
  float limiter_env_ = 0.0f;
  float limiter_gain_ = 1.0f;
};

// ---------------------------------------------------------------------------
// Level meters. Peak and RMS are accumulated in the capture interrupt at the
// full 192 kHz rate -- meters that only see the decimated monitor stream would
// miss ultrasonic overload that still clips the ADC.
// ---------------------------------------------------------------------------
class Meters {
 public:
  void reset();
  // capture interrupt context
  void accumulate(const Frame4* frames, uint32_t count);
  // thread context: snapshot and clear the accumulators
  struct Reading {
    float peak_dbfs[cfg::kChannels];
    float rms_dbfs[cfg::kChannels];
    bool  clipped[cfg::kChannels];
  };
  void read(Reading* out);

 private:
  volatile uint32_t peak_[cfg::kChannels] = { 0, 0, 0, 0 };
  volatile uint64_t sumsq_[cfg::kChannels] = { 0, 0, 0, 0 };
  volatile uint32_t count_ = 0;
  volatile uint32_t clip_ms_[cfg::kChannels] = { 0, 0, 0, 0 };
  float held_peak_[cfg::kChannels] = { -120.0f, -120.0f, -120.0f, -120.0f };
  uint32_t last_read_ms_ = 0;
};

}  // namespace qpr
