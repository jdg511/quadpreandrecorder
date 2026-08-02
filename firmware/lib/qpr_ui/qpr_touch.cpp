// qpr_touch.cpp — FT6336G capacitive touch
// Vendor: Illicit Apothecary

#include "qpr_touch.h"
#include <Wire.h>

namespace qpr {
namespace {
constexpr uint8_t REG_TD_STATUS = 0x02;   // low 4 bits = number of touches
constexpr uint8_t REG_P1_XH     = 0x03;   // then XL, YH, YL
constexpr uint8_t REG_TH_GROUP  = 0x80;   // touch threshold
constexpr uint8_t REG_CHIP_ID   = 0xA3;
constexpr uint8_t REG_VENDOR_ID = 0xA8;   // 0x11 for FocalTech

// Native panel resolution of the LCDWiki MSP2834 in its portrait orientation,
// which is what the touch controller reports in.
constexpr int16_t kPanelW = 240;
constexpr int16_t kPanelH = 320;
}  // namespace

bool TouchFt6336::readRegs(uint8_t start, uint8_t* buf, uint8_t len) {
  Wire.beginTransmission(board::FT6336_I2C_ADDR);
  Wire.write(start);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)board::FT6336_I2C_ADDR, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = (uint8_t)Wire.read();
  return true;
}

bool TouchFt6336::begin(uint8_t rotation) {
  rotation_ = rotation;

  // TOUCH_RST is active low. The datasheet wants at least 5 ms of reset and
  // about 300 ms before the controller answers on I2C.
  pinMode(pins::TOUCH_RST, OUTPUT);
  digitalWriteFast(pins::TOUCH_RST, LOW);
  delay(10);
  digitalWriteFast(pins::TOUCH_RST, HIGH);
  delay(300);

  pinMode(pins::TOUCH_IRQ, INPUT);   // module has its own pull-up

  uint8_t v = 0, c = 0;
  if (!readRegs(REG_VENDOR_ID, &v, 1)) { present_ = false; return false; }
  if (!readRegs(REG_CHIP_ID, &c, 1))   { present_ = false; return false; }
  vendor_id_ = v;
  chip_id_ = c;

  // Any answer at all means something is there. Accept a range of chip IDs:
  // FT6206/FT6236/FT6336 variants all report different values and the module
  // vendor changes parts without notice.
  present_ = (v != 0x00 && v != 0xFF);

  if (present_) {
    Wire.beginTransmission(board::FT6336_I2C_ADDR);
    Wire.write(REG_TH_GROUP);
    Wire.write(22);          // touch threshold; lower = more sensitive
    Wire.endTransmission();
  }
  return present_;
}

TouchFt6336::Point TouchFt6336::read() {
  Point p{ -1, -1, false };
  if (!present_) return p;

  uint8_t buf[5];
  if (!readRegs(REG_TD_STATUS, buf, 5)) return p;

  const uint8_t touches = buf[0] & 0x0F;
  if (touches == 0 || touches > 2) return p;

  const int16_t raw_x = (int16_t)(((buf[1] & 0x0F) << 8) | buf[2]);
  const int16_t raw_y = (int16_t)(((buf[3] & 0x0F) << 8) | buf[4]);

  // Map the panel's portrait coordinates onto the display rotation. Rotation
  // numbering matches ILI9341_t3::setRotation.
  switch (rotation_ & 3) {
    case 0: p.x = raw_x;               p.y = raw_y;               break;
    case 1: p.x = raw_y;               p.y = kPanelW - 1 - raw_x; break;
    case 2: p.x = kPanelW - 1 - raw_x; p.y = kPanelH - 1 - raw_y; break;
    default:p.x = kPanelH - 1 - raw_y; p.y = raw_x;               break;
  }
  p.pressed = true;
  return p;
}

}  // namespace qpr
