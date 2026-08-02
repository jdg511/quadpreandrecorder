#!/usr/bin/env bash
# run_tests.sh — the whole host test suite in one command
#
# Vendor: Illicit Apothecary
#
#   cd test/host && make test
#
# What this proves, without any hardware:
#   1. The real qpr_dsp.cpp produces the same audio as the Python model you
#      tune by ear. Both linear and in limiting.
#   2. The real qpr_recorder.cpp keeps four files sample-aligned through a
#      microSD stall, and drops audio collectively when it has to.
#   3. The WAV files it writes are valid and open in ordinary tools.
#
# What it CANNOT prove: anything electrical. SAI, eDMA, I2C, the display and
# the analog path all need the board. See docs/BRINGUP.md.

set -u
cd "$(dirname "$0")"

FAIL=0
step() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }
result() {
  if [ "$1" -eq 0 ]; then printf '  --> PASS\n'; else printf '  --> FAIL\n'; FAIL=1; fi
}

step "1/4  build"
make -s all
result $?

step "2/4  monitor DSP: firmware vs model"
python3 compare_firmware_to_model.py
result $?

step "3/4  recorder: four streams through a simulated card stall"
rm -rf /tmp/qpr_sd
./build/test_recorder /tmp/qpr_sd
result $?

step "4/4  the WAV files the recorder just wrote"
if command -v ffprobe >/dev/null 2>&1; then
  BAD=0
  for f in /tmp/qpr_sd/*.WAV; do
    [ -e "$f" ] || continue
    INFO=$(ffprobe -v error -show_entries stream=codec_name,sample_rate,channels,duration \
                   -of default=nw=1:nk=1 "$f" 2>&1)
    if [ $? -ne 0 ]; then
      printf '  %-18s UNREADABLE\n' "$(basename "$f")"
      BAD=1
      continue
    fi
    printf '  %-18s %s\n' "$(basename "$f")" "$(echo "$INFO" | tr '\n' ' ')"
    echo "$INFO" | grep -q '^pcm_s24le$' || BAD=1
  done
  result $BAD
else
  printf '  ffprobe not installed, skipping (install ffmpeg for this check)\n'
  printf '  --> SKIPPED\n'
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then
  printf '\033[1mALL HOST TESTS PASSED\033[0m\n'
  printf 'The DSP and the recorder behave correctly. Everything electrical\n'
  printf 'still needs the board -- run bringup/ t01..t06 before trusting it.\n'
else
  printf '\033[1mSOME HOST TESTS FAILED\033[0m\n'
fi
exit "$FAIL"
