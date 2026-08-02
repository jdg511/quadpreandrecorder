// t05_display_touch.cpp — bring-up test 5: the TFT and its capacitive touch
//
// Vendor: Illicit Apothecary
//
// WHAT IT PROVES
//   - The ILI9341 display responds over SPI on the J3 header wiring.
//   - Colours and orientation are right, so the module's pin order matches
//     hardware/connector-pinout.md.
//   - The FT6336G touch controller answers on I2C and reports coordinates
//     that line up with what you touched.
//
// NOTE ON PIN 5
//   Teensy pin 5 is TOUCH_RST, not a chip select. The FT6336G is an I2C
//   device. Older notes in this project called it "TOUCH_CS"; that came from
//   an earlier resistive-touch design and is wrong for Rev A. If you drive
//   pin 5 as a chip select, the controller stays in reset and never answers.
//
// WHAT TO EXPECT
//   1. Colour bars, then a white border, then text. If the border is not
//      flush with all four edges, the rotation or the panel variant is wrong.
//   2. A target grid. Touch each of the five crosses. The test draws where it
//      thinks you touched and reports the error in pixels.
//   3. A free-draw area: drag a finger and watch the line follow it.
//
// IF IT FAILS
//   Backlight on, screen black   -> SPI wiring (J3 pins 3/5/6/7/9) or the
//                                   TFT_RST line on Teensy pin 7.
//   Backlight off entirely       -> R56 (100R from +5V to J3 pin 8), or the
//                                   module needs more current than 100R
//                                   allows. This is hardwired on; there is no
//                                   software dimming.
//   Colours inverted or swapped  -> the module is a BGR-panel variant. Change
//                                   the ILI9341_t3 init or use ILI9341_t3n.
//   Touch reports nothing        -> check J3 pins 10/11/12/13, and confirm the
//                                   module actually has capacitive touch. Some
//                                   MSP2834 revisions ship with resistive
//                                   XPT2046 touch instead, which will never
//                                   answer at I2C address 0x38.
//   Touch axes swapped/mirrored  -> fix the rotation mapping in
//                                   TouchFt6336::read().

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <ILI9341_t3.h>
#include "qpr_board.h"
#include "qpr_config.h"
#include "qpr_touch.h"

using namespace qpr;

static ILI9341_t3 tft(pins::TFT_CS, pins::TFT_DC, pins::TFT_RST,
                      pins::SPI_MOSI, pins::SPI_SCK, pins::SPI_MISO);
static TouchFt6336 touch;

static const int16_t W = 320, H = 240;
struct Target { int16_t x, y; bool hit; float err; };
static Target targets[5] = {
  { 30,  30,  false, 0 }, { 290, 30,  false, 0 },
  { 160, 120, false, 0 },
  { 30,  210, false, 0 }, { 290, 210, false, 0 },
};
static uint8_t stage = 0;
static uint32_t stage_ms = 0;

static void colourBars() {
  const uint16_t cols[8] = { ILI9341_WHITE, ILI9341_YELLOW, ILI9341_CYAN,
                             ILI9341_GREEN, ILI9341_MAGENTA, ILI9341_RED,
                             ILI9341_BLUE, ILI9341_BLACK };
  const int16_t bw = W / 8;
  for (uint8_t i = 0; i < 8; i++) tft.fillRect(i * bw, 0, bw, H, cols[i]);
  tft.drawRect(0, 0, W, H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_WHITE, ILI9341_BLACK);
  tft.setTextSize(2);
  tft.setCursor(8, H - 40);
  tft.print("COLOUR BARS");
  tft.setTextSize(1);
  tft.setCursor(8, H - 18);
  tft.print("white yellow cyan green magenta red blue black");
}

static void drawCross(int16_t x, int16_t y, uint16_t c) {
  tft.drawFastHLine(x - 10, y, 21, c);
  tft.drawFastVLine(x, y - 10, 21, c);
  tft.drawCircle(x, y, 6, c);
}

static void startTargets() {
  tft.fillScreen(ILI9341_BLACK);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(1);
  tft.setCursor(60, 140);
  tft.print("Touch each cross");
  for (uint8_t i = 0; i < 5; i++) drawCross(targets[i].x, targets[i].y,
                                            ILI9341_YELLOW);
}

