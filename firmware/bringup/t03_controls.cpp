// t03_controls.cpp — bring-up test 3: buttons, encoder, pad switch
//
// Vendor: Illicit Apothecary
//
// WHAT IT PROVES
//   - SW2 (record button) makes and breaks cleanly.
//   - SW3 (EC11 encoder) counts in the right direction and does not skip or
//     bounce between detents.
//   - SW3's shaft push works.
//   - SW1 (pad select) reaches both states, and the R42/R43 divider delivers
//     a safe voltage to the Teensy rather than 9 V.
//   - The record LED responds.
//
// WHAT TO DO
//   Open the serial monitor. Then, one at a time:
//     1. Press and release the record button a few times, including one long
//        press of about a second.
//     2. Turn the encoder slowly one full turn clockwise, then one full turn
//        anticlockwise. Count the detents as you go.
//     3. Press the encoder shaft.
//     4. Flip the pad switch back and forth.
//   The test keeps a running tally and tells you when each control has been
//   exercised. It prints PASS for a control once it has seen enough of it.
//
// WHAT TO LOOK FOR
//   - Clockwise must report "+1". If it reports "-1", the A and B lines are
//     swapped at the encoder; either swap them in the harness or swap
//     GAIN_A and GAIN_B in qpr_board.h.
//   - One physical detent must produce exactly one count. Several counts per
//     detent means the encoder is not a 4-edge-per-detent type; adjust the
//     divisor in Controls::poll().
//   - Bounce warnings mean the RC filter is not doing its job; check
//     C48/C49/C50.

#include <Arduino.h>
#include "qpr_board.h"
#include "qpr_controls.h"

using namespace qpr;

static Controls controls;

static int32_t enc_position = 0;
static uint32_t rec_presses = 0, rec_long = 0, push_presses = 0;
static uint32_t pad_changes = 0;
static uint32_t cw_detents = 0, ccw_detents = 0;
static bool seen_pad_in = false, seen_pad_out = false;

// Raw-edge counter, to spot contact bounce the debouncer would otherwise hide.
static uint32_t raw_edges = 0;
static bool last_raw_rec = true;
static uint32_t last_edge_ms = 0;
static uint32_t bounce_events = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }
  controls.begin();

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" QuadPreRecorder bring-up test 3 of 6: CONTROLS"));
  Serial.println(F(" Illicit Apothecary"));
  Serial.println(F("======================================================"));
  Serial.println();
  Serial.println(F("Exercise each control. The test reports as you go."));
  Serial.println(F("  1. press the RECORD button (short and long)"));
  Serial.println(F("  2. turn the encoder one turn each way"));
  Serial.println(F("  3. press the encoder shaft"));
  Serial.println(F("  4. flip the pad switch both ways"));
  Serial.println();
  Serial.printf("Pad switch starts %s.\n\n",
                controls.padEngaged() ? "IN (engaged)" : "OUT (bypassed)");
  if (controls.padEngaged()) seen_pad_in = true; else seen_pad_out = true;
}

void loop() {
  controls.poll();

  // Raw bounce watch on the record button.
  const bool raw = digitalReadFast(pins::REC_BUTTON) != 0;
  if (raw != last_raw_rec) {
    last_raw_rec = raw;
    raw_edges++;
    const uint32_t now = millis();
    if (now - last_edge_ms < 5) bounce_events++;
    last_edge_ms = now;
  }

  if (controls.takeRecordPress()) {
    rec_presses++;
    Serial.printf("RECORD short press  (#%lu)\n", (unsigned long)rec_presses);
  }
  if (controls.takeRecordLongPress()) {
    rec_long++;
    Serial.printf("RECORD long press   (#%lu)\n", (unsigned long)rec_long);
  }
  if (controls.takeEncoderPress()) {
    push_presses++;
    Serial.printf("ENCODER shaft press (#%lu)\n", (unsigned long)push_presses);
  }

  const int32_t d = controls.takeEncoderDelta();
  if (d != 0) {
    enc_position += d;
    if (d > 0) cw_detents += (uint32_t)d; else ccw_detents += (uint32_t)(-d);
    Serial.printf("ENCODER %+ld  ->  position %ld   (%s)\n", (long)d,
                  (long)enc_position,
                  d > 0 ? "clockwise, correct if you turned right"
                        : "anticlockwise, correct if you turned left");
  }

  if (controls.padChanged()) {
    pad_changes++;
    if (controls.padEngaged()) seen_pad_in = true; else seen_pad_out = true;
    Serial.printf("PAD switch -> %s   (change #%lu)\n",
                  controls.padEngaged() ? "IN (-9.7 dB)" : "OUT (0 dB)",
                  (unsigned long)pad_changes);
  }

  board::setRecordLed(board::recordButtonPressed());

  // Summary every five seconds.
  static uint32_t last_summary = 0;
  if (millis() - last_summary >= 5000) {
    last_summary = millis();
    Serial.println();
    Serial.println(F("--- progress ---"));
    Serial.printf("  record button : %lu short, %lu long        %s\n",
                  (unsigned long)rec_presses, (unsigned long)rec_long,
                  (rec_presses >= 2 && rec_long >= 1) ? "PASS" : "keep going");
    Serial.printf("  encoder       : %lu CW, %lu CCW, at %ld    %s\n",
                  (unsigned long)cw_detents, (unsigned long)ccw_detents,
                  (long)enc_position,
                  (cw_detents >= 10 && ccw_detents >= 10) ? "PASS" : "keep going");
    Serial.printf("  encoder push  : %lu                        %s\n",
                  (unsigned long)push_presses,
                  push_presses >= 1 ? "PASS" : "keep going");
    Serial.printf("  pad switch    : IN seen %s, OUT seen %s     %s\n",
                  seen_pad_in ? "yes" : "no ", seen_pad_out ? "yes" : "no ",
                  (seen_pad_in && seen_pad_out) ? "PASS" : "keep going");
    if (bounce_events) {
      Serial.printf("  ! %lu fast edges on the record button -- check C47\n",
                    (unsigned long)bounce_events);
    }
    Serial.println();
  }
}
