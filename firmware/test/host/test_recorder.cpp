// test_recorder.cpp — run the REAL four-stream WAV writer on a desktop
//
// Vendor: Illicit Apothecary
//
// Links lib/qpr_recorder/qpr_recorder.cpp unmodified against a stdio-backed
// SdFat shim, and drives it the way main.cpp does: pushFrames() from the
// "capture interrupt", service() from the "main loop".
//
// The point is not to prove the recorder writes a file. It is to prove what
// happens when the card MISBEHAVES, which is the only failure mode that
// actually loses takes and the only one you cannot discover by reading code.
//
// Cases covered:
//   1. clean run           -- four files, equal length, correct contents
//   2. survivable stall    -- a 100 ms pause the 128 ms buffer absorbs
//   3. fatal stall         -- a 400 ms pause that must overrun, and must do so
//                             COLLECTIVELY, leaving all four files the same
//                             length and still sample-aligned
//   4. accounting          -- written frames + dropped frames == pushed frames
//   5. take numbering      -- a half-written previous set is never overwritten
//
// Every sample carries its own frame index, so a desynchronised channel is
// detectable exactly rather than by ear.

#include <Arduino.h>
#include <SdFat.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>

#include "qpr_config.h"
#include "qpr_sai.h"
#include "qpr_recorder.h"

using namespace qpr;

static int g_failures = 0;

static void check(bool ok, const char* what, const char* detail = "") {
  printf("  [%s] %s%s%s\n", ok ? "PASS" : "FAIL", what,
         detail[0] ? "  " : "", detail);
  if (!ok) g_failures++;
}

// Each sample encodes (frame_index, channel) so misalignment is provable.
//   value = (frame & 0xFFFFF) * 16 + channel
// 20 bits of frame index is 1,048,576 frames = 5.46 s at 192 kHz. Keep test
// runs shorter than that or the tag wraps and the monotonicity check trips on
// its own arithmetic rather than on a real fault.
static constexpr uint64_t kMaxTaggedFrames = 1ull << 20;
static inline int32_t stamp(uint64_t frame, uint8_t ch) {
  return (int32_t)(((uint32_t)(frame & 0xFFFFFu) << 4) | ch);
}

struct FileCheck {
  bool     opened = false;
  uint64_t data_bytes = 0;
  uint64_t frames = 0;
  bool     channel_ok = true;      // every sample's channel tag matches
  bool     monotonic = true;       // frame tags never go backwards
  uint64_t first_frame = 0;
  uint64_t last_frame = 0;
  uint64_t gaps = 0;               // discontinuities in the frame tags
  std::vector<uint64_t> tags;      // frame index of every stored sample
};

