// qpr_pcm1864.h — TI PCM1864 four-channel ADC driver over I2C
//
// Vendor: Illicit Apothecary
//
// Register values in this driver come from TI SLAS831D (the cached copy in
// hardware/datasheets/). Section references are in the .cpp.
//
// Board wiring this driver assumes (verified against the routed netlist):
//   U7.3  VINL1 = FLU  -> ADC1 Left   -> DOUT  (Teensy pin 8), left  slot
//   U7.4  VINR1 = FRD  -> ADC1 Right  -> DOUT  (Teensy pin 8), right slot
//   U7.1  VINL2 = BLD  -> ADC2 Left   -> DOUT2 (Teensy pin 6), left  slot
//   U7.2  VINR2 = BRU  -> ADC2 Right  -> DOUT2 (Teensy pin 6), right slot
//   U7.25 MS/AD = GND  -> I2C address 0x4A
//   U7.26 MD0   = GND  -> I2C control mode (not SPI)
//   U7.22 GPIO0        -> retasked as DOUT2

#pragma once
#include <Arduino.h>
#include <stdint.h>

namespace qpr {

class Pcm1864 {
 public:
  enum class Format : uint8_t {
    // Two data lines, plain I2S, 2 channels each. 64 BCK per frame.
    // This is the only way to get four channels at 192 kHz out of this part.
    DualI2S = 0,
    // Single data line, 4-channel TDM. Fixed 256 BCK per frame, so this
    // tops out at 96 kHz on a Teensy 4.1.
    Tdm4Ch = 1,
  };

  enum class Status : uint8_t {
    Ok = 0,
    NoAck,            // device did not acknowledge its address
    WriteFailed,
    ReadbackMismatch, // wrote a register, read it back, got something else
    ClockError,       // device reports SCK/BCK/LRCK error or halt
    NotRunning,       // device never reached the RUN state
  };

  static const char* statusName(Status s);

  // Probes the part, resets it, and applies the full configuration.
  // Call after Wire.begin(). Does not start clocks -- the SAI driver does
  // that; this call is safe to make before or after clocks are running, but
  // waitUntilRunning() will only succeed once clocks are present.
  Status begin(Format fmt, bool enableHighPass = true);

  // Blocks until the device reports STATE == RUN (0xF) or the timeout expires.
  // Clocks must already be running. Returns ClockError with a decoded reason
  // in lastClockError() if the part is stuck in the clock-waiting state.
  Status waitUntilRunning(uint32_t timeout_ms = 250);

  // Sets all four channels to the same gain. Uses the part's LINK bit so the
  // hardware applies one value to all four PGAs simultaneously -- four
  // separate I2C writes would start their smoothing ramps microseconds apart.
  // Returns the gain actually applied after quantising to 0.5 dB steps.
  // If the I2C write fails the previous gain is kept and lastGainStatus()
  // reports why.
  float setGainDb(float gain_db);
  float gainDb() const { return gain_db_; }
  Status lastGainStatus() const { return last_gain_status_; }

  Status setMuted(bool muted);

  // Raw register access, mostly for the bring-up tests.
  Status writeReg(uint8_t page, uint8_t reg, uint8_t value);
  Status readReg(uint8_t page, uint8_t reg, uint8_t* out);

  // Snapshot of the two clock-status registers, decoded.
  struct ClockStatus {
    bool sck_error, bck_error, lrck_error;
    bool sck_halt,  bck_halt,  lrck_halt;
    uint8_t sck_ratio_code;   // register 0x74 bits 2:0
    uint8_t bck_ratio_code;   // register 0x74 bits 6:4
    uint8_t state;            // register 0x72 bits 3:0, 0xF == RUN
    bool ok() const {
      return !sck_error && !bck_error && !lrck_error &&
             !sck_halt && !bck_halt && !lrck_halt;
    }
  };
  Status readClockStatus(ClockStatus* out);
  static const char* stateName(uint8_t state);
  static const char* sckRatioName(uint8_t code);
  static const char* bckRatioName(uint8_t code);

 private:
  Status selectPage(uint8_t page);
  Status writeVerified(uint8_t reg, uint8_t value);

  uint8_t current_page_ = 0xFF;
  float   gain_db_ = 0.0f;
  Status  last_gain_status_ = Status::Ok;
  Format  format_ = Format::DualI2S;
};

}  // namespace qpr
