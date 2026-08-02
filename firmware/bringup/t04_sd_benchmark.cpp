// t04_sd_benchmark.cpp — bring-up test 4: can this microSD card keep up?
//
// Vendor: Illicit Apothecary
//
// THIS IS THE MOST IMPORTANT TEST IN THE SET. Everything else either works or
// obviously does not. A marginal SD card fails silently, in the middle of a
// take, months later.
//
// WHAT IT PROVES
//   The card sustains four simultaneous 192 kHz / 24-bit streams -- 2.304 MB/s
//   of file payload -- for as long as you let it run, WITHOUT a single write
//   stall longer than the firmware's buffer can absorb.
//
//   Average speed is not the number that matters. A card that averages
//   20 MB/s but pauses for 300 ms while it does internal garbage collection
//   will drop samples on a recorder with 128 ms of buffering. This test
//   reports the WORST single write it ever saw, and compares it to the real
//   buffer depth the firmware is built with.
//
// WHAT TO DO
//   Put the card you actually intend to record on into the slot. Flash this.
//   Let it run for LONGER THAN YOUR LONGEST INTENDED RECORDING. Ten minutes
//   tells you very little; an hour tells you something real. Cards get slower
//   as they fill, so run it on a card that is at least half full if that is
//   how you will use it.
//
// WHAT IT WRITES
//   Four files named BENCH0.TMP .. BENCH3.TMP, written exactly the way the
//   recorder writes: preallocated, 24576-byte block-aligned chunks, round
//   robin. It deletes them when you stop it with the 'q' key.
//
// HOW TO READ THE RESULT
//   PASS      worst write comfortably inside the buffer window
//   MARGINAL  worst write above half the buffer window -- it will probably
//             work, but a long take is a gamble. Use a better card, or raise
//             kRingChunksPerChannel in qpr_config.h and rebuild.
//   FAIL      worst write exceeded the buffer window. This card WILL drop
//             samples. Do not record on it.

#include <Arduino.h>
#include <SdFat.h>
#include "qpr_board.h"
#include "qpr_config.h"

using namespace qpr;

static SdFs sd;
static FsFile files[cfg::kChannels];
static DMAMEM __attribute__((aligned(32))) uint8_t buf[cfg::kSdWriteChunkBytes];

// Real numbers from the firmware's configuration, not guesses.
static constexpr uint32_t kBytesPerSecPerChannel = cfg::kSampleRateHz * 3u;
static constexpr float kBufferWindowMs =
    1000.0f * (float)cfg::kRingBytesPerChannel / (float)kBytesPerSecPerChannel;

static uint64_t total_bytes = 0;
static uint32_t writes = 0;
static uint32_t worst_us = 0;
static uint32_t worst_at_ms = 0;
static uint32_t hist[8] = { 0 };   // <1, <2, <5, <10, <20, <50, <100, >=100 ms
static uint32_t start_ms = 0;
static bool running = false;

static void bucket(uint32_t us) {
  const uint32_t ms = us / 1000;
  if (ms < 1)        hist[0]++;
  else if (ms < 2)   hist[1]++;
  else if (ms < 5)   hist[2]++;
  else if (ms < 10)  hist[3]++;
  else if (ms < 20)  hist[4]++;
  else if (ms < 50)  hist[5]++;
  else if (ms < 100) hist[6]++;
  else               hist[7]++;
}

static void cleanup() {
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    if (files[c].isOpen()) { files[c].close(); }
    char name[16];
    snprintf(name, sizeof(name), "BENCH%u.TMP", c);
    sd.remove(name);
  }
  Serial.println(F("\nTemporary files removed."));
}

static void report() {
  const float secs = (millis() - start_ms) / 1000.0f;
  const float mbps = (float)total_bytes / 1e6f / secs;
  const float need = (float)kBytesPerSecPerChannel * cfg::kChannels / 1e6f;

  Serial.println();
  Serial.printf("elapsed        %.0f s   (%.1f min)\n", (double)secs,
                (double)(secs / 60.0f));
  Serial.printf("written        %.2f GB in %lu chunks\n",
                (double)(total_bytes / 1e9), (unsigned long)writes);
  Serial.printf("sustained      %.2f MB/s   (need %.2f MB/s)   %s\n",
                (double)mbps, (double)need,
                mbps >= need * 1.05f ? "ok" : "TOO SLOW ON AVERAGE");
  Serial.printf("worst write    %.1f ms at t=%.0f s\n",
                (double)(worst_us / 1000.0f), (double)(worst_at_ms / 1000.0f));
  Serial.printf("buffer window  %.0f ms  (%lu KiB per channel)\n",
                (double)kBufferWindowMs,
                (unsigned long)(cfg::kRingBytesPerChannel / 1024));

  const char* labels[8] = { "<1ms", "1-2ms", "2-5ms", "5-10ms",
                            "10-20ms", "20-50ms", "50-100ms", ">100ms" };
  Serial.print(F("distribution  "));
  for (uint8_t i = 0; i < 8; i++) {
    if (hist[i]) Serial.printf(" %s:%lu", labels[i], (unsigned long)hist[i]);
  }
  Serial.println();

  const float worst_ms = worst_us / 1000.0f;
  Serial.print(F("VERDICT        "));
  if (mbps < need * 1.05f || worst_ms >= kBufferWindowMs) {
    Serial.println(F("FAIL -- this card will drop samples. Use a different card."));
  } else if (worst_ms >= kBufferWindowMs * 0.5f) {
    Serial.println(F("MARGINAL -- it fits, but with little room. Consider a"));
    Serial.println(F("               better card, or raise kRingChunksPerChannel."));
  } else {
    Serial.println(F("PASS -- comfortable margin."));
  }
  Serial.println(F("Press 'q' to stop and delete the temporary files."));
  Serial.println();
}