static FileCheck readAndCheck(const std::string& path, uint8_t ch) {
  FileCheck r;
  FILE* f = fopen(path.c_str(), "rb");
  if (!f) return r;
  r.opened = true;

  fseek(f, 0, SEEK_END);
  const long size = ftell(f);
  fseek(f, cfg::kWavHeaderBytes, SEEK_SET);
  r.data_bytes = (uint64_t)size - cfg::kWavHeaderBytes;
  r.frames = r.data_bytes / 3;
  r.tags.reserve(r.frames);

  uint8_t b[3];
  uint64_t prev = 0;
  bool first = true;
  while (fread(b, 1, 3, f) == 3) {
    const uint32_t v = (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
                       ((uint32_t)b[2] << 16);
    const uint8_t tag_ch = (uint8_t)(v & 0x0F);
    const uint64_t tag_frame = (v >> 4) & 0xFFFFFu;
    if (tag_ch != ch) r.channel_ok = false;
    if (first) { r.first_frame = tag_frame; first = false; }
    else {
      if (tag_frame < prev) r.monotonic = false;
      if (tag_frame != prev + 1) r.gaps++;
    }
    prev = tag_frame;
    r.tags.push_back(tag_frame);
  }
  r.last_frame = prev;
  fclose(f);
  return r;
}

// Drives the recorder for `blocks` capture blocks. `stall_at_block` schedules
// one SD write to take `stall_us`. Returns the recorder's own accounting.
struct RunResult {
  uint64_t pushed = 0;
  uint64_t recorded = 0;
  uint64_t dropped = 0;
  uint32_t overruns = 0;
  float    peak_use = 0.0f;
  uint32_t take = 0;
};

static RunResult runTake(Recorder& rec, uint32_t blocks,
                         uint32_t stall_at_block, uint32_t stall_us) {
  RunResult out;
  const uint32_t N = cfg::kDmaFramesPerHalf;
  std::vector<Frame4> frames(N);

  hostsd::reset();
  if (stall_us) {
    // Each capture block produces N * 3 bytes per channel, and a write moves
    // kSdWriteChunkBytes. Across all four channels that is well under one
    // write per block, so the index has to be computed in floating point --
    // integer division here rounds to zero and schedules the stall at a write
    // number the run never reaches, which silently disables the test.
    const double writes_per_block =
        (double)(N * 3 * cfg::kChannels) / (double)cfg::kSdWriteChunkBytes;
    const uint32_t idx = (uint32_t)(stall_at_block * writes_per_block);
    hostsd::injectStall(idx, stall_us);
    printf("  (stall of %.0f ms scheduled at SD write #%lu)\n",
           stall_us / 1000.0, (unsigned long)idx);
  }

  if (!rec.start()) {
    printf("  ! recorder.start() failed: %s\n",
           Recorder::errorName(rec.lastError()));
    return out;
  }
  out.take = rec.takeNumber();

  // The capture interrupt is driven by the VIRTUAL CLOCK, not by loop
  // iterations. This is the whole point: when service() blocks for 400 ms
  // inside a stalled SD write, the ADC does not politely wait -- 300 blocks
  // of audio become due the moment the write returns, and they have to fit in
  // a ring that only holds 96 blocks. Driving capture off the iteration count
  // instead would make every stall survivable and the test meaningless.
  const uint64_t block_us = 1000000ull * N / cfg::kSampleRateHz;
  uint64_t next_capture_us = qpr_host::g_micros;
  uint64_t frame_index = 0;
  uint32_t delivered = 0;

  while (delivered < blocks) {
    // Deliver every capture block that has come due.
    while (qpr_host::g_micros >= next_capture_us && delivered < blocks) {
      for (uint32_t i = 0; i < N; i++) {
        for (uint8_t c = 0; c < cfg::kChannels; c++) {
          frames[i].ch[c] = stamp(frame_index + i, c);
        }
      }
      rec.pushFrames(frames.data(), N);
      frame_index += N;
      out.pushed += N;
      delivered++;
      next_capture_us += block_us;
    }

    // One turn of the main loop. A turn that writes nothing still costs a
    // little time, or the clock would never advance and capture would never
    // come due again.
    const uint64_t before = qpr_host::g_micros;
    rec.service();
    if (qpr_host::g_micros == before) qpr_host::advanceMicros(20);
  }

  // Let the loop drain, as it would after the user stops pushing.
  for (int i = 0; i < 256; i++) rec.service();

  out.recorded = rec.framesRecorded();
  out.dropped = rec.framesDropped();
  out.overruns = rec.overrunCount();
  out.peak_use = rec.peakBufferUse();
  rec.stop();
  return out;
}

static void checkTake(const RunResult& r, const char* label,
                      bool expect_overrun) {
  printf("\n%s\n", label);
  printf("  pushed %llu, recorded %llu, dropped %llu, overruns %lu, "
         "peak buffer %.0f%%\n",
         (unsigned long long)r.pushed, (unsigned long long)r.recorded,
         (unsigned long long)r.dropped, (unsigned long)r.overruns,
         (double)(r.peak_use * 100.0f));

  char buf[160];
  snprintf(buf, sizeof(buf), "recorded %llu + dropped %llu == pushed %llu",
           (unsigned long long)r.recorded, (unsigned long long)r.dropped,
           (unsigned long long)r.pushed);
  check(r.recorded + r.dropped == r.pushed, "frame accounting closes", buf);

  if (expect_overrun) {
    check(r.overruns > 0, "the stall did overrun, as intended");
  } else {
    check(r.overruns == 0, "no overrun");
  }

  FileCheck fc[cfg::kChannels];
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    char name[32];
    snprintf(name, sizeof(name), "%s/%s%03lu.WAV", hostsd::root().c_str(),
             cfg::kChannelNames[c], (unsigned long)r.take);
    fc[c] = readAndCheck(name, c);
  }

  bool all_open = true, all_ch_ok = true, all_mono = true;
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    all_open &= fc[c].opened;
    all_ch_ok &= fc[c].channel_ok;
    all_mono &= fc[c].monotonic;
  }
  check(all_open, "all four files exist");
  check(all_ch_ok, "every sample landed in the right channel's file");
  check(all_mono, "frame numbering never goes backwards");

  bool equal_len = true;
  for (uint8_t c = 1; c < cfg::kChannels; c++) {
    if (fc[c].frames != fc[0].frames) equal_len = false;
  }
  snprintf(buf, sizeof(buf), "FLU %llu, FRD %llu, BLD %llu, BRU %llu frames",
           (unsigned long long)fc[0].frames, (unsigned long long)fc[1].frames,
           (unsigned long long)fc[2].frames, (unsigned long long)fc[3].frames);
  check(equal_len, "all four files are exactly the same length", buf);

  // THE important one: identical frame tags at identical offsets. This is
  // what a per-channel overrun would break, and it is invisible by ear.
  bool aligned = equal_len;
  uint64_t first_mismatch = 0;
  if (aligned) {
    for (uint64_t i = 0; i < fc[0].tags.size() && aligned; i++) {
      for (uint8_t c = 1; c < cfg::kChannels; c++) {
        if (fc[c].tags[i] != fc[0].tags[i]) {
          aligned = false;
          first_mismatch = i;
          break;
        }
      }
    }
  }
  if (aligned) {
    check(true, "all four channels are sample-aligned end to end");
  } else {
    snprintf(buf, sizeof(buf), "first divergence at sample %llu",
             (unsigned long long)first_mismatch);
    check(false, "all four channels are sample-aligned end to end", buf);
  }

  snprintf(buf, sizeof(buf), "%llu gap(s), %llu frames lost",
           (unsigned long long)fc[0].gaps, (unsigned long long)r.dropped);
  check(fc[0].frames + r.dropped == r.pushed,
        "file length + reported loss == captured audio", buf);

  if (expect_overrun) {
    bool same_gaps = true;
    for (uint8_t c = 1; c < cfg::kChannels; c++) {
      if (fc[c].gaps != fc[0].gaps) same_gaps = false;
    }
    check(same_gaps, "every channel has the SAME gaps (collective overrun)");
  }
}

