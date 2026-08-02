// qpr_recorder.cpp — four simultaneous mono WAV streams to microSD
// Vendor: Illicit Apothecary

#include "qpr_recorder.h"
#include <string.h>

namespace qpr {
namespace {

constexpr uint32_t kRingBytes = cfg::kRingBytesPerChannel;

// The rings live in OCRAM. They are only ever touched by the CPU (the audio
// DMA writes elsewhere), so no cache maintenance is needed on them.
DMAMEM uint8_t g_rings[cfg::kChannels][kRingBytes];

inline void put32le(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
  p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}
inline void put64le(uint8_t* p, uint64_t v) {
  put32le(p, (uint32_t)v); put32le(p + 4, (uint32_t)(v >> 32));
}
inline void put16le(uint8_t* p, uint16_t v) {
  p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}
inline void putTag(uint8_t* p, const char* t) { memcpy(p, t, 4); }

// Staging buffer for one SD write. Sits in OCRAM; SdFat's SDIO path is happy
// with either RAM, and keeping it out of DTCM leaves the stack alone.
DMAMEM __attribute__((aligned(32))) uint8_t g_write_buf[cfg::kSdWriteChunkBytes];

// Header layout, all offsets in bytes from the start of the file:
//   0   'RIFF' <riffSize> 'WAVE'                         12
//   12  'JUNK' 28 <reserved for ds64>                    36
//   48  'fmt ' 16 <PCM 24-bit mono>                      24
//   72  'JUNK' 424 <padding>                            432
//   504 'data' <dataSize>                                 8
//   512 audio
constexpr uint32_t kOffDs64  = 12;
constexpr uint32_t kOffFmt   = 48;
constexpr uint32_t kOffPad   = 72;
constexpr uint32_t kOffData  = 504;
static_assert(cfg::kWavHeaderBytes == 512, "header layout assumes 512 bytes");

}  // namespace

const char* Recorder::errorName(Error e) {
  switch (e) {
    case Error::None:              return "ok";
    case Error::NoCard:            return "no SD card / mount failed";
    case Error::ScanFailed:        return "could not read the card root directory";
    case Error::CreateFailed:      return "could not create a WAV file";
    case Error::PreallocateFailed: return "could not preallocate file space";
    case Error::WriteFailed:       return "SD write failed";
    case Error::Overrun:           return "buffer overrun -- card too slow";
  }
  return "?";
}

bool Recorder::begin() {
  for (uint8_t c = 0; c < cfg::kChannels; c++) ring_[c] = g_rings[c];

  // FIFO_SDIO is SdFat's fastest reliable mode on the Teensy 4.1's native
  // 4-bit SDIO port. DMA_SDIO is faster still but interacts badly with other
  // DMA-heavy code; capture DMA has priority here.
  if (!sd_.begin(SdioConfig(FIFO_SDIO))) {
    mounted_ = false;
    last_error_ = Error::NoCard;
    return false;
  }
  mounted_ = true;
  last_error_ = Error::None;
  return scanExistingTakes();
}

bool Recorder::scanExistingTakes() {
  last_take_ = 0;
  FsFile root;
  if (!root.open("/")) { last_error_ = Error::ScanFailed; return false; }

  char name[64];
  FsFile entry;
  while (entry.openNext(&root, O_RDONLY)) {
    entry.getName(name, sizeof(name));
    entry.close();
    // Compare all four prefixes. A take counts as "used" if ANY of the four
    // files exists, which is what stops a partial set being overwritten.
    for (uint8_t c = 0; c < cfg::kChannels; c++) {
      const char* pre = cfg::kChannelNames[c];
      if (strncasecmp(name, pre, 3) != 0) continue;
      const char* p = name + 3;
      uint32_t n = 0;
      uint8_t digits = 0;
      while (*p >= '0' && *p <= '9') { n = n * 10 + (uint32_t)(*p - '0'); p++; digits++; }
      if (digits == 0) continue;
      if (strcasecmp(p, ".WAV") != 0) continue;
      if (n > last_take_) last_take_ = n;
    }
  }
  root.close();
  return true;
}

void Recorder::writeHeader(FsFile& f, uint64_t data_bytes, bool final_write) {
  uint8_t hdr[cfg::kWavHeaderBytes];
  memset(hdr, 0, sizeof(hdr));

  const bool rf64 = data_bytes > cfg::kWavRiffLimitBytes;
  const uint64_t riff_bytes = data_bytes + cfg::kWavHeaderBytes - 8;

  // --- RIFF / RF64 ---------------------------------------------------------
  putTag(hdr + 0, rf64 ? "RF64" : "RIFF");
  put32le(hdr + 4, rf64 ? 0xFFFFFFFFu : (uint32_t)riff_bytes);
  putTag(hdr + 8, "WAVE");

  // --- ds64 (or JUNK placeholder) -----------------------------------------
  putTag(hdr + kOffDs64, rf64 ? "ds64" : "JUNK");
  put32le(hdr + kOffDs64 + 4, 28);
  put64le(hdr + kOffDs64 + 8,  riff_bytes);                  // riffSize
  put64le(hdr + kOffDs64 + 16, data_bytes);                  // dataSize
  put64le(hdr + kOffDs64 + 24, data_bytes / 3);              // sampleCount
  put32le(hdr + kOffDs64 + 32, 0);                           // table length

  // --- fmt  ----------------------------------------------------------------
  putTag(hdr + kOffFmt, "fmt ");
  put32le(hdr + kOffFmt + 4, 16);
  put16le(hdr + kOffFmt + 8,  1);                            // PCM
  put16le(hdr + kOffFmt + 10, 1);                            // mono
  put32le(hdr + kOffFmt + 12, cfg::kSampleRateHz);
  put32le(hdr + kOffFmt + 16, cfg::kSampleRateHz * 3);       // byte rate
  put16le(hdr + kOffFmt + 20, 3);                            // block align
  put16le(hdr + kOffFmt + 22, 24);                           // bits per sample

  // --- padding so audio starts at 512 --------------------------------------
  putTag(hdr + kOffPad, "JUNK");
  put32le(hdr + kOffPad + 4, kOffData - (kOffPad + 8));

  // --- data ----------------------------------------------------------------
  putTag(hdr + kOffData, "data");
  put32le(hdr + kOffData + 4, rf64 ? 0xFFFFFFFFu : (uint32_t)data_bytes);

  const uint64_t restore = final_write ? 0 : f.curPosition();
  f.seek(0);
  if (f.write(hdr, sizeof(hdr)) != sizeof(hdr)) {
    last_error_ = Error::WriteFailed;   // a bad header means an unplayable file
  }
  if (!final_write) f.seek(restore);
}

bool Recorder::openFiles(uint32_t take) {
  char name[16];
  const uint64_t prealloc =
      (uint64_t)cfg::kSampleRateHz * 3ull * cfg::kPreallocateSeconds +
      cfg::kWavHeaderBytes;

  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    snprintf(name, sizeof(name), "%s%03lu.WAV", cfg::kChannelNames[c],
             (unsigned long)take);
    if (!file_[c].open(name, O_RDWR | O_CREAT | O_TRUNC)) {
      last_error_ = Error::CreateFailed;
      return false;
    }
    // Contiguous preallocation keeps the FAT out of the write path. If the
    // card cannot do it we carry on -- it will just be slower and riskier.
    if (!file_[c].preAllocate(prealloc)) {
      // Not fatal: the take still runs, just with the FAT in the write path.
      // Recorded separately so it cannot mask a real error later.
      prealloc_ok_ = false;
    }
    data_bytes_[c] = 0;
    writeHeader(file_[c], 0, false);
    file_[c].seek(cfg::kWavHeaderBytes);
  }
  return true;
}

