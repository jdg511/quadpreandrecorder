// t01_power_serial.cpp — bring-up test 1: is the board alive?
//
// Vendor: Illicit Apothecary
//
// FLASH THIS FIRST on a brand new board.
//
// WHAT IT PROVES
//   - The Teensy boots, runs, and talks over USB serial.
//   - The record LED (D5) and its 1k resistor (R55) work.
//   - Every control input idles at the level the schematic says it should.
//   - The headphone amplifier and DAC mute lines can be driven, and start
//     in their safe (silent) state.
//
// WHAT TO EXPECT
//   The red RECORD LED blinks once per second. The blue POWER LED (D4) is
//   always on and is not under software control; if it is dark, you have a
//   power problem, not a firmware problem.
//   Open the serial monitor at 115200 baud. You should see a report every
//   two seconds with every line saying "ok".
//
// IF IT FAILS
//   Nothing on serial at all      -> the Teensy is not running. Check the
//                                    9 V input, F1, D1/D2, the TPS62160 5 V
//                                    rail, and D3 into Teensy VIN.
//   Serial works, LED never lights-> check D5 orientation and R55.
//   A control input reads LOW when it should be HIGH -> that input is shorted
//                                    to ground, or its 10k pull-up
//                                    (R50/R51/R52/R53) is missing.
//
// SAFETY: this test never enables the headphone amplifier and never unmutes
// the DAC. You can have headphones plugged in.

#include <Arduino.h>
#include "qpr_board.h"

using namespace qpr;

static void reportPin(const char* name, uint8_t pin, bool expect_high,
                      const char* meaning_if_wrong) {
  const bool high = digitalReadFast(pin) != 0;
  const bool ok = (high == expect_high);
  Serial.printf("  %-12s pin %-2u = %s   %s", name, pin, high ? "HIGH" : "LOW ",
                ok ? "ok" : "UNEXPECTED");
  if (!ok) Serial.printf("  <- %s", meaning_if_wrong);
  Serial.println();
}

void setup() {
  board::configureControlPins();
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 1 of 6: POWER AND I/O"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();
  Serial.println(F("The red RECORD LED should be blinking once per second."));
  Serial.println(F("The blue POWER LED is hardwired on and is not tested here."));
  Serial.println();
}

void loop() {
  static uint32_t last_blink = 0;
  static uint32_t last_report = 0;
  static bool led = false;
  const uint32_t now = millis();

  if (now - last_blink >= 500) {
    last_blink = now;
    led = !led;
    board::setRecordLed(led);
  }

  if (now - last_report >= 2000) {
    last_report = now;

    Serial.printf("--- t=%lu s ---\n", (unsigned long)(now / 1000));
    Serial.printf("  CPU          %lu MHz, core temp %.1f C\n",
                  (unsigned long)(F_CPU_ACTUAL / 1000000),
                  (double)tempmonGetTemp());

    Serial.println(F("  control inputs (all have 10k pull-ups; idle = HIGH)"));
    reportPin("REC_BUTTON", pins::REC_BUTTON, true,
              "SW2 stuck closed, or R50 missing");
    reportPin("GAIN_A", pins::GAIN_A, true, "encoder A shorted, or R51 missing");
    reportPin("GAIN_B", pins::GAIN_B, true, "encoder B shorted, or R52 missing");
    reportPin("GAIN_PUSH", pins::GAIN_PUSH, true,
              "encoder shaft stuck pressed, or R53 missing");

    Serial.printf("  %-12s pin %-2u = %s   (SW1 %s -- both states are valid)\n",
                  "PAD_SENSE", pins::PAD_SENSE,
                  board::padEngaged() ? "HIGH" : "LOW ",
                  board::padEngaged() ? "pad IN" : "pad out");

    Serial.println(F("  outputs (must both be LOW = silent at power-up)"));
    reportPin("HP_ENABLE", pins::HP_ENABLE, false,
              "headphone amp is ON when it should be off");
    reportPin("DAC_MUTE", pins::DAC_MUTE, false,
              "DAC is UNMUTED when it should be muted");

    Serial.println(F("  Press the RECORD button and turn the encoder now;"));
    Serial.println(F("  the next report should show them changing."));
    Serial.println();
  }
}
