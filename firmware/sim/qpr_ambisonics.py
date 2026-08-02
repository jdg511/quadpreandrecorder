"""qpr_ambisonics.py -- the monitor-path maths, shared by the simulator and the
firmware coefficient generator.

Vendor: Illicit Apothecary
Project: Quad Preamp and Recorder

This module is the single source of truth for the A-format-to-binaural chain.
The firmware does not reimplement any of it: build_hrtf.py runs the code here
and emits the resulting FIR tables as a C header, so what you audition in
simulate_binaural.py is bit-for-bit the same filter set the Teensy convolves.

Conventions used throughout
---------------------------
Coordinates: right-handed, x = forward, y = left, z = up (the ambisonic
convention, not the graphics one).

Azimuth is measured counter-clockwise from front, so +90 deg is the listener's
LEFT. Elevation is positive upward.

B-format is stored in the order [W, X, Y, Z] with SN3D normalisation, i.e. a
mono source of amplitude s at unit direction d encodes to
    W = s, X = s*d_x, Y = s*d_y, Z = s*d_z.
(ACN channel ordering would be W, Y, Z, X. We keep W, X, Y, Z because it reads
better next to the capsule names; convert if you export to a SOFA/AmbiX tool.)
"""

from __future__ import annotations

import numpy as np

SPEED_OF_SOUND = 343.0  # m/s at 20 C

# Length of the capture-rate anti-alias filter used by the decimator. Must
# match cfg::kDecimatorTaps in the firmware; build_hrtf.py emits it so the two
# can never drift apart.
DECIMATOR_TAPS = 192

# ---------------------------------------------------------------------------
# Capsule geometry
# ---------------------------------------------------------------------------
# The four capsules of a vertical tetrahedron. Names match the recorded files
# and the PCM1864 input order fixed by the PCB:
#   FLU -> VINL1 -> ADC1 L -> DOUT  left  slot
#   FRD -> VINR1 -> ADC1 R -> DOUT  right slot
#   BLD -> VINL2 -> ADC2 L -> DOUT2 left  slot
#   BRU -> VINR2 -> ADC2 R -> DOUT2 right slot
CAPSULE_NAMES = ("FLU", "FRD", "BLD", "BRU")

_S = 1.0 / np.sqrt(3.0)
CAPSULE_DIRECTIONS = np.array(
    [
        [+_S, +_S, +_S],  # FLU  front left  up
        [+_S, -_S, -_S],  # FRD  front right down
        [-_S, +_S, -_S],  # BLD  back  left  down
        [-_S, -_S, +_S],  # BRU  back  right up
    ]
)


def a_to_b_matrix() -> np.ndarray:
    """4x4 matrix mapping [FLU, FRD, BLD, BRU] to [W, X, Y, Z].

    Derived directly from CAPSULE_DIRECTIONS rather than hard-coded, so if you
    ever change the capsule layout the matrix follows.

    Row W is the mean of the capsules (the pressure component). Rows X/Y/Z
    project the capsule signals onto each axis and are scaled so that a plane
    wave arriving along an axis produces the SN3D-correct component amplitude.
    """
    d = CAPSULE_DIRECTIONS
    n = d.shape[0]
    m = np.zeros((4, n))
    m[0, :] = 1.0 / n                       # W
    m[1:4, :] = d.T * (3.0 / n)             # X, Y, Z
    return m


def encode_source(direction: np.ndarray, gain: float = 1.0) -> np.ndarray:
    """SN3D first-order encoding gains [W, X, Y, Z] for a unit direction."""
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)
    return gain * np.array([1.0, d[0], d[1], d[2]])


