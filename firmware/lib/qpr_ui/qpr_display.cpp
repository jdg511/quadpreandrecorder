// qpr_display.cpp — ILI9341 meter and transport screen
// Vendor: Illicit Apothecary

#include "qpr_display.h"
#include <SPI.h>
#include <string.h>
#include <stdio.h>

namespace qpr {
namespace {

constexpr int16_t W = 320, H = 240;

// Layout
constexpr int16_t kHeaderH   = 30;
constexpr int16_t kMeterTop  = 36;
constexpr int16_t kMeterH    = 22;
constexpr int16_t kMeterGap  = 6;
constexpr int16_t kLabelW    = 40;
constexpr int16_t kBarX      = kLabelW + 4;
constexpr int16_t kBarW      = W - kBarX - 46;   // leave room for the dB number
constexpr int16_t kScaleY    = kMeterTop + 4 * (kMeterH + kMeterGap);
constexpr int16_t kButtonY   = kScaleY + 14;
constexpr int16_t kButtonH   = 40;
constexpr int16_t kFooterY   = kButtonY + kButtonH + 6;

// Meter range
constexpr float kMeterMinDb = -60.0f;
constexpr float kMeterMaxDb = 0.0f;

constexpr uint16_t kBg      = ILI9341_BLACK;
constexpr uint16_t kFg      = ILI9341_WHITE;
constexpr uint16_t kDim     = 0x8410;   // mid grey
constexpr uint16_t kGreen   = 0x07E0;
constexpr uint16_t kAmber   = 0xFD20;
constexpr uint16_t kRed     = 0xF800;
constexpr uint16_t kBlue    = 0x03BF;
constexpr uint16_t kPanel   = 0x18E3;   // very dark grey

int16_t dbToPixels(float db) {
  if (db <= kMeterMinDb) return 0;
  if (db >= kMeterMaxDb) return kBarW;
  const float t = (db - kMeterMinDb) / (kMeterMaxDb - kMeterMinDb);
  return (int16_t)(t * kBarW + 0.5f);
}

uint16_t levelColour(float db) {
  if (db >= -3.0f)  return kRed;
  if (db >= -12.0f) return kAmber;
  return kGreen;
}

int16_t meterY(uint8_t ch) { return kMeterTop + ch * (kMeterH + kMeterGap); }

void formatTime(char* out, size_t n, float seconds) {
  if (seconds < 0) seconds = 0;
  const uint32_t s = (uint32_t)seconds;
  snprintf(out, n, "%lu:%02lu:%02lu",
           (unsigned long)(s / 3600), (unsigned long)((s / 60) % 60),
           (unsigned long)(s % 60));
}

// Touch button geometry
constexpr int16_t kBtnRecX = 6,   kBtnRecW = 120;
constexpr int16_t kBtnHpX  = 134, kBtnHpW  = 60;
constexpr int16_t kBtnDnX  = 202, kBtnDnW  = 52;
constexpr int16_t kBtnUpX  = 262, kBtnUpW  = 52;

}  // namespace

bool Display::begin() {
  SPI.begin();
  tft_.begin();
  tft_.setRotation(cfg::kTftRotation);
  tft_.fillScreen(kBg);

  // The ILI9341 has no reliable "are you there" register on this module, so
  // presence is assumed. If the screen stays black, t05_display_touch is the
  // test that tells you whether it is the panel, the backlight, or the SPI
  // wiring.
  present_ = true;
  dirty_all_ = true;
  return present_;
}

void Display::splash(const char* line1, const char* line2) {
  tft_.fillScreen(kBg);
  tft_.setTextColor(kFg);
  tft_.setTextSize(3);
  tft_.setCursor(14, 60);
  tft_.print("QuadPre");
  tft_.setTextSize(2);
  tft_.setCursor(16, 96);
  tft_.setTextColor(kBlue);
  tft_.print("Illicit Apothecary");
  tft_.setTextColor(kDim);
  tft_.setTextSize(1);
  tft_.setCursor(16, 140);
  tft_.print(line1);
  tft_.setCursor(16, 156);
  tft_.print(line2);
  dirty_all_ = true;
}

void Display::fatal(const char* title, const char* detail) {
  tft_.fillScreen(kBg);
  tft_.fillRect(0, 0, W, 34, kRed);
  tft_.setTextColor(kFg);
  tft_.setTextSize(2);
  tft_.setCursor(8, 9);
  tft_.print(title);

  tft_.setTextSize(1);
  tft_.setCursor(8, 52);
  // Wrap at roughly 52 characters, which is what fits at text size 1.
  const size_t len = strlen(detail);
  size_t i = 0;
  int16_t y = 52;
  while (i < len && y < H - 12) {
    size_t take = len - i > 52 ? 52 : len - i;
    if (take == 52) {
      size_t back = take;
      while (back > 0 && detail[i + back] != ' ') back--;
      if (back > 10) take = back;
    }
    char line[56];
    memcpy(line, detail + i, take);
    line[take] = 0;
    tft_.setCursor(8, y);
    tft_.print(line);
    i += take;
    while (i < len && detail[i] == ' ') i++;
    y += 12;
  }
  dirty_all_ = true;
}

void Display::drawStatic() {
  tft_.fillScreen(kBg);
  tft_.fillRect(0, 0, W, kHeaderH, kPanel);

  // Channel labels and empty meter frames.
  tft_.setTextSize(1);
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    const int16_t y = meterY(c);
    tft_.setTextColor(kFg);
    tft_.setCursor(4, y + 7);
    tft_.setTextSize(2);
    tft_.print(cfg::kChannelNames[c]);
    tft_.setTextSize(1);
    tft_.drawRect(kBarX, y, kBarW, kMeterH, kDim);
  }