bool Recorder::start() {
  if (recording_) return true;
  if (!mounted_ && !begin()) return false;

  scanExistingTakes();
  take_ = last_take_ + 1;

  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    head_[c] = 0;
    tail_[c] = 0;
  }
  frames_written_ = 0;
  frames_dropped_ = 0;
  overruns_ = 0;
  overrun_flag_ = false;
  prealloc_ok_ = true;
  peak_use_ = 0.0f;
  max_write_us_ = 0;
  last_error_ = Error::None;

  // Measure free space BEFORE preallocating, and force a real scan rather
  // than accepting the cache -- otherwise the figure is short by the whole
  // preallocation (4 x ~2 GB) and the remaining-time readout is nonsense.
  invalidateFreeSpace();
  free_at_start_ = freeSpaceBytes();

  if (!openFiles(take_)) {
    for (uint8_t c = 0; c < cfg::kChannels; c++) file_[c].close();
    return false;
  }
  last_header_ms_ = millis();
  recording_ = true;   // set last: the ISR starts filling rings the moment
                       // this is true
  return true;
}

void Recorder::stop() {
  if (!recording_) return;
  recording_ = false;   // ISR stops producing immediately

  // Drain whatever is left, in whole samples.
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    for (;;) {
      uint32_t head = head_[c];
      uint32_t tail = tail_[c];
      uint32_t avail = (head >= tail) ? (head - tail) : (kRingBytes - tail + head);
      avail -= avail % 3;
      if (avail == 0) break;
      uint32_t n = avail > cfg::kSdWriteChunkBytes ? cfg::kSdWriteChunkBytes : avail;
      uint32_t first = kRingBytes - tail;
      if (first > n) first = n;
      memcpy(g_write_buf, ring_[c] + tail, first);
      if (n > first) memcpy(g_write_buf + first, ring_[c], n - first);
      if (file_[c].write(g_write_buf, n) != (size_t)n) {
        last_error_ = Error::WriteFailed;
        break;
      }
      data_bytes_[c] += n;
      tail_[c] = (tail + n) % kRingBytes;
    }
    file_[c].truncate(cfg::kWavHeaderBytes + data_bytes_[c]);
    writeHeader(file_[c], data_bytes_[c], true);
    file_[c].sync();
    file_[c].close();
  }
  // The take we just finished is now the highest one on the card. Without
  // this, lastTakeOnCard() keeps reporting the value from before the take and
  // the display offers an already-used number as "next" until something else
  // triggers a rescan.
  if (take_ > last_take_) last_take_ = take_;
  invalidateFreeSpace();
}