def spherical_to_cartesian(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    az = np.radians(azimuth_deg)
    el = np.radians(elevation_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


# ---------------------------------------------------------------------------
# A-format correction
# ---------------------------------------------------------------------------
def a_format_correction(
    n_fft: int,
    sample_rate: float,
    capsule_radius: float,
    lf_shelf_hz: float = 80.0,
    max_boost_db: float = 18.0,
):
    """Complex frequency responses (W_resp, V_resp) correcting the A-to-B stage.

    A tetrahedral array of finite size under-represents the velocity
    components (X/Y/Z) at low frequency, because the capsules are too close
    together to resolve a pressure gradient there. The textbook correction is a
    +6 dB/octave boost below the array's transition frequency

        f_t = c / (2*pi*r)

    which for a 15 mm array is about 3.6 kHz. Left unbounded that boost
    explodes at DC, so it is floored below `lf_shelf_hz` and hard-limited to
    `max_boost_db`. Those two numbers are the difference between a usable
    monitor and a rumbling mess; they are the first thing to tune against a
    real measurement.

    The pressure component W gets the complementary (very gentle) treatment so
    that the W/XYZ balance stays flat through the transition region.

    THIS IS A MODEL, NOT A MEASUREMENT. Real capsules have their own response,
    the enclosure diffracts, and the array is never perfectly symmetric.
    Measure your microphone and replace this function's output with the
    measured correction when you can.
    """
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    f_t = SPEED_OF_SOUND / (2.0 * np.pi * capsule_radius)

    with np.errstate(divide="ignore", invalid="ignore"):
        # First-order high-pass-shaped deficit; the correction is its inverse.
        f_eff = np.maximum(freqs, lf_shelf_hz)
        boost = np.sqrt(1.0 + (f_t / f_eff) ** 2)

    max_lin = 10.0 ** (max_boost_db / 20.0)
    boost = np.minimum(boost, max_lin)
    boost[0] = boost[1] if len(boost) > 1 else 1.0

    # Normalise so the correction is unity gain at 1 kHz -- otherwise changing
    # the radius silently changes the monitor level.
    ref = np.interp(1000.0, freqs, boost)
    v_resp = (boost / ref).astype(complex)
    w_resp = np.ones_like(v_resp)
    return w_resp, v_resp


# ---------------------------------------------------------------------------
# Analytic HRTF: Brown & Duda spherical head, plus pinna and torso terms
# ---------------------------------------------------------------------------
HEAD_RADIUS = 0.0875  # m, the usual anthropometric average


def _brown_duda_shadow(theta: np.ndarray, freqs: np.ndarray, a: float) -> np.ndarray:
    """Head-shadow transfer function, Brown & Duda (1998) one-pole/one-zero.

        H(s) = (alpha*s/w0 + 1) / (s/w0 + 1),  w0 = c/a

    theta is the angle in radians between the source direction and the ear
    direction: 0 = source straight at that ear, pi = directly opposite.
    """
    alpha_min = 0.1
    theta_min = np.radians(150.0)
    alpha = (1.0 + alpha_min / 2.0) + (1.0 - alpha_min / 2.0) * np.cos(
        theta / theta_min * np.pi
    )
    w0 = SPEED_OF_SOUND / a
    s = 2j * np.pi * freqs
    return (alpha * s / w0 + 1.0) / (s / w0 + 1.0)


def _woodworth_itd(theta: float, a: float) -> float:
    """Propagation delay to one ear, seconds, relative to the head centre."""
    t = abs(theta)
    if t < np.pi / 2.0:
        return -(a / SPEED_OF_SOUND) * np.cos(t)
    return (a / SPEED_OF_SOUND) * (t - np.pi / 2.0)


def analytic_hrir(
    direction: np.ndarray,
    n_taps: int,
    sample_rate: float,
    head_radius: float = HEAD_RADIUS,
    pinna_gain: float = -0.35,
    torso_gain: float = 0.18,
    rear_shelf_db: float = -5.0,
) -> np.ndarray:
    """(2, n_taps) left/right impulse responses for one source direction.

    Components, in the order they matter perceptually:
      1. Interaural time difference (Woodworth), applied as a fractional delay.
      2. Head shadow (Brown & Duda one-pole/one-zero).
      3. A single pinna reflection whose delay depends on elevation. This is
         what gives the model any front/back and up/down cue at all; it is a
         crude stand-in for the real pinna's several notches.
      4. A pinna high-frequency shelf that dims sources from behind, which is
         the only reason a first-order render has any front/back cue at all.
      5. A shoulder/torso reflection about 1 ms out, which adds a little
         low-frequency comb that helps externalisation.

    An analytic model cannot match a measured individual HRTF. It is here so
    the monitor works out of the box and so the simulator and firmware agree.
    Load a measured set (see build_hrtf.py --measured) when you have one.
    """
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)
    n_fft = max(1024, 4 * n_taps)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)

    ear_dirs = {"left": np.array([0.0, 1.0, 0.0]), "right": np.array([0.0, -1.0, 0.0])}
    elevation = np.arcsin(np.clip(d[2], -1.0, 1.0))

    out = np.zeros((2, n_taps))
    for idx, ear in enumerate(("left", "right")):
        theta = np.arccos(np.clip(np.dot(d, ear_dirs[ear]), -1.0, 1.0))

        h = _brown_duda_shadow(np.full_like(freqs, theta), freqs, head_radius)

        # Fractional delay. A common offset keeps the whole response inside the
        # window; only the difference between the ears is perceptually real.
        delay = _woodworth_itd(theta, head_radius) + head_radius / SPEED_OF_SOUND
        h = h * np.exp(-2j * np.pi * freqs * delay)

        # Pinna reflection. The delay depends on elevation AND on how far
        # forward the source is, so the resulting notch moves with both. The
        # front/back dependence matters: without it a first-order render is
        # exactly front/back symmetric and the monitor gives you no cue at all
        # about whether something is ahead or behind.
        frontness = float(d[0])  # +1 dead ahead, -1 dead behind
        pinna_delay = 0.5 * (
            0.00012
            + 0.00022 * (1.0 - np.sin(elevation))
            + 0.00008 * (1.0 - frontness)
        )
        h = h * (1.0 + pinna_gain * np.exp(-2j * np.pi * freqs * pinna_delay))

        # Pinna shadowing: the outer ear faces forward, so sources behind lose
        # high frequency. A first-order shelf from about 4 kHz, reaching
        # `rear_shelf_db` for a source directly astern. This is the other half
        # of the front/back cue.
        shelf_db = rear_shelf_db * 0.5 * (1.0 - frontness)
        shelf_lin = 10.0 ** (shelf_db / 20.0)
        f_shelf = 4000.0
        s_n = 1j * freqs / f_shelf
        h = h * ((1.0 + shelf_lin * s_n) / (1.0 + s_n))

        # Torso reflection, stronger for sources below the horizon.
        torso_delay = 0.0011 + 0.0003 * np.sin(elevation)
        strength = torso_gain * (0.6 + 0.4 * (1.0 - np.sin(elevation)))
        h = h * (1.0 + strength * np.exp(-2j * np.pi * freqs * torso_delay))

        ir = np.fft.irfft(h, n=n_fft)
        out[idx] = ir[:n_taps]

    return out


