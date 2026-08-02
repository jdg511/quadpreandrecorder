// qpr_sai.h — bare-metal SAI1 four-channel capture and SAI2 stereo monitor out
//
// Vendor: Illicit Apothecary
//
// Why this is not the Teensy Audio Library:
//   The Audio Library is hard-wired to 44.1 kHz, 128-sample blocks of int16.
//   This recorder needs 192 kHz, 24-bit, four simultaneous channels, and an
//   independent 48 kHz monitor output. So SAI1 and SAI2 are configured
//   directly. The register sequences below follow PaulStoffregen/Audio's
//   proven IMXRT paths (output_i2s.cpp, input_i2s_quad.cpp, output_i2s2.cpp)
//   with the sample rate, word width and DMA element size changed.
//
// Clock plan (all exact, no fractional error anywhere):
//   Audio PLL (PLL4) = 24 MHz x 32.768 = 786.432 MHz
//     SAI1 root = PLL4 / (PRED 4 x PODF 8)  = 24.576 MHz  = MCLK  = 128 fs
//       BCLK    = MCLK / 2                  = 12.288 MHz  = 64 fs
//       LRCLK   = BCLK / 64                 = 192.000 kHz
//     SAI2 root = PLL4 / (PRED 4 x PODF 16) = 12.288 MHz  = 256 fs
//       BCLK    = root / 4                  =  3.072 MHz  = 64 fs
//       LRCLK   = BCLK / 64                 =  48.000 kHz
//   Because both come from one PLL, the monitor rate is exactly the capture
//   rate / 4. The decimator is a fixed integer ratio with zero drift; there is
//   no asynchronous sample-rate conversion anywhere in the monitor path.
//
// 96 kHz TDM fallback:
//     SAI1 root = PLL4 / (PRED 4 x PODF 4)  = 49.152 MHz  = MCLK  = 512 fs
//       BCLK    = MCLK / 2                  = 24.576 MHz  = 256 fs
//       LRCLK   = BCLK / 256                =  96.000 kHz
//
// PIN HAZARD: SAI2's MCLK function lives on Teensy pin 33, which this board
// uses for HP_ENABLE. This driver never muxes pin 33 to SAI2. The PCM5102A
// has SCK tied to ground and recovers its clock from BCK internally, so no
// DAC master clock is needed.

#pragma once
#include <Arduino.h>
#include <stdint.h>
#include "qpr_config.h"

namespace qpr {

// One frame of four simultaneous samples, sign-extended 24-bit in int32.
struct Frame4 {
  int32_t ch[cfg::kChannels];  // indexed by cfg::CH_FLU .. cfg::CH_BRU
};

// Called from the capture DMA interrupt once per half-buffer.
// `frames` points at kDmaFramesPerHalf deinterleaved frames.
// MUST be short and must not block, allocate, or touch the SD card.
using CaptureCallback = void (*)(const Frame4* frames, uint32_t count);

// Called from a low-priority software interrupt to produce the next monitor
// block. Fill `left`/`right` with kMonitorBlockSamples float samples in
// [-1.0, 1.0]. Runs below the capture interrupt, above thread level.
using MonitorCallback = void (*)(float* left, float* right, uint32_t count);

class SaiCapture {
 public:
  // Configures PLL4, SAI1 and the capture DMA, then starts the clocks.
  // The PCM1864 must be configured (Pcm1864::begin) BEFORE clocks start if you
  // want a clean first frame, but the part tolerates either order.
  void begin(CaptureCallback cb);
  void stop();

  // Diagnostics, all updated from the interrupt.
  uint32_t blocksCaptured() const { return blocks_; }
  uint32_t overruns()       const { return overruns_; }
  uint32_t maxIsrMicros()   const { return max_isr_us_; }
  void     resetStats();

  // Actual generated clock rates, computed from the dividers actually written.
  static uint32_t mclkHz();
  static uint32_t bclkHz();
  static uint32_t lrclkHz();

 private:
  static void dmaIsr();
  static SaiCapture* instance_;
  CaptureCallback cb_ = nullptr;
  volatile uint32_t blocks_ = 0;
  volatile uint32_t overruns_ = 0;
  volatile uint32_t max_isr_us_ = 0;
};

class SaiMonitorOut {
 public:
  // Configures SAI2 and its DMA, and installs the low-priority DSP interrupt.
  // Leaves the PCM5102A muted; call qpr::board::setDacMuted(false) once the
  // stream is known good (the DAC powers up muted via R60).
  void begin(MonitorCallback cb);
  void stop();

  // Blocks the DAC had to fill with silence because no rendered block was
  // ready. A steady trickle means the DSP is too expensive.
  uint32_t underruns() const { return underruns_; }
  // Times the DSP interrupt hit its CPU budget and yielded early. Non-zero
  // means the monitor is over-configured; lower cfg::kHrtfTaps.
  uint32_t dspOverBudget() const { return over_budget_; }

 private:
  static void dmaIsr();
  static void dspIsr();
  static SaiMonitorOut* instance_;
  MonitorCallback cb_ = nullptr;
  volatile uint32_t underruns_ = 0;
  volatile uint32_t over_budget_ = 0;
};

}  // namespace qpr
