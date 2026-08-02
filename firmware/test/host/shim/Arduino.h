// Arduino.h — minimal host shim
//
// Vendor: Illicit Apothecary
//
// This exists so the REAL firmware source files compile and run on a desktop.
// Nothing here is a reimplementation of firmware logic: qpr_dsp.cpp,
// qpr_recorder.cpp and qpr_coeffs.cpp are compiled unmodified against this
// header, so the host tests exercise the same code the Teensy runs.
//
// What it can and cannot stand in for:
//   CAN   -- millis/micros, memory attributes, interrupt-disable pairs,
//            the cycle counter, printf-style output.
//   CANNOT -- SAI registers, eDMA, I2C, real interrupt preemption, real
//            timing. Those are hardware and only the board can prove them.
//
// The virtual clock is deliberately manual: tests advance it explicitly so a
// run is deterministic and reproducible rather than depending on how fast the
// machine happens to be.

#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

// ---- memory placement attributes: no-ops on a host -------------------------
#define DMAMEM
#define FLASHMEM
#define PROGMEM

// ---- interrupt control -----------------------------------------------------
// The host tests are single-threaded and call the "ISR" functions directly, so
// these are genuinely no-ops rather than a simplification that hides anything.
// Test 3 covers the interleaving that matters by driving the producer and
// consumer in an explicit, adversarial order.
inline void __disable_irq() {}
inline void __enable_irq() {}

// ---- virtual clock ---------------------------------------------------------
namespace qpr_host {
extern uint64_t g_micros;
extern uint64_t g_cycles;
constexpr uint32_t kCpuHz = 600000000u;
// Advance the virtual clock. Tests call this instead of sleeping.
inline void advanceMicros(uint64_t us) {
  g_micros += us;
  g_cycles += us * (kCpuHz / 1000000u);
}
}  // namespace qpr_host

inline uint32_t millis() { return (uint32_t)(qpr_host::g_micros / 1000ull); }
inline uint32_t micros() { return (uint32_t)qpr_host::g_micros; }
inline void delay(uint32_t ms) { qpr_host::advanceMicros((uint64_t)ms * 1000ull); }
inline void delayMicroseconds(uint32_t us) { qpr_host::advanceMicros(us); }

#define F_CPU_ACTUAL (qpr_host::kCpuHz)
#define ARM_DWT_CYCCNT ((uint32_t)qpr_host::g_cycles)

// ---- GPIO ------------------------------------------------------------------
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWriteFast(uint8_t, uint8_t) {}
inline int  digitalReadFast(uint8_t) { return HIGH; }
inline void digitalWrite(uint8_t, uint8_t) {}
inline int  digitalRead(uint8_t) { return HIGH; }

// ---- Serial ----------------------------------------------------------------
#define F(x) (x)
struct HostSerial {
  void begin(uint32_t) {}
  operator bool() const { return true; }
  int  available() { return 0; }
  int  read() { return -1; }
  void print(const char* s) { fputs(s, stdout); }
  void println() { fputc('\n', stdout); }
  void println(const char* s) { fputs(s, stdout); fputc('\n', stdout); }
  template <typename... A> void printf(const char* f, A... a) {
    ::printf(f, a...);
  }
};
extern HostSerial Serial;

inline float tempmonGetTemp() { return 42.0f; }
