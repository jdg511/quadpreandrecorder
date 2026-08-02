// qpr_pcm1864.cpp — TI PCM1864 four-channel ADC driver
//
// Vendor: Illicit Apothecary
// Register map: TI SLAS831D section 13 (cached in hardware/datasheets/).

#include "qpr_pcm1864.h"
#include <Wire.h>
#include "qpr_board.h"

namespace qpr {
namespace {

// ---- Page 0 register addresses (SLAS831D Table 26) ------------------------
constexpr uint8_t REG_PAGE          = 0x00;
constexpr uint8_t REG_PGA_CH1_L     = 0x01;
constexpr uint8_t REG_PGA_CH1_R     = 0x02;
constexpr uint8_t REG_PGA_CH2_L     = 0x03;
constexpr uint8_t REG_PGA_CH2_R     = 0x04;
constexpr uint8_t REG_PGA_CTRL      = 0x05;  // SMOOTH | LINK | ... | AGC_EN
constexpr uint8_t REG_ADC1_SEL_L    = 0x06;
constexpr uint8_t REG_ADC1_SEL_R    = 0x07;
constexpr uint8_t REG_ADC2_SEL_L    = 0x08;
constexpr uint8_t REG_ADC2_SEL_R    = 0x09;
constexpr uint8_t REG_I2S_FMT       = 0x0B;  // RX_WLEN|TDM_LRCK_MODE|TX_WLEN|FMT
constexpr uint8_t REG_TDM_OSEL      = 0x0C;
constexpr uint8_t REG_TX_TDM_OFFSET = 0x0D;
constexpr uint8_t REG_GPIO01_FUNC   = 0x10;
constexpr uint8_t REG_GPIO01_DIR    = 0x12;
constexpr uint8_t REG_CLK_CFG       = 0x20;  // SCK_XI_SEL|...|MST_MODE|...|CLKDET_EN
constexpr uint8_t REG_POWER         = 0x70;
constexpr uint8_t REG_DSP_CTRL      = 0x71;  // 2CH|RSV|FLT|HPF_EN|MUTE x4
constexpr uint8_t REG_DEVICE_STATE  = 0x72;
constexpr uint8_t REG_CLK_RATIOS    = 0x74;
constexpr uint8_t REG_CLK_ERR       = 0x75;

constexpr uint8_t PAGE_RESET_VALUE  = 0xFE;  // writing this to 0x00 resets regs

// ---- Field values we use -------------------------------------------------
// 0x0B: RX_WLEN=00 (32-bit), TDM_LRCK_MODE=0 (50% duty), TX_WLEN=00 (32-bit),
//       FMT=00 (I2S). 32-bit TX means the part actively drives all 32 BCKs of
//       the slot instead of tri-stating after 24, which keeps the data line
//       from floating between the 33R damper and the Teensy input.
constexpr uint8_t FMT_I2S_32BIT = 0x00;
// 0x0B for TDM: RX_WLEN=00, TDM_LRCK_MODE=1 (1/256 duty, DSP-style frame
//       sync), TX_WLEN=00 (32-bit), FMT=11 (TDM/DSP).
constexpr uint8_t FMT_TDM_32BIT = 0x13;

// 0x0C TDM_OSEL:
//   00 = 2ch per line: DOUT1 = ch1 L/R, DOUT2 = ch2 L/R   <- DualI2S
//   01 = 4ch: DOUT1 = ch1 L, ch1 R, ch2 L, ch2 R          <- Tdm4Ch
constexpr uint8_t TDM_OSEL_2CH = 0x00;
constexpr uint8_t TDM_OSEL_4CH = 0x01;

// 0x10: GPIO1_POL=0, GPIO1_FUNC=000 (plain GPIO, unused/no-connect),
//       GPIO0_POL=0, GPIO0_FUNC=101 (DOUT2).
constexpr uint8_t GPIO0_AS_DOUT2 = 0x05;
// 0x10 with GPIO0 left at its reset function (digital mic input), for TDM mode
// where DOUT2 is not used.
constexpr uint8_t GPIO0_DEFAULT  = 0x01;

// 0x12: GPIO1_DIR=000, GPIO0_DIR=100 (output). Ignored while GPIO0_FUNC
//       selects a hard function, but harmless and explicit.
constexpr uint8_t GPIO0_DIR_OUT  = 0x04;

// 0x20: SCK_XI_SEL=01 (use the SCKI pin, not the crystal oscillator -- XI/XO
//       are no-connects on this board), MST_MODE=0 (slave: the Teensy is the
//       clock master), CLKDET_EN=1 (auto clock detection configures the
//       internal dividers and PLL from the measured SCK/BCK/LRCK ratios).
constexpr uint8_t CLK_CFG_SLAVE_SCKI = 0x41;

// 0x06..0x09 input select. Bit 6 is a reserved bit whose reset value is 1 on
// all four of these registers, so it is written back as 1 in every case.
constexpr uint8_t SEL_VIN1_SE = 0x41;  // VINL1 / VINR1 single-ended
constexpr uint8_t SEL_VIN2_SE = 0x42;  // VINL2 / VINR2 single-ended

// 0x05: SMOOTH=1 (ramp gain changes), LINK=1 (ch1R, ch2L, ch2R follow ch1L),
//       DPGA_CLIP_EN=0, MAX_ATT=00, START_ATT=11, AGC_EN=0.
//       AGC must stay off: automatic clipping suppression would break gain
//       matching between channels, which is the whole point of the array.
constexpr uint8_t PGA_CTRL_LINKED = 0xC6;

constexpr uint8_t STATE_RUN = 0x0F;

int8_t gainDbToRegister(float db) {
  // 7.1 two's complement: register value = round(db * 2).
  float steps = db * 2.0f;
  int32_t v = (int32_t)(steps >= 0 ? steps + 0.5f : steps - 0.5f);
  if (v < -24)  v = -24;   // -12.0 dB
  if (v >  80)  v =  80;   // +40.0 dB
  return (int8_t)v;
}

}  // namespace

const char* Pcm1864::statusName(Status s) {
  switch (s) {
    case Status::Ok:               return "ok";
    case Status::NoAck:            return "no I2C ack from 0x4A";
    case Status::WriteFailed:      return "I2C write failed";
    case Status::ReadbackMismatch: return "register readback mismatch";
    case Status::ClockError:       return "clock error / clock waiting state";
    case Status::NotRunning:       return "device did not reach RUN state";
  }
  return "?";
}

const char* Pcm1864::stateName(uint8_t state) {
  switch (state & 0x0F) {
    case 0x0: return "power down";
    case 0x1: return "wait clock stable";
    case 0x2: return "release reset";
    case 0x3: return "stand-by";
    case 0x4: return "fade in";
    case 0x5: return "fade out";
    case 0x9: return "sleep";
    case 0xF: return "RUN";
  }
  return "reserved";
}

const char* Pcm1864::sckRatioName(uint8_t code) {
  switch (code & 0x07) {
    case 0: return "out of range (low) or SCK halted";
    case 1: return "128 fs";
    case 2: return "256 fs";
    case 3: return "384 fs";
    case 4: return "512 fs";
    case 5: return "768 fs";
    case 6: return "out of range (high)";
    default: return "invalid ratio or LRCK halted";
  }
}

const char* Pcm1864::bckRatioName(uint8_t code) {
  switch (code & 0x07) {
    case 0: return "out of range (low) or BCK halted";
    case 1: return "32 fs";
    case 2: return "48 fs";
    case 3: return "64 fs";
    case 4: return "256 fs";
    case 5: return "not assigned";
    case 6: return "out of range (high)";
    default: return "invalid ratio or LRCK halted";
  }
}

Pcm1864::Status Pcm1864::selectPage(uint8_t page) {
  if (current_page_ == page) return Status::Ok;
  Wire.beginTransmission(board::PCM1864_I2C_ADDR);
  Wire.write(REG_PAGE);
  Wire.write(page);
  if (Wire.endTransmission() != 0) { current_page_ = 0xFF; return Status::NoAck; }
  current_page_ = page;
  return Status::Ok;
}

Pcm1864::Status Pcm1864::writeReg(uint8_t page, uint8_t reg, uint8_t value) {
  Status s = selectPage(page);
  if (s != Status::Ok) return s;
  Wire.beginTransmission(board::PCM1864_I2C_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0 ? Status::Ok : Status::WriteFailed;
}

Pcm1864::Status Pcm1864::readReg(uint8_t page, uint8_t reg, uint8_t* out) {
  Status s = selectPage(page);
  if (s != Status::Ok) return s;
  Wire.beginTransmission(board::PCM1864_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return Status::WriteFailed;
  if (Wire.requestFrom((uint8_t)board::PCM1864_I2C_ADDR, (uint8_t)1) != 1) return Status::NoAck;
  *out = (uint8_t)Wire.read();
  return Status::Ok;
}

Pcm1864::Status Pcm1864::writeVerified(uint8_t reg, uint8_t value) {
  Status s = writeReg(0, reg, value);
  if (s != Status::Ok) return s;
  uint8_t back = 0;
  s = readReg(0, reg, &back);
  if (s != Status::Ok) return s;
  // Registers with read-only or self-clearing bits are excluded by the caller;
  // everything we verify here is plain R/W.
  return (back == value) ? Status::Ok : Status::ReadbackMismatch;
}

Pcm1864::Status Pcm1864::begin(Format fmt, bool enableHighPass) {
  format_ = fmt;
  current_page_ = 0xFF;

  // Probe first so a dead part gives a clear error rather than a mismatch.
  Wire.beginTransmission(board::PCM1864_I2C_ADDR);
  if (Wire.endTransmission() != 0) return Status::NoAck;

  // Full register reset, then let the part settle.
  Wire.beginTransmission(board::PCM1864_I2C_ADDR);
  Wire.write(REG_PAGE);
  Wire.write(PAGE_RESET_VALUE);
  if (Wire.endTransmission() != 0) return Status::WriteFailed;
  delay(10);
  current_page_ = 0xFF;

  Status s;

  // Clock source and role. Do this before the format so the auto clock
  // detector is looking at the right pin from the start.
  if ((s = writeVerified(REG_CLK_CFG, CLK_CFG_SLAVE_SCKI)) != Status::Ok) return s;

  // Input routing: four single-ended inputs, no polarity inversion.
  if ((s = writeVerified(REG_ADC1_SEL_L, SEL_VIN1_SE)) != Status::Ok) return s;  // FLU
  if ((s = writeVerified(REG_ADC1_SEL_R, SEL_VIN1_SE)) != Status::Ok) return s;  // FRD
  if ((s = writeVerified(REG_ADC2_SEL_L, SEL_VIN2_SE)) != Status::Ok) return s;  // BLD
  if ((s = writeVerified(REG_ADC2_SEL_R, SEL_VIN2_SE)) != Status::Ok) return s;  // BRU

  // Serial audio format.
  if (fmt == Format::DualI2S) {
    if ((s = writeVerified(REG_I2S_FMT,       FMT_I2S_32BIT)) != Status::Ok) return s;
    if ((s = writeVerified(REG_TDM_OSEL,      TDM_OSEL_2CH))  != Status::Ok) return s;
    if ((s = writeVerified(REG_TX_TDM_OFFSET, 0))             != Status::Ok) return s;
    // Retask GPIO0 as the second data output.
    if ((s = writeVerified(REG_GPIO01_DIR,    GPIO0_DIR_OUT)) != Status::Ok) return s;
    if ((s = writeVerified(REG_GPIO01_FUNC,   GPIO0_AS_DOUT2))!= Status::Ok) return s;
  } else {
    if ((s = writeVerified(REG_I2S_FMT,       FMT_TDM_32BIT)) != Status::Ok) return s;
    if ((s = writeVerified(REG_TDM_OSEL,      TDM_OSEL_4CH))  != Status::Ok) return s;
    // 1 BCK offset puts the first slot one clock after the frame sync, which
    // is what the Teensy SAI generates with FSE (frame sync early) set.
    if ((s = writeVerified(REG_TX_TDM_OFFSET, 1))             != Status::Ok) return s;
    if ((s = writeVerified(REG_GPIO01_FUNC,   GPIO0_DEFAULT)) != Status::Ok) return s;
  }

  // Four-channel processing, optional DC-blocking high-pass, all channels
  // unmuted. Bit 7 (2CH) must be 0 for a four-channel device.
  uint8_t dsp_ctrl = enableHighPass ? 0x10 : 0x00;
  if ((s = writeVerified(REG_DSP_CTRL, dsp_ctrl)) != Status::Ok) return s;

  // Gain control: smooth ramps, all four PGAs linked to ch1 L, AGC off.
  if ((s = writeVerified(REG_PGA_CTRL, PGA_CTRL_LINKED)) != Status::Ok) return s;

  // The PGA smoothing ramp needs the internal DSPs clocked, which they are
  // not until the SAI starts. 0 dB is the reset value, so this is a no-op that
  // simply records the state; the application re-applies the real gain after
  // clocks are running.
  setGainDb(0.0f);
  return last_gain_status_;
}

float Pcm1864::setGainDb(float gain_db) {
  int8_t reg = gainDbToRegister(gain_db);
  // LINK=1 makes ch1R / ch2L / ch2R follow ch1L in hardware, so one write
  // moves all four PGAs on the same internal ramp.
  last_gain_status_ = writeReg(0, REG_PGA_CH1_L, (uint8_t)reg);
  if (last_gain_status_ == Status::Ok) gain_db_ = reg * 0.5f;
  return gain_db_;
}

Pcm1864::Status Pcm1864::setMuted(bool muted) {
  uint8_t v = 0;
  Status s = readReg(0, REG_DSP_CTRL, &v);
  if (s != Status::Ok) return s;
  v = muted ? (uint8_t)(v | 0x0F) : (uint8_t)(v & ~0x0F);
  return writeReg(0, REG_DSP_CTRL, v);
}

Pcm1864::Status Pcm1864::readClockStatus(ClockStatus* out) {
  uint8_t err = 0, ratios = 0, state = 0;
  Status s;
  if ((s = readReg(0, REG_CLK_ERR,      &err))    != Status::Ok) return s;
  if ((s = readReg(0, REG_CLK_RATIOS,   &ratios)) != Status::Ok) return s;
  if ((s = readReg(0, REG_DEVICE_STATE, &state))  != Status::Ok) return s;
  out->lrck_halt      = err & 0x40;
  out->bck_halt       = err & 0x20;
  out->sck_halt       = err & 0x10;
  out->lrck_error     = err & 0x04;
  out->bck_error      = err & 0x02;
  out->sck_error      = err & 0x01;
  out->bck_ratio_code = (ratios >> 4) & 0x07;
  out->sck_ratio_code = ratios & 0x07;
  out->state          = state & 0x0F;
  return Status::Ok;
}

Pcm1864::Status Pcm1864::waitUntilRunning(uint32_t timeout_ms) {
  uint32_t start = millis();
  ClockStatus cs{};
  for (;;) {
    Status s = readClockStatus(&cs);
    if (s != Status::Ok) return s;
    if (cs.state == STATE_RUN) return Status::Ok;
    if (millis() - start > timeout_ms) {
      return cs.ok() ? Status::NotRunning : Status::ClockError;
    }
    delay(2);
  }
}

}  // namespace qpr