void Recorder::pushFrames(const Frame4* frames, uint32_t count) {
  if (!recording_) return;

  const uint32_t need = count * 3;

  // Admission is COLLECTIVE. The four rings do not drain evenly -- service()
  // deliberately empties the fullest channel first -- so their occupancies can
  // differ by a whole write chunk. Deciding per channel would let one channel
  // keep a block that the other three had to drop, which permanently
  // time-shifts that file against the others and quietly invalidates the
  // A-format-to-B-format decode for the rest of the take.
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    const uint32_t head = head_[c];
    const uint32_t tail = tail_[c];
    // Keep one byte free so head == tail always means "empty".
    const uint32_t free_bytes =
        (head >= tail) ? (kRingBytes - head + tail) : (tail - head);
    if (free_bytes <= need) {
      overruns_++;
      overrun_flag_ = true;
      frames_dropped_ += count;   // all four files lose the same block
      return;
    }
  }

  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    uint32_t head = head_[c];
    uint8_t* ring = ring_[c];
    for (uint32_t i = 0; i < count; i++) {
      const int32_t s = frames[i].ch[c];
      ring[head] = (uint8_t)s;
      if (++head == kRingBytes) head = 0;
      ring[head] = (uint8_t)(s >> 8);
      if (++head == kRingBytes) head = 0;
      ring[head] = (uint8_t)(s >> 16);
      if (++head == kRingBytes) head = 0;
    }
    head_[c] = head;
  }
  frames_written_ += count;
}

// 64-bit counters are updated in the capture interrupt and read here as two
// 32-bit loads, so they need a critical section to avoid a torn value.
uint64_t Recorder::framesRecorded() const {
  __disable_irq();
  const uint64_t v = frames_written_;
  __enable_irq();
  return v;
}

uint64_t Recorder::framesDropped() const {
  __disable_irq();
  const uint64_t v = frames_dropped_;
  __enable_irq();
  return v;
}

