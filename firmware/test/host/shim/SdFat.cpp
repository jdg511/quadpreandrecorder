// SdFat.cpp — host shim implementation
// Vendor: Illicit Apothecary

#include "SdFat.h"
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>

HostSerial Serial;
namespace qpr_host {
uint64_t g_micros = 0;
uint64_t g_cycles = 0;
}

namespace hostsd {
namespace {
std::string g_root = "/tmp/qpr_sd";
uint32_t g_write_cost_us = 300;      // a healthy card's typical 24 KiB write
uint32_t g_writes = 0;
uint32_t g_stall_at = 0xFFFFFFFF;
uint32_t g_stall_us = 0;
uint64_t g_free_bytes = 30ull * 1000ull * 1000ull * 1000ull;
}  // namespace

void setRoot(const std::string& dir) {
  g_root = dir;
  ::mkdir(dir.c_str(), 0777);
}
const std::string& root() { return g_root; }
void setWriteCost(uint32_t us) { g_write_cost_us = us; }
void injectStall(uint32_t after_writes, uint32_t stall_us) {
  g_stall_at = after_writes;
  g_stall_us = stall_us;
}
uint32_t writeCount() { return g_writes; }
void setFreeBytes(uint64_t b) { g_free_bytes = b; }
void reset() {
  g_writes = 0;
  g_stall_at = 0xFFFFFFFF;
  g_stall_us = 0;
  g_write_cost_us = 300;
}

uint32_t chargeWrite() {
  const uint32_t cost =
      (g_writes == g_stall_at) ? g_stall_us : g_write_cost_us;
  g_writes++;
  qpr_host::advanceMicros(cost);
  return cost;
}
uint64_t freeBytes() { return g_free_bytes; }
}  // namespace hostsd

static std::string joinPath(const char* name) {
  std::string n(name ? name : "");
  if (!n.empty() && n[0] == '/') n.erase(0, 1);
  return hostsd::root() + "/" + n;
}

bool FsFile::open(const char* name, oflag_t flags) {
  close();
  name_ = name ? name : "";

  if (name_ == "/" || name_.empty()) {
    // Directory handle, for openNext().
    is_dir_ = true;
    entries_.clear();
    next_entry_ = 0;
    if (DIR* d = ::opendir(hostsd::root().c_str())) {
      while (struct dirent* e = ::readdir(d)) {
        std::string n = e->d_name;
        if (n == "." || n == "..") continue;
        entries_.push_back(n);
      }
      ::closedir(d);
    }
    std::sort(entries_.begin(), entries_.end());
    return true;
  }

  const std::string path = joinPath(name);
  const char* mode;
  if (flags & O_TRUNC)       mode = "w+b";
  else if (flags & O_CREAT)  mode = "r+b";
  else if (flags & (O_RDWR | O_WRONLY)) mode = "r+b";
  else                        mode = "rb";

  fp_ = ::fopen(path.c_str(), mode);
  if (!fp_ && (flags & O_CREAT)) fp_ = ::fopen(path.c_str(), "w+b");
  return fp_ != nullptr;
}

bool FsFile::open(FsVolume*, const char* name, oflag_t flags) {
  return open(name, flags);
}

bool FsFile::openNext(FsFile* dir, oflag_t flags) {
  if (!dir || !dir->is_dir_) return false;
  if (dir->next_entry_ >= dir->entries_.size()) return false;
  const std::string n = dir->entries_[dir->next_entry_++];
  return open(n.c_str(), flags);
}

void FsFile::close() {
  if (fp_) { ::fclose(fp_); fp_ = nullptr; }
  is_dir_ = false;
  entries_.clear();
  next_entry_ = 0;
}

bool FsFile::preAllocate(uint64_t length) {
  if (!fp_) return false;
  // Real preallocation reserves contiguous clusters. Here we only need the
  // API to succeed or fail; the recorder truncates to the real length anyway.
  const long here = ::ftell(fp_);
  if (::fseek(fp_, 0, SEEK_END) != 0) return false;
  const long end = ::ftell(fp_);
  if ((uint64_t)end < length) {
    if (::fseek(fp_, (long)length - 1, SEEK_SET) != 0) return false;
    const char zero = 0;
    if (::fwrite(&zero, 1, 1, fp_) != 1) return false;
  }
  ::fseek(fp_, here, SEEK_SET);
  return true;
}

bool FsFile::truncate(uint64_t length) {
  if (!fp_) return false;
  ::fflush(fp_);
  const std::string path = joinPath(name_.c_str());
  return ::truncate(path.c_str(), (off_t)length) == 0;
}

bool FsFile::seek(uint64_t pos) {
  if (!fp_) return false;
  return ::fseek(fp_, (long)pos, SEEK_SET) == 0;
}

uint64_t FsFile::curPosition() {
  if (!fp_) return 0;
  return (uint64_t)::ftell(fp_);
}

size_t FsFile::write(const void* buf, size_t count) {
  if (!fp_) return 0;
  hostsd::chargeWrite();
  return ::fwrite(buf, 1, count, fp_);
}

int FsFile::read(void* buf, size_t count) {
  if (!fp_) return -1;
  return (int)::fread(buf, 1, count, fp_);
}

void FsFile::sync() { if (fp_) ::fflush(fp_); }

size_t FsFile::getName(char* out, size_t len) {
  if (!out || len == 0) return 0;
  strncpy(out, name_.c_str(), len - 1);
  out[len - 1] = 0;
  return strlen(out);
}

uint32_t FsVolume::freeClusterCount() {
  // Charged like a real allocation-bitmap walk, which is exactly why the
  // recorder caches this and never calls it during a take.
  qpr_host::advanceMicros(25000);
  return (uint32_t)(hostsd::freeBytes() / bytesPerCluster());
}

bool FsVolume::remove(const char* name) {
  return ::remove(joinPath(name).c_str()) == 0;
}

bool SdFs::begin(SdioConfig) {
  ::mkdir(hostsd::root().c_str(), 0777);
  return true;
}