int main(int argc, char** argv) {
  const std::string dir = argc > 1 ? argv[1] : "/tmp/qpr_sd";
  hostsd::setRoot(dir);
  printf("host recorder test — Illicit Apothecary\n");
  printf("scratch dir  : %s\n", dir.c_str());
  printf("config       : %lu Hz, %u ch, %lu KiB ring, %lu KiB chunk, "
         "%.0f ms of slack\n",
         (unsigned long)cfg::kSampleRateHz, cfg::kChannels,
         (unsigned long)(cfg::kRingBytesPerChannel / 1024),
         (unsigned long)(cfg::kSdWriteChunkBytes / 1024),
         (double)(1000.0 * cfg::kRingBytesPerChannel /
                  (cfg::kSampleRateHz * 3.0)));

  Recorder rec;
  if (!rec.begin()) {
    printf("FAIL: recorder.begin() -> %s\n",
           Recorder::errorName(rec.lastError()));
    return 1;
  }

  // ~2 seconds of audio per case: enough for many write chunks.
  const uint32_t blocks = (uint32_t)(2.0 * cfg::kSampleRateHz /
                                     cfg::kDmaFramesPerHalf);
  if ((uint64_t)blocks * cfg::kDmaFramesPerHalf >= kMaxTaggedFrames) {
    printf("FAIL: test run is longer than the 20-bit frame tag can encode\n");
    return 1;
  }

  checkTake(runTake(rec, blocks, 0, 0),
            "case 1: clean run, healthy card", false);

  checkTake(runTake(rec, blocks, blocks / 2, 100000),
            "case 2: 100 ms stall — inside the 128 ms buffer", false);

  const RunResult r3 = runTake(rec, blocks, blocks / 2, 400000);
  checkTake(r3, "case 3: 400 ms stall — MUST overrun, collectively", true);
  const uint32_t r5_prev_take = r3.take;

  // Case 5: delete one file of the last take and confirm the next take does
  // not reuse that number.
  printf("\ncase 4: a half-written previous set must not be overwritten\n");
  // After stop(), lastTakeOnCard() must already reflect the take that just
  // finished -- the display relies on this to offer the right next number.
  const uint32_t last = rec.lastTakeOnCard();
  {
    char b2[96];
    snprintf(b2, sizeof(b2), "reports %03lu, last recorded was %03lu",
             (unsigned long)last, (unsigned long)r5_prev_take);
    check(last == r5_prev_take,
          "lastTakeOnCard() is fresh immediately after stop()", b2);
  }
  char victim[64];
  snprintf(victim, sizeof(victim), "%s%03lu.WAV", cfg::kChannelNames[3],
           (unsigned long)last);
  rec.volume()->remove(victim);
  printf("  removed %s, leaving takes %03lu incomplete\n", victim,
         (unsigned long)last);
  Recorder rec2;
  rec2.begin();
  check(rec2.lastTakeOnCard() == last,
        "the incomplete take still counts as used");
  const RunResult r5 = runTake(rec2, 16, 0, 0);
  char buf[96];
  snprintf(buf, sizeof(buf), "new take is %03lu, previous was %03lu",
           (unsigned long)r5.take, (unsigned long)last);
  check(r5.take == last + 1, "the next take gets a fresh number", buf);
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    char name[32];
    snprintf(name, sizeof(name), "%s/%s%03lu.WAV", hostsd::root().c_str(),
             cfg::kChannelNames[c], (unsigned long)last);
    FILE* f = fopen(name, "rb");
    if (c == 3) {
      check(f == nullptr, "the deleted file was not silently recreated");
    }
    if (f) fclose(f);
  }

  printf("\n%s (%d failure%s)\n", g_failures ? "FAILED" : "ALL PASSED",
         g_failures, g_failures == 1 ? "" : "s");
  return g_failures ? 1 : 0;
}
