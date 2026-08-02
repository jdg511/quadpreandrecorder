// qpr_board.h — QuadPreRecorder Rev A board support
//
// Vendor: Illicit Apothecary
// Project: Quad Preamp and Recorder (four-channel ambisonic electret front end)
//
// EVERY pin number below was extracted from the routed KiCad netlist
// (hardware/review_outputs/QuadPreRecorder.net), not from documentation.
// If you respin the board, regenerate this file from the netlist -- do not
// edit it from memory.
//
// Teensy 4.1 fixed-peripheral facts this board relies on:
//   SAI1 (I2S1): MCLK1 = 23, BCLK1 = 21, LRCLK1 = 20,
//                RX_DATA0 = 8, RX_DATA1 = 6
//   SAI2 (I2S2): TX_DATA = 2, LRCLK2 = 3, BCLK2 = 4, MCLK2 = 33 (NOT USED HERE)
//   LPSPI4:      MOSI = 11, MISO = 12, SCK = 13
//   Wire (I2C0): SDA = 18, SCL = 19
//
// WARNING: Teensy pin 33 is SAI2_MCLK in hardware, but on this board it is
// wired to HP_ENABLE. The PCM5102A has SCK tied to ground and runs from its
// internal PLL, so SAI2 MCLK is never routed to a pad. Never set
// CORE_PIN33_CONFIG to the SAI2 alt function.

#pragma once
#include <Arduino.h>

namespace qpr {
namespace pins {

// ---- Serial audio: ADC (PCM1864, U7) on SAI1 -----------------------------
constexpr uint8_t ADC_MCLK  = 23;  // /ADC_MCLK  -> R46 33R -> U7.15 SCKI
constexpr uint8_t ADC_BCLK  = 21;  // /ADC_BCLK  -> R48 33R -> U7.17 BCK
constexpr uint8_t ADC_LRCLK = 20;  // /ADC_LRCLK -> R47 33R -> U7.16 LRCK
constexpr uint8_t ADC_DATA1 = 8;   // /ADC_TDM   <- R49 33R <- U7.18 DOUT  (ch1 L/R)
constexpr uint8_t ADC_DATA2 = 6;   // /ADC_DOUT2 <- R69 33R <- U7.22 GPIO0 (ch2 L/R)

// ---- Serial audio: DAC (PCM5102A, U9) on SAI2 ----------------------------
constexpr uint8_t DAC_DIN   = 2;   // /DAC_DIN   -> R58 33R -> U9.14 DIN
constexpr uint8_t DAC_LRCLK = 3;   // /DAC_LRCLK -> R59 33R -> U9.15 LRCK
constexpr uint8_t DAC_BCLK  = 4;   // /DAC_BCLK  -> R57 33R -> U9.13 BCK

// ---- Control ------------------------------------------------------------
constexpr uint8_t I2C_SDA   = 18;  // PCM1864 (0x4A) + FT6336G touch
constexpr uint8_t I2C_SCL   = 19;

constexpr uint8_t SPI_MOSI  = 11;
constexpr uint8_t SPI_MISO  = 12;
constexpr uint8_t SPI_SCK   = 13;

constexpr uint8_t TFT_CS    = 10;  // J3.3
constexpr uint8_t TFT_DC    = 9;   // J3.5
constexpr uint8_t TFT_RST   = 7;   // J3.4   (moved from pin 6 in the 192 kHz fix)
constexpr uint8_t TOUCH_RST = 5;   // J3.11  (FT6336G is I2C: this is RESET, not CS)
constexpr uint8_t TOUCH_IRQ = 22;  // J3.13

constexpr uint8_t REC_BUTTON = 28; // SW2 B3F-5150, active LOW, R50 10k pull-up + C47
constexpr uint8_t GAIN_A     = 29; // SW3 EC11 quadrature A, R51 10k pull-up + C48 10nF
constexpr uint8_t GAIN_B     = 30; // SW3 EC11 quadrature B, R52 10k pull-up + C49 10nF
constexpr uint8_t GAIN_PUSH  = 31; // SW3 push, active LOW, R53 10k pull-up + C50
constexpr uint8_t PAD_SENSE  = 32; // SW1 via R42 100k / R43 47k divider: 0 V or 2.88 V
constexpr uint8_t HP_ENABLE  = 33; // TPA6132A2 EN, active HIGH, R64 100k pull-DOWN
constexpr uint8_t DAC_MUTE   = 34; // PCM5102A XSMT via R61 100R, R60 10k pull-DOWN
                                   //   LOW  = muted (power-on default)
                                   //   HIGH = unmuted -- firmware must drive it
constexpr uint8_t REC_LED    = 35; // D5 red via R55 1k, active HIGH

}  // namespace pins

// ---- Board-level electrical facts the firmware must respect --------------
namespace board {

// PCM1864 7-bit I2C address. Datasheet: 1001 01 <AD>. U7.25 (MS/AD) is tied to
// GND, so AD = 0.  U7.26 (MD0) tied to GND selects I2C control mode.
constexpr uint8_t PCM1864_I2C_ADDR = 0x4A;

// FT6336G capacitive touch controller default 7-bit address.
constexpr uint8_t FT6336_I2C_ADDR = 0x38;

// PAD_SENSE reads ~2.88 V (logic HIGH) when SW1 selects the -10 dB pad,
// and 0 V when it is bypassed. 9 V can never reach the Teensy pin.
constexpr bool PAD_SENSE_HIGH_MEANS_PAD_ENGAGED = true;

// Nominal analog gain ahead of the ADC, from the OPA1654 stage (hardware/architecture.md).
constexpr float FIXED_PREAMP_GAIN_DB = 20.1f;
// Nominal loss of the switched divider when SW1 engages the pad.
constexpr float PAD_ATTENUATION_DB = -9.7f;

// All four control inputs have external pull-ups; use plain INPUT mode.
// Enabling INPUT_PULLDOWN on any of them fights R50-R53.
inline void configureControlPins() {
  pinMode(pins::REC_BUTTON, INPUT);
  pinMode(pins::GAIN_A,     INPUT);
  pinMode(pins::GAIN_B,     INPUT);
  pinMode(pins::GAIN_PUSH,  INPUT);
  pinMode(pins::PAD_SENSE,  INPUT);

  pinMode(pins::REC_LED,    OUTPUT);
  digitalWriteFast(pins::REC_LED, LOW);

  // Both of these MUST start inactive. HP_ENABLE has a 100k pull-down and
  // DAC_MUTE has a 10k pull-down, so the hardware powers up silent; driving
  // them low here just makes that explicit and survives a warm reset.
  pinMode(pins::HP_ENABLE,  OUTPUT);
  digitalWriteFast(pins::HP_ENABLE, LOW);
  pinMode(pins::DAC_MUTE,   OUTPUT);
  digitalWriteFast(pins::DAC_MUTE, LOW);
}

inline bool recordButtonPressed()  { return digitalReadFast(pins::REC_BUTTON) == LOW; }
inline bool encoderPushPressed()   { return digitalReadFast(pins::GAIN_PUSH)  == LOW; }
inline bool padEngaged()           { return digitalReadFast(pins::PAD_SENSE)  == HIGH; }

inline void setRecordLed(bool on)  { digitalWriteFast(pins::REC_LED,  on ? HIGH : LOW); }
inline void setHeadphoneAmp(bool on) { digitalWriteFast(pins::HP_ENABLE, on ? HIGH : LOW); }
inline void setDacMuted(bool muted)  { digitalWriteFast(pins::DAC_MUTE, muted ? LOW : HIGH); }

}  // namespace board
}  // namespace qpr
