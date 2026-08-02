// qpr_controls.h — record button, EC11 gain encoder, pad-select sense
//
// Vendor: Illicit Apothecary
//
// All four inputs have external pull-ups (R50-R53, 10k) and RC filters on the
// board, so they are read as plain INPUT. Do not enable INPUT_PULLDOWN on any
// of them: it fights the pull-up and floats the threshold.
//
// The encoder is decoded from a state table rather than with interrupts. At a
// 1 ms poll the RC-filtered EC11 (tau = 100 us on A/B) cannot produce a
// transition fast enough to be missed by a human hand, and polling keeps the
// capture interrupt free of contention.

#pragma once
#include <Arduino.h>
#include "qpr_board.h"

namespace qpr {

class Controls {
 public:
  void begin();

  // Call frequently from loop(). Cheap: a few digital reads.
  void poll();

  // --- edge-triggered events, cleared by reading ---------------------------
  bool takeRecordPress();       // short press of SW2
  bool takeRecordLongPress();   // held for longer than kLongPressMs
  bool takeEncoderPress();      // short press of the EC11 shaft
  // Net encoder detents since the last call: positive = clockwise.
  int32_t takeEncoderDelta();

  // --- level state ---------------------------------------------------------
  bool padEngaged() const { return pad_engaged_; }
  bool padChanged();       // true once after SW1 moves

  static constexpr uint32_t kLongPressMs = 800;

 private:
  uint8_t  enc_state_ = 0;
  int32_t  enc_accum_ = 0;      // quarter-detents
  int32_t  enc_detents_ = 0;

  bool     rec_down_ = false;
  uint32_t rec_down_ms_ = 0;
  bool     rec_long_fired_ = false;
  bool     rec_short_ = false;
  bool     rec_long_ = false;

  bool     push_down_ = false;
  uint32_t push_down_ms_ = 0;
  bool     push_short_ = false;

  bool     pad_engaged_ = false;
  bool     pad_changed_ = false;
  uint32_t pad_stable_ms_ = 0;
  bool     pad_candidate_ = false;

  uint32_t last_poll_ms_ = 0;
};

}  // namespace qpr