  // dBFS scale ticks under the meters.
  tft_.setTextColor(kDim);
  const int8_t ticks[] = { -60, -48, -36, -24, -18, -12, -6, 0 };
  for (uint8_t i = 0; i < sizeof(ticks); i++) {
    const int16_t x = kBarX + dbToPixels((float)ticks[i]);
    tft_.drawFastVLine(x, kScaleY, 4, kDim);
    if (ticks[i] == -60 || ticks[i] == -36 || ticks[i] == -18 ||
        ticks[i] == -6 || ticks[i] == 0) {
      char t[6];
      snprintf(t, sizeof(t), "%d", ticks[i]);
      tft_.setCursor(x - (ticks[i] == 0 ? 2 : 8), kScaleY + 5);
      tft_.print(t);
    }
  }

  last_recording_ = !last_recording_;    // force the transport to redraw
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    last_bar_px_[c] = -1;
    last_rms_px_[c] = -1;
  }
  last_elapsed_s_ = 0xFFFFFFFF;
  last_gain_db_ = -999.0f;
  last_trim_db_ = -999.0f;
  last_buffer_pct_ = -1;
  last_status_[0] = 0;
  last_hp_ = !last_hp_;
}

void Display::drawTransport(const UiState& s) {
  const uint32_t el = (uint32_t)s.elapsed_s;
  if (s.recording != last_recording_ || el != last_elapsed_s_ || dirty_all_) {
    tft_.fillRect(0, 0, W, kHeaderH, kPanel);

    tft_.setTextSize(2);
    tft_.setCursor(6, 8);
    if (s.recording) {
      tft_.setTextColor(kRed);
      tft_.print("REC");
    } else if (!s.card_ok) {
      tft_.setTextColor(kAmber);
      tft_.print("NO SD");
    } else {
      tft_.setTextColor(kGreen);
      tft_.print("READY");
    }

    char buf[24];
    tft_.setTextColor(kFg);
    formatTime(buf, sizeof(buf), s.elapsed_s);
    tft_.setCursor(96, 8);
    tft_.print(buf);

    tft_.setTextSize(1);
    tft_.setTextColor(kDim);
    snprintf(buf, sizeof(buf), "take %03lu",
             (unsigned long)(s.recording ? s.take : s.take + 1));
    tft_.setCursor(200, 4);
    tft_.print(buf);

    formatTime(buf, sizeof(buf), s.remaining_s);
    tft_.setCursor(200, 17);
    tft_.print("left ");
    tft_.print(buf);

    last_recording_ = s.recording;
    last_elapsed_s_ = el;
  }
}

