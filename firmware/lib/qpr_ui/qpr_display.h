// qpr_display.h — ILI9341 meter and transport screen
//
// Vendor: Illicit Apothecary
//
// 320x240 landscape. Everything is drawn as small dirty rectangles rather than
// as full-screen repaints, because a full 320x240 SPI repaint at 25 Hz would
// hold the SPI bus (and the CPU) for far longer than the audio path can spare.
//
// Runs entirely at thread level from loop(). Nothing here may be called from
// an interrupt.

#pragma once
#include <Arduino.h>
#include <ILI9341_t3.h>
#include "qpr_config.h"
#include "qpr_board.h"
#include "qpr_dsp.h"

namespace qpr {

// What the UI needs to know about the rest of the system in order to draw.
struct UiState {
  bool     recording = false;
  bool     card_ok = false;
  uint32_t take = 0;
  float    elapsed_s = 0.0f;
  float    remaining_s = 0.0f;
  float    buffer_use = 0.0f;      // 0..1, peak ring occupancy
  uint32_t overruns = 0;
  uint32_t lost_ms = 0;      // audio lost to overruns, in milliseconds
  float    gain_db = 0.0f;
  bool     pad_engaged = false;
  bool     hp_enabled = false;
  // Digital trim on the shared stereo render. Moves BOTH jacks:
  // the line output and the headphone output come from one DAC and
  // split in the analog domain. The RV1 knob is headphones only.
  float    output_trim_db = 0.0f;
  bool     ref_tone = false;
  float    dsp_cpu_pct = 0.0f;
  bool     measured_hrtf = false;
  const char* status_line = "";
  Meters::Reading meters{};
};

// Touch-sensitive regions. Returned by Display::hitTest().
enum class UiHit : uint8_t {
  None = 0,
  RecordStop,
  HeadphoneToggle,
  MonitorDown,
  MonitorUp,
  MeterReset,
};

class Display {
 public:
  bool begin();
  bool present() const { return present_; }

  // Repaints whatever has changed. Call at cfg::kMeterUpdateHz.
  void update(const UiState& s);

  // Full repaint, e.g. after the splash screen or an error page.
  void forceRedraw() { dirty_all_ = true; }

  void splash(const char* line1, const char* line2);
  // Big readable error page for the failures a user can actually act on.
  void fatal(const char* title, const char* detail);

  UiHit hitTest(int16_t x, int16_t y) const;

 private:
  void drawStatic();
  void drawTransport(const UiState& s);
  void drawMeter(uint8_t ch, float peak_db, float rms_db, bool clipped);
  void drawFooter(const UiState& s);
  void drawButtons(const UiState& s);

  ILI9341_t3 tft_{ pins::TFT_CS, pins::TFT_DC, pins::TFT_RST,
                   pins::SPI_MOSI, pins::SPI_SCK, pins::SPI_MISO };
  bool present_ = false;
  bool dirty_all_ = true;

  // Last drawn values, so we only touch pixels that actually changed.
  int16_t last_bar_px_[cfg::kChannels] = { -1, -1, -1, -1 };
  int16_t last_rms_px_[cfg::kChannels] = { -1, -1, -1, -1 };
  bool    last_clip_[cfg::kChannels] = { false, false, false, false };
  bool    last_recording_ = false;
  bool    last_hp_ = false;
  uint32_t last_elapsed_s_ = 0xFFFFFFFF;
  float   last_gain_db_ = -999.0f;
  float   last_trim_db_ = -999.0f;
  bool    last_tone_ = false;
  bool    last_pad_ = false;
  int8_t  last_buffer_pct_ = -1;
  char    last_status_[48] = "";
};

}  // namespace qpr
