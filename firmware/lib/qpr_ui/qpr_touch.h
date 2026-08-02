// qpr_touch.h — FocalTech FT6336G capacitive touch controller over I2C
//
// Vendor: Illicit Apothecary
//
// IMPORTANT: earlier revisions of this project's documentation described
// Teensy pin 5 as "touch CS". That was left over from a resistive XPT2046
// design. The Rev A hardware uses an FT6336G, which is an I2C device with a
// reset line and an interrupt line and NO chip select. Pin 5 is TOUCH_RST and
// driving it as a chip select holds the controller in reset forever.
//
// The controller shares the I2C bus with the PCM1864 (0x4A). It sits at 0x38.

#pragma once
#include <Arduino.h>
#include "qpr_board.h"

namespace qpr {

class TouchFt6336 {
 public:
  struct Point { int16_t x, y; bool pressed; };

  // Pulses TOUCH_RST and probes the controller. Returns false if it does not
  // answer, which usually means the display module is unplugged, is a
  // resistive-touch variant, or has no 3.3 V rail.
  bool begin(uint8_t rotation);

  bool present() const { return present_; }
  uint8_t vendorId() const { return vendor_id_; }
  uint8_t chipId()   const { return chip_id_; }

  // Reads the current touch point, mapped into display coordinates for the
  // rotation given to begin(). Safe to call at any rate; the controller holds
  // the last point until release.
  Point read();

  // True while TOUCH_IRQ is asserted (active low). Use it to skip the I2C
  // read entirely when nothing is being touched.
  bool interruptAsserted() const {
    return digitalReadFast(pins::TOUCH_IRQ) == LOW;
  }

 private:
  bool readRegs(uint8_t start, uint8_t* buf, uint8_t len);

  bool    present_ = false;
  uint8_t rotation_ = 1;
  uint8_t vendor_id_ = 0;
  uint8_t chip_id_ = 0;
};

}  // namespace qpr