void Display::drawMeter(uint8_t ch, float peak_db, float rms_db, bool clipped) {
  const int16_t y = meterY(ch);
  const int16_t peak_px = dbToPixels(peak_db);
  const int16_t rms_px = dbToPixels(rms_db);

  if (peak_px != last_bar_px_[ch] || rms_px != last_rms_px_[ch] || dirty_all_) {
    const int16_t ix = kBarX + 1, iy = y + 1;
    const int16_t iw = kBarW - 2, ih = kMeterH - 2;

    // RMS is the solid body of the bar; peak is a brighter cap on top of it.
    const int16_t rms_w = rms_px > iw ? iw : rms_px;
    tft_.fillRect(ix, iy, rms_w, ih, levelColour(rms_db));
    if (rms_w < iw) tft_.fillRect(ix + rms_w, iy, iw - rms_w, ih, kBg);

    if (peak_px > rms_w + 1) {
      const int16_t cap = (peak_px > iw ? iw : peak_px) - 2;
      if (cap > 0) tft_.fillRect(ix + cap, iy, 2, ih, kFg);
    }

    // Numeric peak, right of the bar.
    char t[8];
    if (peak_db <= kMeterMinDb) snprintf(t, sizeof(t), " --  ");
    else snprintf(t, sizeof(t), "%+5.1f", (double)peak_db);
    tft_.fillRect(kBarX + kBarW + 2, y + 7, 44, 8, kBg);
    tft_.setTextSize(1);
    tft_.setTextColor(clipped ? kRed : kDim);
    tft_.setCursor(kBarX + kBarW + 2, y + 7);
    tft_.print(t);

    last_bar_px_[ch] = peak_px;
    last_rms_px_[ch] = rms_px;
  }

  if (clipped != last_clip_[ch] || dirty_all_) {
    tft_.fillRect(kBarX + kBarW - 4, y + 1, 3, kMeterH - 2,
                  clipped ? kRed : kBg);
    last_clip_[ch] = clipped;
  }
}

void Display::drawButtons(const UiState& s) {
  if (s.recording != last_recording_ || s.hp_enabled != last_hp_ || dirty_all_) {
    tft_.fillRect(kBtnRecX, kButtonY, kBtnRecW, kButtonH,
                  s.recording ? kRed : kPanel);
    tft_.drawRect(kBtnRecX, kButtonY, kBtnRecW, kButtonH, kDim);
    tft_.setTextSize(2);
    tft_.setTextColor(kFg);
    tft_.setCursor(kBtnRecX + 22, kButtonY + 13);
    tft_.print(s.recording ? "STOP" : "RECORD");

    tft_.fillRect(kBtnHpX, kButtonY, kBtnHpW, kButtonH,
                  s.hp_enabled ? kBlue : kPanel);
    tft_.drawRect(kBtnHpX, kButtonY, kBtnHpW, kButtonH, kDim);
    tft_.setCursor(kBtnHpX + 16, kButtonY + 13);
    tft_.print("HP");

    tft_.fillRect(kBtnDnX, kButtonY, kBtnDnW, kButtonH, kPanel);
    tft_.drawRect(kBtnDnX, kButtonY, kBtnDnW, kButtonH, kDim);
    tft_.setCursor(kBtnDnX + 20, kButtonY + 13);
    tft_.print("-");

    tft_.fillRect(kBtnUpX, kButtonY, kBtnUpW, kButtonH, kPanel);
    tft_.drawRect(kBtnUpX, kButtonY, kBtnUpW, kButtonH, kDim);
    tft_.setCursor(kBtnUpX + 18, kButtonY + 13);
    tft_.print("+");

    last_hp_ = s.hp_enabled;
  }
}