void setup() {
  board::configureControlPins();
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 5 of 6: DISPLAY + TOUCH"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();

  SPI.begin();
  tft.begin();
  tft.setRotation(cfg::kTftRotation);
  Serial.printf("Display initialised, rotation %u, %dx%d\n",
                cfg::kTftRotation, tft.width(), tft.height());

  Wire.begin();
  Wire.setClock(400000);

  Serial.println(F("Resetting the touch controller (Teensy pin 5 = TOUCH_RST,"));
  Serial.println(F("not a chip select -- the FT6336G is an I2C device)."));
  if (touch.begin(cfg::kTftRotation)) {
    Serial.printf("Touch controller found: vendor 0x%02X, chip 0x%02X\n",
                  touch.vendorId(), touch.chipId());
  } else {
    Serial.println(F("TOUCH CONTROLLER DID NOT ANSWER at 0x38."));
    Serial.println(F("  The display half of this test still runs."));
    Serial.println(F("  Check J3 pins 10/11/12/13, or confirm the module has"));
    Serial.println(F("  capacitive (FT6336G) and not resistive (XPT2046) touch."));
  }

  colourBars();
  stage = 0;
  stage_ms = millis();
  Serial.println(F("\nStage 1: colour bars. Check the order and the border."));
}

void loop() {
  const uint32_t now = millis();

  if (stage == 0 && now - stage_ms > 6000) {
    stage = 1;
    stage_ms = now;
    startTargets();
    Serial.println(F("Stage 2: touch each of the five crosses."));
    if (!touch.present()) {
      Serial.println(F("  (no touch controller -- skipping in 8 s)"));
    }
  }

  if (stage == 1) {
    if (touch.present() && touch.interruptAsserted()) {
      const TouchFt6336::Point p = touch.read();
      if (p.pressed) {
        tft.fillCircle(p.x, p.y, 3, ILI9341_GREEN);
        // Find the nearest unhit target.
        int best = -1;
        float best_d = 1e9f;
        for (uint8_t i = 0; i < 5; i++) {
          const float dx = p.x - targets[i].x, dy = p.y - targets[i].y;
          const float d = sqrtf(dx * dx + dy * dy);
          if (d < best_d) { best_d = d; best = i; }
        }
        if (best >= 0 && best_d < 40.0f && !targets[best].hit) {
          targets[best].hit = true;
          targets[best].err = best_d;
          drawCross(targets[best].x, targets[best].y, ILI9341_GREEN);
          Serial.printf("  target %d at (%d,%d): touched (%d,%d), error %.1f px\n",
                        best, targets[best].x, targets[best].y, p.x, p.y,
                        (double)best_d);
        } else if (best_d >= 40.0f) {
          Serial.printf("  touch at (%d,%d) is %.0f px from any target -- "
                        "axes may be swapped or mirrored\n",
                        p.x, p.y, (double)best_d);
        }
      }
    }

    uint8_t hits = 0;
    for (uint8_t i = 0; i < 5; i++) if (targets[i].hit) hits++;
    if (hits == 5 || (!touch.present() && now - stage_ms > 8000) ||
        now - stage_ms > 45000) {
      float worst = 0;
      for (uint8_t i = 0; i < 5; i++) if (targets[i].err > worst) worst = targets[i].err;
      Serial.printf("Stage 2 result: %u of 5 targets, worst error %.1f px  %s\n",
                    hits, (double)worst,
                    (hits == 5 && worst < 20.0f) ? "PASS" :
                    (hits == 5 ? "usable, but the mapping could be tightened"
                               : "INCOMPLETE"));
      stage = 2;
      stage_ms = now;
      tft.fillScreen(ILI9341_BLACK);
      tft.setTextColor(ILI9341_WHITE);
      tft.setTextSize(1);
      tft.setCursor(8, 4);
      tft.print("Stage 3: drag a finger to draw. Reflash t01 when done.");
      Serial.println(F("Stage 3: free draw. Drag a finger across the screen."));
    }
  }

  if (stage == 2 && touch.present() && touch.interruptAsserted()) {
    static int16_t px = -1, py = -1;
    const TouchFt6336::Point p = touch.read();
    if (p.pressed) {
      if (px >= 0) tft.drawLine(px, py, p.x, p.y, ILI9341_CYAN);
      else tft.fillCircle(p.x, p.y, 2, ILI9341_CYAN);
      px = p.x; py = p.y;
    } else {
      px = py = -1;
    }
  }

  board::setRecordLed((now / 500) & 1);
}
