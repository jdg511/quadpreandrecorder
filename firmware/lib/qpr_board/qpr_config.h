// qpr_config.h — build-time configuration for the QuadPreRecorder firmware
//
// Vendor: Illicit Apothecary
//
// Everything you would reasonably want to change without reading driver code
// lives here. Values that are electrically load-bearing say so.

#pragma once
#include <stdint.h>

namespace qpr {
namespace cfg {

// ---------------------------------------------------------------------------
// Capture rate
// ---------------------------------------------------------------------------
// MODE_DUAL_I2S_192K (default)
//   PCM1864 in plain I2S, 2 channels per data line, two data lines.
//   DOUT  (Teensy pin 8) = ch1 L/R = FLU, FRD
//   DOUT2 (Teensy pin 6) = ch2 L/R = BLD, BRU
//   MCLK 24.576 MHz (128 fs), BCLK 12.288 MHz (64 fs), LRCLK 192 kHz.
//
// MODE_TDM_96K (fallback)
//   PCM1864 in 4-channel TDM on the single DOUT line.
//   The PCM1864 TDM frame is fixed at 256 BCK, so 192 kHz would need a
//   49.152 MHz bit clock; that is why TDM is a 96 kHz-only fallback.
//   MCLK 49.152 MHz (512 fs), BCLK 24.576 MHz (256 fs), LRCLK 96 kHz.
#define QPR_MODE_DUAL_I2S_192K 0
#define QPR_MODE_TDM_96K       1

#ifndef QPR_CAPTURE_MODE
#define QPR_CAPTURE_MODE QPR_MODE_DUAL_I2S_192K
#endif

#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
constexpr uint32_t kSampleRateHz = 192000;
#else
constexpr uint32_t kSampleRateHz = 96000;
#endif

// Monitor / DAC rate. Chosen so that kSampleRateHz is an exact integer
// multiple of it AND both SAI blocks can run from one 786.432 MHz audio PLL.
// Do not change this to a non-divisor: the decimator is integer-ratio only.
constexpr uint32_t kMonitorRateHz = 48000;
constexpr uint32_t kDecimationFactor = kSampleRateHz / kMonitorRateHz;  // 4 or 2

constexpr uint8_t kChannels = 4;

// Channel order. This order is fixed by the hardware:
//   PCM1864 VINL1 (pin 3) = FLU_ADC -> ch1 L
//   PCM1864 VINR1 (pin 4) = FRD_ADC -> ch1 R
//   PCM1864 VINL2 (pin 1) = BLD_ADC -> ch2 L
//   PCM1864 VINR2 (pin 2) = BRU_ADC -> ch2 R
enum Channel : uint8_t { CH_FLU = 0, CH_FRD = 1, CH_BLD = 2, CH_BRU = 3 };
constexpr const char* kChannelNames[kChannels] = { "FLU", "FRD", "BLD", "BRU" };

// ---------------------------------------------------------------------------
// DMA and buffering
// ---------------------------------------------------------------------------
// Frames per DMA half-buffer. The capture ISR fires every
// kDmaFramesPerHalf / kSampleRateHz seconds (256 / 192000 = 1.333 ms).
// Must be a multiple of kDecimationFactor.
constexpr uint32_t kDmaFramesPerHalf = 256;

// Bytes handed to SdFat per write() call. This has to be a multiple of 512
// (SD block size) AND of 3 (packed 24-bit sample size), or every write would
// straddle a block boundary and throughput would collapse.
// 24576 = 512 * 48 = 3 * 8192.
constexpr uint32_t kSdWriteChunkBytes = 24576u;

// Per-channel elastic ring between the capture ISR and the SD writer, in
// whole write chunks. 3 chunks = 72 KiB = 72*1024 / 576000 = 128 ms of slack
// for a microSD erase/program pause. Total RAM cost = 4 x 72 KiB = 288 KiB of
// the Teensy 4.1's 512 KiB OCRAM. Raise it if t04_sd_benchmark shows your
// card stalling for longer than that; watch the RAM2 figure when you do.
constexpr uint32_t kRingChunksPerChannel = 3;
constexpr uint32_t kRingBytesPerChannel =
    kSdWriteChunkBytes * kRingChunksPerChannel;

// Every WAV file's audio data starts at byte 512 so that all subsequent
// writes land on SD block boundaries. The space before it is a RIFF header
// plus padding chunks, including a reserved slot for an RF64 'ds64' chunk.
constexpr uint32_t kWavHeaderBytes = 512;

// ---------------------------------------------------------------------------
// Recording
// ---------------------------------------------------------------------------
// Preallocated length per file, in seconds. Preallocation is what keeps the
// FAT from being touched mid-recording. Files are truncated to the real
// length on stop.
constexpr uint32_t kPreallocateSeconds = 60 * 60;  // 1 hour per channel

// WAV data chunks cannot exceed 4 GiB - 1. Above this the writer switches the
// finished header to RF64. 192 kHz / 24-bit mono hits 4 GiB at ~2.07 hours.
constexpr uint64_t kWavRiffLimitBytes = 0xFFFFFFFFull - 1024ull;

// How often the writer refreshes the in-progress RIFF sizes so that a file
// left behind by a power cut is still playable.
constexpr uint32_t kHeaderRefreshMs = 5000;

// ---------------------------------------------------------------------------
// Gain
// ---------------------------------------------------------------------------
// PCM1864 PGA register range is -12.0 dB .. +40.0 dB in 0.5 dB steps, but only
// -12 .. +32 dB is analog gain; above +32 dB the part makes up the difference
// digitally, which costs noise floor. Default cap is +32 dB.
constexpr float kPgaMinDb = -12.0f;
constexpr float kPgaMaxDb =  32.0f;
constexpr float kPgaStepDb = 0.5f;
constexpr float kPgaDefaultDb = 0.0f;

// Encoder detents per 1 dB of gain change. EC11 with 4 quadrature edges per
// detent -> one detent = one step.
constexpr float kGainDbPerDetent = 1.0f;

// ---------------------------------------------------------------------------
// Monitor DSP
// ---------------------------------------------------------------------------
// Block size for the monitor path, in samples at kMonitorRateHz.
// kDmaFramesPerHalf / kDecimationFactor = 256 / 4 = 64.
constexpr uint32_t kMonitorBlockSamples = kDmaFramesPerHalf / kDecimationFactor;

// Length of each ambisonic-to-binaural FIR, in taps, at kMonitorRateHz.
// Cost is 8 FIRs (4 B-format channels x 2 ears) of this length.
// 256 taps -> 8 * 256 * 48000 = 98 MMAC/s, roughly 20-25% of one Cortex-M7.
constexpr uint32_t kHrtfTaps = 128;

// Microphone geometry used by the A-format-to-B-format correction filters.
// Measure the real capsule array and update this: it is the single number
// that most affects how the monitor sounds.
constexpr float kCapsuleRadiusMeters = 0.015f;

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
// There is ONE stereo DAC and ONE binaural signal. It splits in the analog
// domain after the reconstruction filter (R62/R63 + C67/C68):
//
//   PCM5102A OUTL/OUTR -> R62/R63 470R -> LINE_L / LINE_R
//        |
//        +--> J4, the 1/4 inch line output          (fixed level)
//        |
//        +--> RV1 10k audio-taper volume -> C57/C58 -> TPA6132A2
//                  -> R65/R66 10R -> J5, the 1/8 inch headphone output
//
// So both jacks carry the same binaural render. RV1 changes the headphone
// level ONLY; kOutputTrimDb below changes BOTH, because it acts digitally
// before the DAC.
//
// PCM5102A full scale is 2.1 Vrms, ground-centred (no DC blocking caps).
// With the limiter ceiling at -1 dBFS the line output tops out near
// 1.87 Vrms = +7.6 dBu. Set the receiving device so that 0 dBFS here does not
// clip its input: 0 dBFS at the jack is about +8.6 dBu.
constexpr float kDacFullScaleVrms = 2.1f;

// The 2.1 Vrms figure is at the PCM5102A pin. What arrives at J4 is divided
// by the series resistor and whatever loads the node. RV1 sits across that
// node permanently, so it is part of the load even with nothing plugged in.
constexpr float kLineSeriesOhms = 470.0f;      // R62 / R63
constexpr float kLineInternalLoadOhms = 10000.0f;  // RV1, always present
// Assumed external load for the reported line level. Almost all modern line
// inputs are 10 k or higher. A 600 ohm input costs about 5 dB HERE AND ON THE
// HEADPHONES, because the split is upstream of the volume pot.
constexpr float kLineAssumedExternalOhms = 10000.0f;

// Digital trim applied to BOTH outputs, before the limiter. Use this to match
// the line output to whatever you feed; use the RV1 knob for headphone level.
constexpr float kOutputTrimDb = 0.0f;
constexpr float kOutputTrimMinDb = -40.0f;
constexpr float kOutputTrimMaxDb = 12.0f;

// Built-in calibration tone. Exactly 1 kHz at 48 kHz is 48 samples per cycle,
// so the tone is bit-periodic and its level is exact.
constexpr float kRefToneHz = 1000.0f;
constexpr float kRefToneDbfs = -20.0f;

// Output limiter, applied after binaural rendering, before the DAC.
constexpr float kLimiterThresholdDbfs = -1.0f;
constexpr float kLimiterAttackMs      = 1.0f;
constexpr float kLimiterReleaseMs     = 120.0f;

// Filename on the SD card holding a measured HRTF set. If present and valid,
// it replaces the compiled-in analytic set at boot. Generate it with
// sim/build_hrtf.py --measured.
constexpr const char* kHrtfFileName = "HRTF.BIN";

// ---------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------
constexpr uint32_t kMeterUpdateHz = 25;      // TFT redraw rate
constexpr float    kMeterDecayDbPerSec = 20.0f;
constexpr uint32_t kClipHoldMs = 2000;
constexpr uint8_t  kTftRotation = 1;         // 320x240 landscape

}  // namespace cfg
}  // namespace qpr
