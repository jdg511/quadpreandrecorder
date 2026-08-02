// qpr_recorder.h — four simultaneous mono WAV streams to microSD
//
// Vendor: Illicit Apothecary
//
// Real-time contract:
//   pushFrames()  runs inside the capture DMA interrupt. It only packs bytes
//                 into lock-free ring buffers. No allocation, no file I/O, no
//                 blocking, no floating point.
//   service()     runs at thread level from loop(). It does every SD access.
//   Producer and consumer never touch the same ring index, so no critical
//   sections are needed on a single core.
//
// File format:
//   One mono 24-bit WAV per capsule: FLUnnn.WAV, FRDnnn.WAV, BLDnnn.WAV,
//   BRUnnn.WAV, all sharing one take number nnn.
//   Audio data always starts at byte offset 512 so every subsequent write is
//   SD-block aligned. Past 4 GiB the finished header is written as RF64.
//
// Take numbering:
//   At start() the card is scanned for ALL FOUR prefixes and the next take is
//   (highest number seen on any of them) + 1. A half-written previous set --
//   say FLU007 exists but BRU007 does not -- can therefore never be
//   overwritten by the next recording.

#pragma once
#include <Arduino.h>
#include <SdFat.h>
#include "qpr_config.h"
#include "qpr_sai.h"

namespace qpr {

class Recorder {
 public:
  enum class Error : uint8_t {
    None = 0,
    NoCard,
    ScanFailed,
    CreateFailed,
    PreallocateFailed,
    WriteFailed,
    Overrun,        // capture outran the card; samples were dropped
  };
  static const char* errorName(Error e);

  // Mounts the card. Returns false if the card is missing or unformatted.
  bool begin();
  bool cardMounted() const { return mounted_; }

  // Highest take number currently on the card (0 if none). Valid after begin().
  uint32_t lastTakeOnCard() const { return last_take_; }

  // Opens and preallocates the four files for take lastTakeOnCard()+1.
  bool start();
  // Flushes everything still buffered, truncates the files to their real
  // length, and writes the final headers. Safe to call when not recording.
  void stop();

  bool recording() const { return recording_; }
  uint32_t takeNumber() const { return take_; }

  // --- interrupt context ---------------------------------------------------
  // Appends one capture block to all four rings, or to NONE of them.
  // The all-or-nothing rule is load-bearing: this is an ambisonic recorder,
  // and four files that are individually intact but time-shifted relative to
  // each other decode to a smeared, rotated sound field. That failure is
  // silent and unrecoverable, so a gap in all four is strictly better than a
  // gap in one.
  void pushFrames(const Frame4* frames, uint32_t count);

  // --- thread context ------------------------------------------------------
  // Call as often as possible from loop(). Writes at most one chunk per
  // channel per call so the caller keeps control of its own timing.
  void service();

  // --- telemetry -----------------------------------------------------------
  // Frames actually committed to all four rings. Dropped frames are NOT
  // counted, so this always matches the length of the files on the card.
  uint64_t framesRecorded() const;
  float    elapsedSeconds() const {
    return (float)framesRecorded() / (float)cfg::kSampleRateHz;
  }
  // Frames lost to overruns. Non-zero means the take has gaps.
  uint64_t framesDropped() const;
  // Worst-case ring occupancy since start, 0..1. This is the number that tells
  // you whether the card is keeping up. Under ~0.5 is comfortable; sustained
  // above ~0.8 means the card is marginal for 192 kHz four-channel.
  float    peakBufferUse() const { return peak_use_; }
  // Longest single SD write, in microseconds. Card stalls show up here.
  uint32_t maxWriteMicros() const { return max_write_us_; }
  uint32_t overrunCount()   const { return overruns_; }
  Error    lastError()      const { return last_error_; }
  // The mounted volume, for other subsystems that need to read a file
  // from the same card (the DSP loads HRTF.BIN through this).
  FsVolume* volume() { return mounted_ ? &sd_ : nullptr; }

  // Free space on the card, in bytes. CACHED: the underlying exFAT free-
  // cluster scan can take tens of milliseconds, which is long enough to
  // starve the SD writer if it were called at the display refresh rate. The
  // cache refreshes on a timer, and never while recording -- during a take
  // the figure is extrapolated from what has already been written.
  uint64_t freeSpaceBytes();
  // Seconds of recording the remaining card space allows, at the current rate.
  float    remainingSeconds();
  // Forces the next freeSpaceBytes() to do a real scan.
  void     invalidateFreeSpace() { free_cache_ms_ = 0; }

 private:
  bool scanExistingTakes();
  bool openFiles(uint32_t take);
  void writeHeader(FsFile& f, uint64_t data_bytes, bool final_write);
  bool writeChunk(uint8_t ch);

  SdFs   sd_;
  FsFile file_[cfg::kChannels];
  bool   mounted_   = false;
  volatile bool recording_ = false;   // written by thread, read by the ISR
  uint32_t take_    = 0;
  uint32_t last_take_ = 0;

  // Lock-free SPSC rings, one per channel, holding packed 24-bit LE bytes.
  uint8_t* ring_[cfg::kChannels] = { nullptr, nullptr, nullptr, nullptr };
  volatile uint32_t head_[cfg::kChannels] = { 0, 0, 0, 0 };  // written by ISR
  volatile uint32_t tail_[cfg::kChannels] = { 0, 0, 0, 0 };  // written by loop

  volatile uint64_t frames_written_ = 0;
  volatile uint64_t frames_dropped_ = 0;
  volatile uint32_t overruns_ = 0;
  volatile bool     overrun_flag_ = false;   // ISR sets, service() folds in
  bool     prealloc_ok_ = true;
  float    peak_use_ = 0.0f;
  uint32_t max_write_us_ = 0;
  uint32_t last_header_ms_ = 0;
  uint64_t data_bytes_[cfg::kChannels] = { 0, 0, 0, 0 };
  Error    last_error_ = Error::None;

  uint64_t free_cache_bytes_ = 0;
  uint32_t free_cache_ms_ = 0;
  uint64_t free_at_start_ = 0;
  static constexpr uint32_t kFreeCacheMs = 15000;
};

}  // namespace qpr
