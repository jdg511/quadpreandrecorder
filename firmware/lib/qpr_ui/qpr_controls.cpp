// qpr_controls.cpp
// Vendor: Illicit Apothecary

#include "qpr_controls.h"

namespace qpr {
namespace {

// Standard quadrature transition table. Index is (previous AB << 2) | current
// AB; the value is the increment in quarter-detents. Illegal transitions
// (both lines changing at once, i.e. a missed sample) score 0 rather than
// guessing a direction.
const int8_t kQuadTable[16] = {
   0, -1, +1,  0,
  +1,  0,  0, -1,
  -1,  0,  0, +1,
   0, +1, -1,  0,
};

constexpr uint32_t kDebounceMs = 25;
constexpr uint32_t kPadStableMs = 60;

}  // namespace

void Controls::begin() {
  board::configureControlPins();
  const uint8_t a = digitalReadFast(pins::GAIN_A) ? 1 : 0;
  const uint8_t b = digitalReadFast(pins::GAIN_B) ? 1 : 0;
  enc_state_ = (uint8_t)((a << 1) | b);
  enc_accum_ = 0;
  enc_detents_ = 0;
  pad_engaged_ = board::padEngaged();
  pad_candidate_ = pad_engaged_;
  pad_changed_ = false;
  last_poll_ms_ = millis();
}

void Controls::poll() {
  const uint32_t now = millis();

  // --- encoder ------------------------------------------------------------
  const uint8_t a = digitalReadFast(pins::GAIN_A) ? 1 : 0;
  const uint8_t b = digitalReadFast(pins::GAIN_B) ? 1 : 0;
  const uint8_t state = (uint8_t)((a << 1) | b);
  if (state != enc_state_) {
    enc_accum_ += kQuadTable[(enc_state_ << 2) | state];
    enc_state_ = state;
    // An EC11 with detents produces four quadrature edges per click.
    while (enc_accum_ >= 4)  { enc_accum_ -= 4; enc_detents_++; }
    while (enc_accum_ <= -4) { enc_accum_ += 4; enc_detents_--; }
  }

  // --- record button ------------------------------------------------------
  const bool rec = board::recordButtonPressed();
  if (rec && !rec_down_) {
    rec_down_ = true;
    rec_down_ms_ = now;
    rec_long_fired_ = false;
  } else if (rec && rec_down_) {
    if (!rec_long_fired_ && (now - rec_down_ms_) >= kLongPressMs) {
      rec_long_fired_ = true;
      rec_long_ = true;
    }
  } else if (!rec && rec_down_) {
    rec_down_ = false;
    const uint32_t held = now - rec_down_ms_;
    if (held >= kDebounceMs && !rec_long_fired_) rec_short_ = true;
  }

  // --- encoder push -------------------------------------------------------
  const bool push = board::encoderPushPressed();
  if (push && !push_down_) {
    push_down_ = true;
    push_down_ms_ = now;
  } else if (!push && push_down_) {
    push_down_ = false;
    if (now - push_down_ms_ >= kDebounceMs) push_short_ = true;
  }

  // --- pad select ---------------------------------------------------------
  // SW1 is break-before-make; during the transit PAD_SELECT is only weakly
  // pulled through R42+R43, so require the new level to hold before believing
  // it.
  const bool pad = board::padEngaged();
  if (pad != pad_candidate_) {
    pad_candidate_ = pad;
    pad_stable_ms_ = now;
  } else if (pad != pad_engaged_ && (now - pad_stable_ms_) >= kPadStableMs) {
    pad_engaged_ = pad;
    pad_changed_ = true;
  }

  last_poll_ms_ = now;
}

bool Controls::takeRecordPress()      { bool v = rec_short_;  rec_short_ = false;  return v; }
bool Controls::takeRecordLongPress()  { bool v = rec_long_;   rec_long_ = false;   return v; }
bool Controls::takeEncoderPress()     { bool v = push_short_; push_short_ = false; return v; }
bool Controls::padChanged()           { bool v = pad_changed_; pad_changed_ = false; return v; }

int32_t Controls::takeEncoderDelta() {
  const int32_t v = enc_detents_;
  enc_detents_ = 0;
  return v;
}

}  // namespace qpr
