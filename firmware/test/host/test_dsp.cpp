// test_dsp.cpp — run the REAL firmware monitor DSP on a desktop
//
// Vendor: Illicit Apothecary
//
// This links lib/qpr_dsp/qpr_dsp.cpp and qpr_coeffs.cpp unmodified. The
// decimator, the A-format-to-B-format matrix, the eight binaural FIRs and the
// limiter that run here are byte-for-byte the ones the Teensy runs.
//
//   in   : raw int32 little-endian, 4 channels interleaved (FLU FRD BLD BRU),
//          sign-extended 24-bit values, at the capture rate
//   out  : raw float32 little-endian, 2 channels interleaved, at 48 kHz
//
// sim/compare_firmware_to_model.py then checks this against the Python model.
// If the two disagree by more than float rounding, one of them is wrong, and
// that is exactly the bug this catches: a firmware DSP that quietly does
// something different from the thing you tuned by ear.

#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>

#include "qpr_config.h"
#include "qpr_sai.h"
#include "qpr_dsp.h"

using namespace qpr;

static MonitorDsp g_dsp;
static Meters g_meters;

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr,
            "usage: %s <in.a4.raw> <out.stereo.f32> [meters.txt] [trim_dB]\n"
            "  in : int32 LE, 4ch interleaved, 24-bit values, %lu Hz\n"
            "  out: float32 LE, 2ch interleaved, %lu Hz\n",
            argv[0], (unsigned long)cfg::kSampleRateHz,
            (unsigned long)cfg::kMonitorRateHz);
    return 2;
  }

  FILE* fin = fopen(argv[1], "rb");
  if (!fin) { perror("input"); return 1; }
  FILE* fout = fopen(argv[2], "wb");
  if (!fout) { perror("output"); return 1; }

  g_dsp.begin();
  g_meters.reset();

  // Optional trim, so the comparison can push the signal into the limiter.
  // The limiter is the only stateful, non-linear stage in the chain and so
  // the one most likely for two implementations to disagree about.
  if (argc > 4) {
    g_dsp.setOutputTrimDb((float)atof(argv[4]));
    printf("  output trim  %+.1f dB\n", (double)g_dsp.outputTrimDb());
  }

  const uint32_t N = cfg::kDmaFramesPerHalf;
  const uint32_t M = cfg::kMonitorBlockSamples;

  std::vector<int32_t> raw(N * cfg::kChannels);
  std::vector<Frame4> frames(N);
  std::vector<float> left(M), right(M);

  uint64_t in_frames = 0, out_frames = 0;

  for (;;) {
    const size_t got = fread(raw.data(), sizeof(int32_t),
                             raw.size(), fin);
    if (got < raw.size()) break;   // only whole blocks, as the DMA delivers

    for (uint32_t i = 0; i < N; i++) {
      for (uint8_t c = 0; c < cfg::kChannels; c++) {
        frames[i].ch[c] = raw[i * cfg::kChannels + c];
      }
    }
    in_frames += N;

    // Exactly the sequence main.cpp uses, minus the recorder.
    g_dsp.pushCaptureBlock(frames.data(), N);
    g_meters.accumulate(frames.data(), N);
    g_dsp.render(left.data(), right.data(), M);

    for (uint32_t i = 0; i < M; i++) {
      fwrite(&left[i], sizeof(float), 1, fout);
      fwrite(&right[i], sizeof(float), 1, fout);
    }
    out_frames += M;

    // One capture block is one DMA period of virtual time.
    qpr_host::advanceMicros(1000000ull * N / cfg::kSampleRateHz);
  }

  fclose(fin);
  fclose(fout);

  Meters::Reading mr;
  g_meters.read(&mr);

  printf("firmware DSP run\n");
  printf("  in           %llu frames at %lu Hz\n",
         (unsigned long long)in_frames, (unsigned long)cfg::kSampleRateHz);
  printf("  out          %llu frames at %lu Hz\n",
         (unsigned long long)out_frames, (unsigned long)cfg::kMonitorRateHz);
  printf("  hrtf taps    %lu\n", (unsigned long)cfg::kHrtfTaps);
  printf("  dropped      %lu\n", (unsigned long)g_dsp.dropped());
  printf("  starved      %lu\n", (unsigned long)g_dsp.starved());
  printf("  meters       ");
  for (uint8_t c = 0; c < cfg::kChannels; c++) {
    printf("%s %+.1f/%+.1f  ", cfg::kChannelNames[c],
           (double)mr.peak_dbfs[c], (double)mr.rms_dbfs[c]);
  }
  printf("\n");

  if (argc > 3) {
    FILE* fm = fopen(argv[3], "w");
    if (fm) {
      for (uint8_t c = 0; c < cfg::kChannels; c++) {
        fprintf(fm, "%s %.6f %.6f\n", cfg::kChannelNames[c],
                (double)mr.peak_dbfs[c], (double)mr.rms_dbfs[c]);
      }
      fclose(fm);
    }
  }

  if (g_dsp.dropped() != 0) {
    fprintf(stderr, "FAIL: the DSP dropped %lu capture blocks\n",
            (unsigned long)g_dsp.dropped());
    return 1;
  }
  return 0;
}