void setup() {
  board::configureControlPins();
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 4 of 6: SD CARD"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();
  Serial.printf("Target: %lu Hz x 24 bit x %u channels = %.3f MB/s\n",
                (unsigned long)cfg::kSampleRateHz, cfg::kChannels,
                (double)(kBytesPerSecPerChannel * cfg::kChannels / 1e6));
  Serial.printf("Firmware buffer depth: %.0f ms per channel\n\n",
                (double)kBufferWindowMs);

  if (!sd.begin(SdioConfig(FIFO_SDIO))) {
    Serial.println(F("CARD DID NOT MOUNT."));
    Serial.println(F("  - Is a card inserted, all the way in?"));
    Serial.println(F("  - Is it formatted exFAT (recommended) or FAT32?"));
    Serial.println(F("  - Teensy 4.1 uses its own microSD socket, not the"));
    Serial.println(F("    display module's. J3 pin 14 is a no-connect here."));
    while (true) { board::setRecordLed((millis() / 200) & 1); }
  }

  Serial.printf("Card mounted: %.1f GB, %s\n",
                (double)(sd.card()->sectorCount() * 512.0 / 1e9),
                sd.fatType() == FAT_TYPE_EXFAT ? "exFAT" : "FAT32");
  Serial.printf("Free space:   %.1f GB\n\n",
                (double)((uint64_t)sd.freeClusterCount() * sd.bytesPerCluster() / 1e9));

  // Fill the buffer with something incompressible, so a card that quietly
  // compresses runs of zeros cannot flatter itself.
  uint32_t seed = 0x1234567;
  for (uint32_t i = 0; i < sizeof(buf); i++) {
    seed = seed * 1664525u + 1013904223u;
    buf[i] = (uint8_t)(seed >> 16);
  }

  const uint64_t prealloc =
      (uint64_t)kBytesPerSecPerChannel * 600ull;   // 10 minutes per file
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    char name[16];
    snprintf(name, sizeof(name), "BENCH%u.TMP", c);
    sd.remove(name);
    if (!files[c].open(name, O_RDWR | O_CREAT | O_TRUNC)) {
      Serial.printf("Could not create %s\n", name);
      while (true) { }
    }
    if (!files[c].preAllocate(prealloc)) {
      Serial.printf("  ! %s could not be preallocated -- the card is nearly "
                    "full, or badly fragmented\n", name);
    }
  }
  Serial.println(F("Writing. Let this run for longer than your longest"));
  Serial.println(F("intended recording. Press 'q' to stop.\n"));

  start_ms = millis();
  running = true;
}

void loop() {
  if (!running) return;

  static uint8_t ch = 0;
  const uint32_t t0 = micros();
  const int n = files[ch].write(buf, sizeof(buf));
  const uint32_t dt = micros() - t0;

  if (n != (int)sizeof(buf)) {
    Serial.println(F("\nWRITE FAILED -- the card ran out of space or errored."));
    report();
    cleanup();
    running = false;
    return;
  }

  total_bytes += sizeof(buf);
  writes++;
  bucket(dt);
  if (dt > worst_us) {
    worst_us = dt;
    worst_at_ms = millis() - start_ms;
    if (dt > 20000) {
      Serial.printf("  ! %.1f ms stall at t=%.0f s\n", (double)(dt / 1000.0f),
                    (double)(worst_at_ms / 1000.0f));
    }
  }

  ch = (uint8_t)((ch + 1) % cfg::kChannels);

  // Rewind before the preallocated extent runs out, so the test can run for
  // hours on a small card and keeps hitting fresh flash blocks.
  if (files[ch].curPosition() > (uint64_t)kBytesPerSecPerChannel * 590ull) {
    for (uint8_t c = 0; c < cfg::kChannels; c++) files[c].seek(0);
  }

  static uint32_t last_report = 0;
  if (millis() - last_report >= 15000) {
    last_report = millis();
    report();
  }

  board::setRecordLed((millis() / 250) & 1);

  if (Serial.available() && Serial.read() == 'q') {
    Serial.println(F("\n=== FINAL RESULT ==="));
    report();
    cleanup();
    board::setRecordLed(false);
    running = false;
  }
}
