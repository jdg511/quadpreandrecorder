// t02_i2c_scan.cpp — bring-up test 2: the I2C bus and the PCM1864 ADC
//
// Vendor: Illicit Apothecary
//
// WHAT IT PROVES
//   - The I2C bus works and has its pull-ups (R44/R45, 4.7k to +3V3_D).
//   - The PCM1864 answers at 0x4A, which also confirms that U7 pin 25 (MS/AD)
//     and pin 26 (MD0) are grounded and the part has power.
//   - Registers can be written and read back, so the part is not half-dead.
//   - GPIO0 can be retasked as DOUT2 -- the single register write the whole
//     192 kHz four-channel scheme depends on.
//   - The FT6336G capacitive touch controller answers at 0x38, if the display
//     module is plugged in.
//
// WHAT TO EXPECT
//   A device list containing 0x38 (touch) and 0x4A (ADC), then a series of
//   register tests all reading "ok", then a live clock-status readout.
//
//   The clock status WILL show errors in this test. That is correct: no audio
//   clocks are running yet, so the ADC sits in the clock-waiting state. Test 6
//   is where the clocks start.
//
// IF IT FAILS
//   No devices found at all      -> check R44/R45, and that +3V3_D is present
//                                   at U7 pins 13/14.
//   0x4A missing, 0x38 present   -> the ADC has a power or solder problem;
//                                   check AVDD (pin 8), DVDD (13), IOVDD (14),
//                                   and the pin 25/26 ground connections.
//   0x38 missing, 0x4A present   -> the display module is unplugged, its
//                                   TOUCH_RST line is stuck, or the module is
//                                   a resistive-touch variant. The recorder
//                                   works without touch.
//   Readback mismatch            -> marginal I2C. Slow the bus to 100 kHz in
//                                   this file and try again; if that fixes it,
//                                   look at bus capacitance and pull-up value.

#include <Arduino.h>
#include <Wire.h>
#include "qpr_board.h"
#include "qpr_pcm1864.h"

using namespace qpr;

static Pcm1864 adc;

static const char* knownDevice(uint8_t addr) {
  switch (addr) {
    case 0x38: return "FT6336G capacitive touch (display module)";
    case 0x4A: return "PCM1864 four-channel ADC (U7)";
    default:   return "unexpected device";
  }
}

static void scanBus() {
  Serial.println(F("Scanning the I2C bus..."));
  uint8_t found = 0;
  bool saw_adc = false, saw_touch = false;
  for (uint8_t a = 0x08; a < 0x78; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X  %s\n", a, knownDevice(a));
      found++;
      if (a == 0x4A) saw_adc = true;
      if (a == 0x38) saw_touch = true;
    }
  }
  if (found == 0) {
    Serial.println(F("  NOTHING FOUND."));
    Serial.println(F("  Either the bus is shorted, the pull-ups R44/R45 are"));
    Serial.println(F("  missing, or +3V3_D is not reaching the devices."));
  }
  Serial.printf("  %u device(s). ADC %s, touch %s.\n\n", found,
                saw_adc ? "PRESENT" : "MISSING",
                saw_touch ? "present" : "missing (display unplugged?)");
}

static void testRegister(const char* label, uint8_t reg, uint8_t value) {
  Pcm1864::Status s = adc.writeReg(0, reg, value);
  if (s != Pcm1864::Status::Ok) {
    Serial.printf("  %-28s WRITE FAILED (%s)\n", label, Pcm1864::statusName(s));
    return;
  }
  uint8_t back = 0xFF;
  s = adc.readReg(0, reg, &back);
  if (s != Pcm1864::Status::Ok) {
    Serial.printf("  %-28s READ FAILED (%s)\n", label, Pcm1864::statusName(s));
    return;
  }
  Serial.printf("  %-28s wrote 0x%02X, read 0x%02X   %s\n", label, value, back,
                back == value ? "ok" : "MISMATCH");
}

void setup() {
  board::configureControlPins();
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  // Release the touch controller from reset so it can answer the scan.
  pinMode(pins::TOUCH_RST, OUTPUT);
  digitalWriteFast(pins::TOUCH_RST, LOW);
  delay(10);
  digitalWriteFast(pins::TOUCH_RST, HIGH);
  delay(300);

  Wire.begin();
  Wire.setClock(400000);

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 2 of 6: I2C AND THE ADC"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();

  scanBus();

  Serial.println(F("Configuring the PCM1864 for dual-line I2S..."));
  Pcm1864::Status s = adc.begin(Pcm1864::Format::DualI2S);
  Serial.printf("  result: %s\n\n", Pcm1864::statusName(s));

  Serial.println(F("Register write/read tests"));
  testRegister("PGA ch1 L = +6.0 dB", 0x01, 0x0C);
  testRegister("PGA ch1 L = -6.0 dB", 0x01, 0xF4);
  testRegister("PGA ch1 L = 0 dB", 0x01, 0x00);
  testRegister("ADC1 L input select", 0x06, 0x41);
  testRegister("ADC2 L input select", 0x08, 0x42);
  testRegister("format: I2S, 32-bit", 0x0B, 0x00);
  testRegister("GPIO0 function = DOUT2", 0x10, 0x05);
  Serial.println();

  Serial.println(F("Read-only identity and status registers"));
  uint8_t v = 0;
  if (adc.readReg(0, 0x72, &v) == Pcm1864::Status::Ok) {
    Serial.printf("  device state (0x72)        0x%02X  %s\n", v,
                  Pcm1864::stateName(v));
  }
  if (adc.readReg(0, 0x78, &v) == Pcm1864::Status::Ok) {
    Serial.printf("  supply status (0x78)       0x%02X  DVDD %s, AVDD %s, LDO %s\n",
                  v, (v & 0x04) ? "ok" : "LOW", (v & 0x02) ? "ok" : "LOW",
                  (v & 0x01) ? "ok" : "LOW");
  }
  Serial.println();
  Serial.println(F("Now watching the ADC clock status once a second."));
  Serial.println(F("Errors here are EXPECTED: nothing is generating clocks yet."));
  Serial.println(F("Test 6 (t06_audio) is where the clocks start."));
  Serial.println();
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < 1000) return;
  last = millis();

  Pcm1864::ClockStatus cs{};
  if (adc.readClockStatus(&cs) != Pcm1864::Status::Ok) {
    Serial.println(F("  ADC stopped answering on I2C"));
    return;
  }
  Serial.printf("  state %-18s SCK %-28s BCK %s\n",
                Pcm1864::stateName(cs.state),
                Pcm1864::sckRatioName(cs.sck_ratio_code),
                Pcm1864::bckRatioName(cs.bck_ratio_code));
  board::setRecordLed((millis() / 500) & 1);
}
