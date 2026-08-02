#!/usr/bin/env python3
"""simulate_binaural.py -- hear the monitor path before the hardware exists.

Vendor: Illicit Apothecary
Project: Quad Preamp and Recorder

This runs the *same* decode and HRTF maths the Teensy firmware runs, on your
desktop, at the same sample rates, using the same coefficient generator. If it
sounds wrong here it will sound wrong on the box, and vice versa -- which is
the whole point of having it.

Two ways to use it:

1. SYNTHESISE a test scene. No microphone needed. This is what you want today.

       python3 simulate_binaural.py --scene orbit --out orbit.wav

   Available scenes:
       orbit     a click train circling the listener at ear height
       flyover   a sweep passing overhead front to back
       corners   a voice-band noise burst at each of the four capsule
                 directions in turn, announced by index
       static    four fixed sources at front / left / back / up

2. RENDER four real A-format recordings from the device.

       python3 simulate_binaural.py --input FLU001.WAV FRD001.WAV \\
                                    BLD001.WAV BRU001.WAV --out monitor.wav

   The four files must be the mono WAVs the recorder writes, same length and
   sample rate.

Useful knobs:
    --radius 0.021      your measured capsule radius, in metres
    --taps 256          binaural filter length
    --no-correction     bypass the A-format correction, to hear what it does
    --sofa KEMAR.sofa   render with a measured HRTF set instead of the model
    --report plots.png  write a page of response plots (needs matplotlib)
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

import qpr_ambisonics as qa

CAPTURE_RATE = 192000.0
MONITOR_RATE = 48000.0


# ---------------------------------------------------------------------------
# WAV helpers -- 24-bit mono in, 24-bit stereo out, matching the device
# ---------------------------------------------------------------------------
def read_wav_mono(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1:
            raise ValueError(f"{path}: expected mono, got {w.getnchannels()} channels")
        width = w.getsampwidth()
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())

    if width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        return v.astype(np.float64) / 8388608.0, rate
    if width == 2:
        v = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
        return v, rate
    if width == 4:
        v = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
        return v, rate
    raise ValueError(f"{path}: unsupported sample width {width * 8} bits")


def write_wav_stereo(path: str, left: np.ndarray, right: np.ndarray, rate: int):
    n = min(len(left), len(right))
    inter = np.empty(n * 2, dtype=np.float64)
    inter[0::2] = left[:n]
    inter[1::2] = right[:n]
    inter = np.clip(inter, -1.0, 1.0)
    q = np.round(inter * 8388607.0).astype(np.int32)
    b = np.empty((q.size, 3), dtype=np.uint8)
    b[:, 0] = q & 0xFF
    b[:, 1] = (q >> 8) & 0xFF
    b[:, 2] = (q >> 16) & 0xFF
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(rate)
        w.writeframes(b.tobytes())


# ---------------------------------------------------------------------------
# Test scenes, rendered directly into A-format at the capture rate
# ---------------------------------------------------------------------------
def _pan_into_a_format(mono: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """Ideal coincident cardioid capsules picking up a plane wave."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    gains = 0.5 * (1.0 + qa.CAPSULE_DIRECTIONS @ d)
    return np.outer(gains, mono)  # (4, n)


def _click_train(n: int, rate: float, hz: float = 4.0) -> np.ndarray:
    sig = np.zeros(n)
    period = int(rate / hz)
    burst = int(rate * 0.004)
    t = np.arange(burst) / rate
    env = np.exp(-t * 500.0)
    tone = np.sin(2 * np.pi * 1500.0 * t) * env
    for start in range(0, n - burst, period):
        sig[start : start + burst] += tone
    return sig * 0.5