# ---------------------------------------------------------------------------
# Virtual loudspeaker array and decoder
# ---------------------------------------------------------------------------
def cube_speaker_layout() -> np.ndarray:
    """Eight virtual loudspeakers on the vertices of a cube.

    A cube is a spherical 2-design: sum(u) = 0 and sum(u u^T) = (N/3) I, which
    is exactly what makes the projection decoder below exact for first order.
    """
    dirs = []
    for sx in (+1, -1):
        for sy in (+1, -1):
            for sz in (+1, -1):
                dirs.append([sx, sy, sz])
    d = np.array(dirs, dtype=float)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def decode_matrix(speakers: np.ndarray, max_re: bool = True) -> np.ndarray:
    """(n_speakers, 4) gains mapping [W, X, Y, Z] to speaker feeds.

    Projection decoder:  g_s = (1/N) * (W + 3*g1*(u_s . [X, Y, Z]))

    With a uniform layout this reproduces the encoded pressure exactly
    (sum of gains = W, because sum(u_s) = 0) and the encoded velocity scaled
    by g1 (because sum(u_s u_s^T) = (N/3) I).

    max_re=True applies the standard first-order 3D max-rE weight g1 = 0.775,
    which trades a little localisation sharpness for a much more stable image
    off-centre -- the right trade for headphone monitoring.
    """
    n = speakers.shape[0]
    g1 = 0.775 if max_re else 1.0
    m = np.zeros((n, 4))
    m[:, 0] = 1.0 / n
    m[:, 1:4] = speakers * (3.0 * g1 / n)
    return m