void Display::drawFooter(const UiState& s) {
  const int8_t buf_pct = (int8_t)(s.buffer_use * 100.0f);
  const bool changed = dirty_all_ ||
                       s.gain_db != last_gain_db_ ||
                       s.output_trim_db != last_trim_db_ ||
                       s.ref_tone != last_tone_ ||
                       s.pad_engaged != last_pad_ ||
                       buf_pct != last_buffer_pct_ ||
                       strncmp(s.status_line, last_status_, sizeof(last_status_) - 1) != 0;
  if (!changed) return;

  tft_.fillRect(0, kFooterY, W, H - kFooterY, kBg);
  tft_.setTextSize(1);

  char t[64];
  tft_.setTextColor(kFg);
  // "OUT" not "MON": this trim moves the line jack and the headphone jack
  // together. RV1 is the headphones-only control.
  snprintf(t, sizeof(t), "GAIN %+.1f dB%s   OUT %+.0f dB%s",
           (double)s.gain_db, s.pad_engaged ? " (PAD)" : "",
           (double)s.output_trim_db, s.ref_tone ? "  [TONE]" : "");
  tft_.setCursor(4, kFooterY);
  tft_.print(t);

  tft_.setTextColor(s.overruns ? kRed : kDim);
  if (s.overruns) {
    snprintf(t, sizeof(t), "buf %d%%  cpu %.0f%%  hrtf %s   LOST %lu ms",
             (int)buf_pct, (double)s.dsp_cpu_pct,
             s.measured_hrtf ? "meas" : "model", (unsigned long)s.lost_ms);
  } else {
    snprintf(t, sizeof(t), "buf %d%%  cpu %.0f%%  hrtf %s",
             (int)buf_pct, (double)s.dsp_cpu_pct,
             s.measured_hrtf ? "meas" : "model");
  }
  tft_.setCursor(4, kFooterY + 11);
  tft_.print(t);

  if (s.status_line && s.status_line[0]) {
    tft_.setTextColor(kAmber);
    tft_.setCursor(4, kFooterY + 22);
    tft_.print(s.status_line);
  }

  last_gain_db_ = s.gain_db;
  last_trim_db_ = s.output_trim_db;
  last_tone_ = s.ref_tone;
  last_pad_ = s.pad_engaged;
  last_buffer_pct_ = buf_pct;
  strncpy(last_status_, s.status_line ? s.status_line : "", sizeof(last_status_) - 1);
  last_status_[sizeof(last_status_) - 1] = 0;
}

void Display::update(const UiState& s) {
  if (!present_) return;
  if (dirty_all_) {
    drawStatic();
  }
  drawTransport(s);
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    drawMeter(c, s.meters.peak_dbfs[c], s.meters.rms_dbfs[c], s.meters.clipped[c]);
  }
  drawButtons(s);
  drawFooter(s);
  dirty_all_ = false;
}

UiHit Display::hitTest(int16_t x, int16_t y) const {
  if (y >= kButtonY && y < kButtonY + kButtonH) {
    if (x >= kBtnRecX && x < kBtnRecX + kBtnRecW) return UiHit::RecordStop;
    if (x >= kBtnHpX  && x < kBtnHpX  + kBtnHpW)  return UiHit::HeadphoneToggle;
    if (x >= kBtnDnX  && x < kBtnDnX  + kBtnDnW)  return UiHit::MonitorDown;
    if (x >= kBtnUpX  && x < kBtnUpX  + kBtnUpW)  return UiHit::MonitorUp;
  }
  // Tapping anywhere in the meter block clears the peak holds and clip flags.
  if (y >= kMeterTop && y < kScaleY) return UiHit::MeterReset;
  return UiHit::None;
}

}  // namespace qpr