def _noise_burst(n: int, rate: float) -> np.ndarray:
    rng = np.random.default_rng(0xC0FFEE)
    sig = rng.standard_normal(n)
    # Band-limit it to something speech-like so direction is easy to hear.
    spec = np.fft.rfft(sig)
    f = np.fft.rfftfreq(n, 1.0 / rate)
    spec[(f < 200.0) | (f > 6000.0)] = 0.0
    sig = np.fft.irfft(spec, n=n)
    env = np.minimum(1.0, np.arange(n) / (0.01 * rate))
    env *= np.minimum(1.0, (n - np.arange(n)) / (0.05 * rate))
    sig = sig / (np.max(np.abs(sig)) + 1e-12)
    return sig * env * 0.4


def build_scene(name: str, seconds: float, rate: float) -> tuple[np.ndarray, str]:
    n = int(seconds * rate)
    a = np.zeros((4, n))

    if name == "orbit":
        src = _click_train(n, rate)
        turns = 2.0
        az = np.linspace(0.0, 360.0 * turns, n)
        for i_chunk in range(0, n, 256):
            j = slice(i_chunk, min(i_chunk + 256, n))
            d = qa.spherical_to_cartesian(az[i_chunk], 0.0)
            a[:, j] += _pan_into_a_format(src[j], d)
        desc = ("a click train orbiting the listener twice at ear height, "
                "starting straight ahead and moving to your LEFT first")

    elif name == "flyover":
        src = _click_train(n, rate, hz=6.0)
        el = np.concatenate([np.linspace(-10, 90, n // 2),
                             np.linspace(90, -10, n - n // 2)])
        az = np.concatenate([np.zeros(n // 2), np.full(n - n // 2, 180.0)])
        for i_chunk in range(0, n, 256):
            j = slice(i_chunk, min(i_chunk + 256, n))
            d = qa.spherical_to_cartesian(az[i_chunk], el[i_chunk])
            a[:, j] += _pan_into_a_format(src[j], d)
        desc = "a source rising from in front, passing overhead, descending behind"

    elif name == "corners":
        seg = n // 4
        for k, d in enumerate(qa.CAPSULE_DIRECTIONS):
            j = slice(k * seg, (k + 1) * seg)
            a[:, j] += _pan_into_a_format(_noise_burst(seg, rate), d)
        desc = ("one noise burst per capsule direction in order "
                + ", ".join(qa.CAPSULE_NAMES))

    elif name == "static":
        seg = n // 4
        places = [(0, 0, "front"), (90, 0, "left"), (180, 0, "behind"), (0, 90, "above")]
        for k, (az, el, _) in enumerate(places):
            j = slice(k * seg, (k + 1) * seg)
            a[:, j] += _pan_into_a_format(_noise_burst(seg, rate),
                                          qa.spherical_to_cartesian(az, el))
        desc = "noise bursts at front, left, behind, above -- in that order"

    else:
        raise ValueError(f"unknown scene '{name}'")

    return a, desc


# ---------------------------------------------------------------------------
# The monitor chain, step for step as the firmware runs it
# ---------------------------------------------------------------------------
def run_monitor_chain(
    a_format: np.ndarray,
    capture_rate: float,
    monitor_rate: float,
    binaural: np.ndarray,
    decim: np.ndarray,
    limiter_threshold_db: float = -1.0,
    output_trim_db: float = 0.0,
    limiter_dtype=np.float64,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """a_format is (4, n) at capture_rate. Returns (left, right, stats)."""
    decimation = int(round(capture_rate / monitor_rate))

    # 1. Anti-alias low-pass and decimate, per capsule.
    # CAUSAL, exactly as the firmware does it: out[j] = sum_k h[k] * x[j*M - k].
    # Not mode="same" -- that centres the filter and would shift this model by
    # half the filter length relative to the firmware, which would make
    # test/host/compare_firmware_to_model.py fail for no real reason.
    n_in = a_format.shape[1]
    dec = np.stack(
        [np.convolve(a_format[c], decim)[:n_in][::decimation] for c in range(4)]
    )

    # 2. A-format to B-format.
    b = qa.a_to_b_matrix() @ dec  # (4, n/decimation), order W X Y Z

    # 3. Eight convolutions: each B-format channel into each ear.
    n_out = b.shape[1]
    left = np.zeros(n_out)
    right = np.zeros(n_out)
    for ch in range(4):
        left += np.convolve(b[ch], binaural[ch, 0])[:n_out]
        right += np.convolve(b[ch], binaural[ch, 1])[:n_out]

    pre_peak = float(max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12))
    del pre_peak  # recomputed below, after the trim, to match the firmware

    # 4. Output trim, then the limiter. Order matters and matches the
    #    firmware exactly: the trim is applied FIRST, and the envelope
    #    detector sees the trimmed signal. Detecting on the untrimmed signal
    #    would make the limiter stop protecting the DAC as soon as you turned
    #    the trim up.
    trim = 10.0 ** (output_trim_db / 20.0)
    left = left * trim
    right = right * trim

    # Same formulation as the firmware: env += a * (peak - env), with `a`
    # obtained from expm1 so the small quantity keeps its precision.
    # limiter_dtype=np.float32 reproduces the firmware's arithmetic exactly,
    # which is what test/host/compare_firmware_to_model.py uses.
    dt = limiter_dtype
    thresh = dt(10.0 ** (limiter_threshold_db / 20.0))
    a_atk = dt(-np.expm1(-1.0 / (0.001 * monitor_rate)))
    a_rel = dt(-np.expm1(-1.0 / (0.120 * monitor_rate)))
    one = dt(1.0)
    lv = left.astype(dt)
    rv = right.astype(dt)
    env = dt(0.0)
    gain = np.ones(n_out, dtype=dt)
    for i in range(n_out):
        peak = max(abs(lv[i]), abs(rv[i]))
        a = a_atk if peak > env else a_rel
        env = env + a * (peak - env)
        gain[i] = (thresh / env) if env > thresh else one
    left = lv.astype(np.float64)
    right = rv.astype(np.float64)
    gain = gain.astype(np.float64)
    left = np.clip(left * gain, -1.0, 1.0)
    right = np.clip(right * gain, -1.0, 1.0)

    stats = {
        "peak_before_limiter_db": 20 * np.log10(
            max(float(np.max(np.abs(left / np.maximum(gain, 1e-30)))), 1e-12)),
        "peak_after_limiter_db": 20 * np.log10(
            max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12)
        ),
        "limiter_min_gain_db": 20 * np.log10(max(float(np.min(gain)), 1e-12)),
        "output_samples": n_out,
    }
    return left, right, stats


def write_report(path: Path, binaural: np.ndarray, decim: np.ndarray, rate: float):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  ! matplotlib is not installed, skipping the report "
              "(pip install matplotlib)", file=sys.stderr)
        return

    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    names = ["W", "X", "Y", "Z"]

    for ch in range(4):
        ax[0, 0].plot(binaural[ch, 0], lw=0.8, label=f"{names[ch]} left")
    ax[0, 0].set_title("Binaural FIR impulse responses (left ear)")
    ax[0, 0].set_xlabel("tap")
    ax[0, 0].legend(fontsize=7)

    n_fft = 8192
    f = np.fft.rfftfreq(n_fft, 1.0 / rate)
    for ch in range(4):
        mag = np.abs(np.fft.rfft(binaural[ch, 0], n_fft))
        ax[0, 1].semilogx(f[1:], 20 * np.log10(mag[1:] + 1e-12), lw=0.9,
                          label=names[ch])
    ax[0, 1].set_title("Binaural filter magnitude, left ear")
    ax[0, 1].set_xlabel("Hz")
    ax[0, 1].set_ylabel("dB")
    ax[0, 1].set_xlim(20, rate / 2)
    ax[0, 1].grid(True, which="both", alpha=0.3)
    ax[0, 1].legend(fontsize=8)

    ax[1, 0].plot(decim, lw=0.8)
    ax[1, 0].set_title("Decimator impulse response")
    ax[1, 0].set_xlabel("tap")

    n_fft2 = 32768
    f2 = np.fft.rfftfreq(n_fft2, 1.0 / CAPTURE_RATE)
    mag2 = np.abs(np.fft.rfft(decim, n_fft2))
    ax[1, 1].plot(f2 / 1000.0, 20 * np.log10(mag2 + 1e-12), lw=0.9)
    ax[1, 1].axvline(24.0, color="r", ls="--", lw=0.8, label="new Nyquist")
    ax[1, 1].axvline(28.0, color="orange", ls="--", lw=0.8,
                     label="fold-back into 20 kHz")
    ax[1, 1].set_title("Decimator magnitude at the capture rate")
    ax[1, 1].set_xlabel("kHz")
    ax[1, 1].set_ylabel("dB")
    ax[1, 1].set_ylim(-140, 10)
    ax[1, 1].set_xlim(0, 96)
    ax[1, 1].grid(alpha=0.3)
    ax[1, 1].legend(fontsize=8)

    fig.suptitle("QuadPreRecorder monitor path -- Illicit Apothecary")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    print(f"  wrote {path}")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--scene", default="orbit",
                   choices=["orbit", "flyover", "corners", "static"])
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--input", nargs=4, metavar=("FLU", "FRD", "BLD", "BRU"),
                   help="four mono A-format WAV files from the recorder")
    p.add_argument("--out", default="monitor.wav")
    p.add_argument("--taps", type=int, default=128,
                   help="binaural FIR length; must match the firmware build")
    p.add_argument("--radius", type=float, default=0.015)
    p.add_argument("--basic", action="store_true")
    p.add_argument("--no-correction", action="store_true")
    p.add_argument("--sofa", type=str, default=None)
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args()

    print("qpr binaural monitor simulator")
    if not qa.self_test(verbose=False):
        print("  ! shared maths self-test FAILED")
        qa.self_test(verbose=True)
        return 1

    provider = None
    if args.sofa:
        import build_hrtf
        provider = build_hrtf.make_sofa_provider(args.sofa)

    if args.input:
        chans = []
        rate = None
        for path in args.input:
            sig, r = read_wav_mono(path)
            if rate is None:
                rate = r
            elif r != rate:
                print(f"  ! {path} is {r} Hz but the first file is {rate} Hz")
                return 1
            chans.append(sig)
        n = min(len(c) for c in chans)
        a_format = np.stack([c[:n] for c in chans])
        capture_rate = float(rate)
        desc = f"four recorded channels, {n / capture_rate:.2f} s at {rate} Hz"
    else:
        capture_rate = CAPTURE_RATE
        a_format, desc = build_scene(args.scene, args.seconds, capture_rate)

    decimation = int(round(capture_rate / MONITOR_RATE))
    if decimation < 1:
        print(f"  ! capture rate {capture_rate} is below the monitor rate")
        return 1

    print(f"  source: {desc}")
    print(f"  capture {capture_rate:.0f} Hz -> monitor {MONITOR_RATE:.0f} Hz "
          f"(decimate by {decimation})")

    binaural = qa.build_binaural_filters(
        n_taps=args.taps,
        sample_rate=MONITOR_RATE,
        capsule_radius=args.radius,
        hrir_provider=provider,
        max_re=not args.basic,
        apply_a_format_correction=not args.no_correction,
    )
    decim = qa.design_decimation_fir(qa.DECIMATOR_TAPS, decimation, capture_rate)

    left, right, stats = run_monitor_chain(
        a_format, capture_rate, MONITOR_RATE, binaural, decim
    )

    write_wav_stereo(args.out, left, right, int(MONITOR_RATE))
    print(f"  wrote {args.out}  ({stats['output_samples']} frames, "
          f"{stats['output_samples'] / MONITOR_RATE:.2f} s)")
    print(f"  peak before limiter : {stats['peak_before_limiter_db']:+.2f} dBFS")
    print(f"  peak after limiter  : {stats['peak_after_limiter_db']:+.2f} dBFS")
    print(f"  most limiting applied: {stats['limiter_min_gain_db']:+.2f} dB")

    if args.report:
        write_report(args.report, binaural, decim, MONITOR_RATE)

    print("  listen on headphones, not speakers -- this is a binaural render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
