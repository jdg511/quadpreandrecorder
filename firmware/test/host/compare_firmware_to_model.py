#!/usr/bin/env python3
"""compare_firmware_to_model.py -- prove the firmware DSP and the Python model
are the same filter.

Vendor: Illicit Apothecary
Project: Quad Preamp and Recorder

The whole premise of sim/simulate_binaural.py is that tuning the monitor on a
laptop is meaningful because the Teensy runs the same maths. This is the test
that makes that a fact rather than a hope.

  1. Build a four-channel A-format test signal in Python.
  2. Quantise it to 24-bit -- exactly what the ADC delivers.
  3. Run it through build/test_dsp, which links the REAL qpr_dsp.cpp.
  4. Run the identical samples through the Python model.
  5. Compare, sample for sample.

If they diverge by more than float32 rounding, one of them is wrong, and the
listening you did on the desktop does not describe the box.

Usage:
    make            # in test/host, to build build/test_dsp
    python3 compare_firmware_to_model.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SIM = HERE.parent.parent / "sim"
sys.path.insert(0, str(SIM))

import qpr_ambisonics as qa          # noqa: E402
import simulate_binaural as sb       # noqa: E402

CAPTURE_RATE = 192000.0
MONITOR_RATE = 48000.0
BLOCK_IN = 256          # cfg::kDmaFramesPerHalf
BLOCK_OUT = 64          # cfg::kMonitorBlockSamples

# The firmware is float32 throughout. The model runs its limiter in float32
# too for this comparison, so the two are doing identical arithmetic and the
# only remaining difference is rounding inside the FIR accumulators, which the
# model still does in float64. Measured worst case is around 5e-7.
#
# The float64 limiter is ALSO reported, as information: the gap between the
# two is a direct measure of how much single precision costs in the recursive
# envelope follower, and it is the number that would grow if someone set a
# much longer release time.
ABS_TOL = 5e-6


def read_taps_from_coeffs() -> int:
    header = HERE.parent.parent / "lib" / "qpr_dsp" / "qpr_coeffs.h"
    for line in header.read_text().splitlines():
        if "kHrtfTaps" in line and "constexpr" in line:
            return int(line.split("=")[1].strip().rstrip(";"))
    raise RuntimeError("could not read kHrtfTaps from qpr_coeffs.h")


def build_test_signal(seconds: float) -> np.ndarray:
    """A-format that exercises every direction and both extremes of level."""
    n = int(seconds * CAPTURE_RATE)
    a = np.zeros((4, n))

    third = n // 3

    # 1. A source orbiting the listener: moves energy between all four capsules.
    src = sb._click_train(third, CAPTURE_RATE)
    az = np.linspace(0.0, 720.0, third)
    for i in range(0, third, 256):
        j = slice(i, min(i + 256, third))
        d = qa.spherical_to_cartesian(az[i], 30.0 * np.sin(i / third * 6.28))
        a[:, j] += sb._pan_into_a_format(src[j], d)

    # 2. Broadband noise from a fixed direction, loud enough to make the
    #    limiter work -- the limiter has state, so it is the part most likely
    #    to drift between two implementations.
    burst = sb._noise_burst(third, CAPTURE_RATE) * 2.2
    a[:, third:2 * third] += sb._pan_into_a_format(
        burst, qa.spherical_to_cartesian(-60.0, -20.0))

    # 3. Near silence, to check the two agree on the way back down out of
    #    limiting and on denormal-scale values.
    quiet = sb._noise_burst(n - 2 * third, CAPTURE_RATE) * 1e-4
    a[:, 2 * third:] += sb._pan_into_a_format(
        quiet, qa.spherical_to_cartesian(0.0, 90.0))

    return a


def quantise_24bit(a: np.ndarray) -> np.ndarray:
    """Exactly what arrives from the PCM1864: signed 24-bit integers."""
    q = np.clip(np.round(a * 8388607.0), -8388608, 8388607)
    return q.astype(np.int32)


def run_case(exe: Path, taps: int, a_int: np.ndarray, trim_db: float) -> bool:
    """One comparison at a given output trim. Returns True on agreement."""
    print(f"\n=== case: output trim {trim_db:+.0f} dB ===")
    # --- run the firmware ---------------------------------------------------
    raw_in = HERE / "build" / "equiv_in.raw"
    raw_out = HERE / "build" / "equiv_out.f32"
    a_int.T.astype("<i4").tofile(raw_in)

    proc = subprocess.run(
        [str(exe), str(raw_in), str(raw_out), str(HERE / "build" / "m.txt"),
         str(trim_db)],
        capture_output=True, text=True)
    print("  --- firmware ---")
    for line in proc.stdout.strip().splitlines():
        print(f"  {line}")
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return False

    fw = np.fromfile(raw_out, dtype="<f4").reshape(-1, 2).astype(np.float64)
    fw_l, fw_r = fw[:, 0], fw[:, 1]

    # --- run the model on the SAME quantised samples ------------------------
    a_model = a_int.astype(np.float64) / 8388608.0
    binaural = qa.build_binaural_filters(
        n_taps=taps, sample_rate=MONITOR_RATE,
        capsule_radius=0.015, max_re=True, apply_a_format_correction=True)
    decim = qa.design_decimation_fir(qa.DECIMATOR_TAPS, 4, CAPTURE_RATE)
    md_l, md_r, stats = sb.run_monitor_chain(
        a_model, CAPTURE_RATE, MONITOR_RATE, binaural, decim,
        output_trim_db=trim_db, limiter_dtype=np.float32)
    d64_l, d64_r, _ = sb.run_monitor_chain(
        a_model, CAPTURE_RATE, MONITOR_RATE, binaural, decim,
        output_trim_db=trim_db, limiter_dtype=np.float64)

    n = min(len(fw_l), len(md_l))
    print("  --- model ---")
    print(f"  out {len(md_l)} frames, peak before limiter "
          f"{stats['peak_before_limiter_db']:+.2f} dBFS, "
          f"limiting {stats['limiter_min_gain_db']:+.2f} dB")

    if n == 0:
        print("! no overlapping output to compare", file=sys.stderr)
        return False

    dl = np.abs(fw_l[:n] - md_l[:n])
    dr = np.abs(fw_r[:n] - md_r[:n])
    worst = float(max(dl.max(), dr.max()))
    where = int(np.argmax(np.maximum(dl, dr)))
    rms_ref = float(np.sqrt(np.mean(md_l[:n] ** 2 + md_r[:n] ** 2)))
    rms_err = float(np.sqrt(np.mean(dl ** 2 + dr ** 2)))

    n64 = min(n, len(d64_l))
    prec = float(np.abs(md_l[:n64] - d64_l[:n64]).max())

    print("  --- comparison ---")
    print(f"  compared           {n} stereo frames")
    print(f"  f32-vs-f64 limiter {prec:.3e}  (cost of single precision)")
    print(f"  worst difference   {worst:.3e}  at sample {where}")
    print(f"  error / signal     {rms_err / max(rms_ref, 1e-30):.3e} rms")
    print(f"  tolerance          {ABS_TOL:.1e}")

    # Correlation is the check that catches a delay or ordering mistake, which
    # a small absolute difference would not.
    if np.std(fw_l[:n]) > 1e-12 and np.std(md_l[:n]) > 1e-12:
        corr = float(np.corrcoef(fw_l[:n], md_l[:n])[0, 1])
        print(f"  correlation (L)    {corr:.9f}")
    else:
        corr = 1.0

    ok = worst <= ABS_TOL and corr > 0.999999
    print(f"\n  {'PASS' if ok else 'FAIL'}: the firmware DSP and the Python "
          f"model {'agree' if ok else 'DISAGREE'}")
    if not ok:
        lo = max(0, where - 3)
        hi = min(n, where + 4)
        print("\n  around the worst sample:")
        print("     idx        firmware            model         diff")
        for i in range(lo, hi):
            print(f"    {i:6d}  {fw_l[i]:+.9f}  {md_l[i]:+.9f}  "
                  f"{fw_l[i] - md_l[i]:+.3e}")
    return ok


def main() -> int:
    exe = HERE / "build" / "test_dsp"
    if not exe.exists():
        print(f"! {exe} not built. Run `make` in {HERE} first.", file=sys.stderr)
        return 2

    taps = read_taps_from_coeffs()
    print("firmware / model equivalence check")
    print(f"  binaural taps      {taps}")
    print(f"  decimator taps     {qa.DECIMATOR_TAPS}")

    a_float = build_test_signal(3.0)
    a_int = quantise_24bit(a_float)
    n_blocks = a_int.shape[1] // BLOCK_IN
    a_int = a_int[:, : n_blocks * BLOCK_IN]
    print(f"  test signal        {a_int.shape[1]} frames "
          f"({a_int.shape[1] / CAPTURE_RATE:.2f} s, {n_blocks} blocks)")

    # 0 dB: the linear path. +12 dB: drives the signal well past the -1 dBFS
    # ceiling so the limiter's attack, hold and release all get exercised.
    ok = True
    for trim in (0.0, 12.0):
        ok &= run_case(exe, taps, a_int, trim)

    print(f"\n{'ALL PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
