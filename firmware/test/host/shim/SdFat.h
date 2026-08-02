// SdFat.h — host shim backed by ordinary files
//
// Vendor: Illicit Apothecary
//
// Implements exactly the SdFat 2.x surface that qpr_recorder.cpp and
// qpr_dsp.cpp use, backed by stdio in a scratch directory. That lets the real
// recorder run natively and produce real WAV files that can be validated with
// ffprobe and decoded in Python.
//
// It also models the one thing that actually breaks recorders in the field:
// WRITE STALLS. hostsd::setStall() makes the next write consume a chosen
// number of virtual microseconds, so a test can reproduce a card pausing for
// 200 ms and check what the firmware does about it.

#pragma once
#include <Arduino.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>

#define O_RDONLY 0x01
#define O_WRONLY 0x02
#define O_RDWR   0x04
#define O_CREAT  0x08
#define O_TRUNC  0x10

typedef int oflag_t;

namespace hostsd {
// Directory every shim file lives in. Set before SdFs::begin().
void setRoot(const std::string& dir);
const std::string& root();

// Microseconds of virtual time the NEXT n writes should each cost.
// A real card's typical write is a few hundred microseconds; a stall is tens
// or hundreds of milliseconds.
void setWriteCost(uint32_t normal_us);
void injectStall(uint32_t after_writes, uint32_t stall_us);
uint32_t writeCount();
void reset();
// Simulated free space, in bytes.
void setFreeBytes(uint64_t bytes);
}  // namespace hostsd

class FsVolume;

class FsFile {
 public:
  FsFile() = default;
  ~FsFile() { close(); }
  FsFile(const FsFile&) = delete;
  FsFile& operator=(const FsFile&) = delete;

  bool open(const char* name, oflag_t flags = O_RDONLY);
  bool open(FsVolume* vol, const char* name, oflag_t flags);
  bool openNext(FsFile* dir, oflag_t flags = O_RDONLY);
  void close();
  bool isOpen() const { return fp_ != nullptr || is_dir_; }

  bool preAllocate(uint64_t length);
  bool truncate(uint64_t length);
  bool seek(uint64_t pos);
  uint64_t curPosition();
  size_t write(const void* buf, size_t count);
  int read(void* buf, size_t count);
  void sync();
  size_t getName(char* out, size_t len);

 private:
  FILE* fp_ = nullptr;
  std::string name_;
  // Directory iteration state for openNext().
  bool is_dir_ = false;
  std::vector<std::string> entries_;
  size_t next_entry_ = 0;
};

class SdCardStub {
 public:
  uint64_t sectorCount() const { return 62500000ull; }  // ~32 GB
};

#define FAT_TYPE_EXFAT 64

class SdioConfig {
 public:
  SdioConfig() = default;
  explicit SdioConfig(int) {}
};
#define FIFO_SDIO 1
#define DMA_SDIO  2

class FsVolume {
 public:
  uint32_t freeClusterCount();
  uint32_t bytesPerCluster() const { return 32768; }
  int fatType() const { return FAT_TYPE_EXFAT; }
  SdCardStub* card() { return &card_; }
  bool remove(const char* name);

 protected:
  SdCardStub card_;
};

class SdFs : public FsVolume {
 public:
  bool begin(SdioConfig = SdioConfig());
};