bool Recorder::writeChunk(uint8_t c) {
  const uint32_t head = head_[c];
  const uint32_t tail = tail_[c];
  const uint32_t avail =
      (head >= tail) ? (head - tail) : (kRingBytes - tail + head);
  if (avail < cfg::kSdWriteChunkBytes) return false;

  const uint32_t n = cfg::kSdWriteChunkBytes;
  uint32_t first = kRingBytes - tail;
  if (first > n) first = n;
  memcpy(g_write_buf, ring_[c] + tail, first);
  if (n > first) memcpy(g_write_buf + first, ring_[c], n - first);

  const uint32_t t0 = micros();
  const size_t written = file_[c].write(g_write_buf, n);
  const uint32_t dt = micros() - t0;
  if (dt > max_write_us_) max_write_us_ = dt;

  if (written != (size_t)n) { last_error_ = Error::WriteFailed; return false; }
  data_bytes_[c] += n;
  tail_[c] = (tail + n) % kRingBytes;
  return true;
}

void Recorder::service() {
  if (!recording_) return;

  // The capture interrupt only sets a flag; promoting it to last_error_ here
  // means an SD write failure and an overrun cannot clobber each other.
  if (overrun_flag_) {
    overrun_flag_ = false;
    if (last_error_ == Error::None) last_error_ = Error::Overrun;
  }

  // Track the fullest ring so the UI can show how much margin the card has.
  uint32_t worst = 0;
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    const uint32_t head = head_[c], tail = tail_[c];
    const uint32_t used = (head >= tail) ? (head - tail) : (kRingBytes - tail + head);
    if (used > worst) worst = used;
  }
  const float use = (float)worst / (float)kRingBytes;
  if (use > peak_use_) peak_use_ = use;

  // Always drain the fullest channel first, so one lagging file cannot push
  // another into overrun.
  for (uint8_t pass = 0; pass < cfg::kChannels; pass++) {
    uint8_t best = 0;
    uint32_t best_used = 0;
    for (uint8_t c = 0; c < cfg::kChannels; c++) {
      const uint32_t head = head_[c], tail = tail_[c];
      const uint32_t used = (head >= tail) ? (head - tail) : (kRingBytes - tail + head);
      if (used > best_used) { best_used = used; best = c; }
    }
    if (best_used < cfg::kSdWriteChunkBytes) break;
    if (!writeChunk(best)) break;
  }

  // Periodically refresh the in-progress sizes so a file left behind by a
  // power cut is still playable up to the last refresh.
  if (millis() - last_header_ms_ >= cfg::kHeaderRefreshMs) {
    last_header_ms_ = millis();
    for (uint8_t c = 0; c < cfg::kChannels; c++) {
      writeHeader(file_[c], data_bytes_[c], false);
      file_[c].sync();
    }
  }
}

uint64_t Recorder::freeSpaceBytes() {
  if (!mounted_) return 0;

  if (recording_) {
    // Never scan the allocation bitmap mid-take: on a large exFAT card that
    // walk can block for tens of milliseconds, which is a third of the ring
    // buffer's whole slack budget. Extrapolate instead.
    const uint64_t used = data_bytes_[0] + data_bytes_[1] +
                          data_bytes_[2] + data_bytes_[3];
    return used >= free_at_start_ ? 0 : (free_at_start_ - used);
  }

  const uint32_t now = millis();
  if (free_cache_ms_ != 0 && (now - free_cache_ms_) < kFreeCacheMs) {
    return free_cache_bytes_;
  }
  free_cache_bytes_ = (uint64_t)sd_.freeClusterCount() *
                      (uint64_t)sd_.bytesPerCluster();
  free_cache_ms_ = now ? now : 1;
  return free_cache_bytes_;
}

float Recorder::remainingSeconds() {
  const uint64_t bytes_per_sec = (uint64_t)cfg::kSampleRateHz * 3ull * cfg::kChannels;
  return (float)freeSpaceBytes() / (float)bytes_per_sec;
}

}  // namespace qpr