# ---------------------------------------------------------------------------
# The deliverable: 4 B-format channels x 2 ears of FIR
# ---------------------------------------------------------------------------
def build_binaural_filters(
    n_taps: int,
    sample_rate: float,
    capsule_radius: float,
    hrir_provider=None,
    speakers: np.ndarray | None = None,
    max_re: bool = True,
    apply_a_format_correction: bool = True,
) -> np.ndarray:
    """Return an (4, 2, n_taps) float array: filters[bformat_channel][ear].

    The monitor path in the firmware is then simply

        for ch in W, X, Y, Z:
            left  += fir(bformat[ch], filters[ch][0])
            right += fir(bformat[ch], filters[ch][1])

    which is eight convolutions per output sample regardless of how many
    virtual loudspeakers went into the design.

    hrir_provider(direction, n_taps, sample_rate) -> (2, n_taps).
    Defaults to the analytic model; pass a lookup into a measured set to use
    real data.
    """
    if hrir_provider is None:
        hrir_provider = analytic_hrir
    if speakers is None:
        speakers = cube_speaker_layout()

    decode = decode_matrix(speakers, max_re=max_re)
    filters = np.zeros((4, 2, n_taps))

    for s in range(speakers.shape[0]):
        hrir = hrir_provider(speakers[s], n_taps, sample_rate)
        for ch in range(4):
            g = decode[s, ch]
            if g == 0.0:
                continue
            filters[ch, 0] += g * hrir[0]
            filters[ch, 1] += g * hrir[1]

    if apply_a_format_correction:
        n_fft = 4 * n_taps
        w_resp, v_resp = a_format_correction(n_fft, sample_rate, capsule_radius)
        for ch in range(4):
            resp = w_resp if ch == 0 else v_resp
            for ear in range(2):
                spec = np.fft.rfft(filters[ch, ear], n=n_fft) * resp
                ir = np.fft.irfft(spec, n=n_fft)
                # The correction is minimum-phase-ish and mostly low frequency,
                # so energy stays near the front of the window; take the first
                # n_taps and window the tail to avoid a hard truncation click.
                ir = ir[:n_taps]
                fade = np.ones(n_taps)
                tail = max(8, n_taps // 8)
                fade[-tail:] = np.hanning(2 * tail)[tail:]
                filters[ch, ear] = ir * fade

    return filters


def design_decimation_fir(
    n_taps: int, decimation: int, sample_rate_in: float, cutoff_hz: float | None = None
) -> np.ndarray:
    """Anti-alias low-pass for the capture-rate to monitor-rate decimator.

    Windowed sinc, Blackman window, unity DC gain.

    Design target: what matters is not attenuation exactly at the new Nyquist
    (24 kHz content folds back to 24 kHz, which nobody can hear) but
    attenuation above it. Decimating 192 kHz to 48 kHz folds a component at
    24 + f down to 24 - f, so energy at 28 kHz lands at 20 kHz and energy at
    44 kHz lands at 4 kHz -- squarely audible. The filter therefore aims for
    deep attenuation from about 28 kHz upward and accepts a soft shoulder
    between 20 and 28 kHz.
    """
    fs_out = sample_rate_in / decimation
    if cutoff_hz is None:
        cutoff_hz = min(20000.0, 0.83 * (fs_out / 2.0))

    n = np.arange(n_taps) - (n_taps - 1) / 2.0
    fc = cutoff_hz / sample_rate_in
    h = 2.0 * fc * np.sinc(2.0 * fc * n)
    w = np.blackman(n_taps)
    h = h * w
    return h / np.sum(h)


# ---------------------------------------------------------------------------
# Self-checks -- run these whenever you change the maths
# ---------------------------------------------------------------------------
def self_test(verbose: bool = True) -> bool:
    ok = True

    def check(label, condition, detail=""):
        nonlocal ok
        if not condition:
            ok = False
        if verbose:
            print(f"  [{'PASS' if condition else 'FAIL'}] {label}{detail}")

    # 1. Capsules are unit vectors and mutually symmetric.
    norms = np.linalg.norm(CAPSULE_DIRECTIONS, axis=1)
    check("capsule directions are unit length", np.allclose(norms, 1.0))
    check("capsule directions sum to zero",
          np.allclose(CAPSULE_DIRECTIONS.sum(axis=0), 0.0, atol=1e-12))

    # 2. A plane wave hitting the array from direction d, sampled by ideal
    #    coincident capsules, must decode to the SN3D encoding of d.
    m = a_to_b_matrix()
    for az, el in [(0, 0), (90, 0), (0, 90), (45, 35.26), (-120, -20)]:
        d = spherical_to_cartesian(az, el)
        # Ideal first-order capsule response: 0.5*(1 + cos) is a cardioid, but
        # the A-to-B matrix is defined for the pressure+velocity decomposition,
        # so feed it pressure 1 and velocity d.
        a = 0.5 * (1.0 + CAPSULE_DIRECTIONS @ d)
        b = m @ a
        expect = 0.5 * encode_source(d)
        check(f"A-to-B recovers encoding at az={az} el={el}",
              np.allclose(b, expect, atol=1e-9),
              f"  got {np.round(b, 4)} want {np.round(expect, 4)}")

    # 3. Cube layout is a 2-design.
    u = cube_speaker_layout()
    check("cube layout: sum(u) == 0", np.allclose(u.sum(axis=0), 0.0, atol=1e-12))
    check("cube layout: sum(u u^T) == (N/3) I",
          np.allclose(u.T @ u, (u.shape[0] / 3.0) * np.eye(3), atol=1e-12))

    # 4. Encode then decode must put the energy in the right place.
    dec = decode_matrix(u, max_re=False)
    for az, el in [(0, 0), (90, 0), (180, 0), (0, 45)]:
        d = spherical_to_cartesian(az, el)
        b = encode_source(d)
        feeds = dec @ b
        check(f"decoded pressure preserved at az={az} el={el}",
              np.isclose(feeds.sum(), b[0], atol=1e-9))
        vel = (feeds[:, None] * u).sum(axis=0)
        check(f"decoded velocity preserved at az={az} el={el}",
              np.allclose(vel, d, atol=1e-9),
              f"  got {np.round(vel, 4)} want {np.round(d, 4)}")

    # 5. Analytic HRIR must show the right ear leading for a source on the right.
    fs = 48000.0
    right = analytic_hrir(spherical_to_cartesian(-90, 0), 256, fs)
    e_left = np.sum(right[0] ** 2)
    e_right = np.sum(right[1] ** 2)
    check("source at az=-90 is louder in the right ear", e_right > e_left * 1.5,
          f"  L={e_left:.4g} R={e_right:.4g}")

    front = analytic_hrir(spherical_to_cartesian(0, 0), 256, fs)
    check("source straight ahead is symmetric",
          np.allclose(front[0], front[1], atol=1e-9))

    behind = analytic_hrir(spherical_to_cartesian(180, 0), 256, fs)
    check("source behind is still left/right symmetric",
          np.allclose(behind[0], behind[1], atol=1e-9))
    # Without a front/back term the render has no cue at all for ahead vs
    # behind, so make sure the model actually distinguishes them.
    spec_f = np.abs(np.fft.rfft(front[0], 4096))
    spec_b = np.abs(np.fft.rfft(behind[0], 4096))
    fr = np.fft.rfftfreq(4096, 1.0 / fs)
    hf = (fr > 5000.0) & (fr < 15000.0)
    hf_diff = 20 * np.log10(
        np.mean(spec_f[hf]) / max(float(np.mean(spec_b[hf])), 1e-12))
    check("sources behind are dimmer above 5 kHz than sources ahead",
          hf_diff > 2.0, f"  {hf_diff:+.2f} dB")

    above = analytic_hrir(spherical_to_cartesian(0, 90), 256, fs)
    check("source above differs from source ahead",
          not np.allclose(above[0], front[0], atol=1e-6))

    # 6. Decimation filter: flat where it matters, dead where aliasing would
    #    become audible.
    h = design_decimation_fir(DECIMATOR_TAPS, 4, 192000.0)
    check("decimator has unity DC gain", np.isclose(np.sum(h), 1.0, atol=1e-9))
    spec = np.abs(np.fft.rfft(h, 16384))
    fr = np.fft.rfftfreq(16384, 1.0 / 192000.0)

    at_10k = np.interp(10000.0, fr, spec)
    check("decimator is flat at 10 kHz", abs(20 * np.log10(at_10k)) < 0.5,
          f"  {20 * np.log10(at_10k):+.2f} dB")

    # Anything from 28 kHz up folds below 20 kHz, so this is the real spec.
    worst = np.max(spec[fr >= 28000.0])
    check("decimator attenuates the fold-back band (>=28 kHz) by >80 dB",
          worst < 1e-4, f"  worst {20 * np.log10(max(worst, 1e-12)):.1f} dB")

    return ok


if __name__ == "__main__":
    print("qpr_ambisonics self-test")
    raise SystemExit(0 if self_test() else 1)
