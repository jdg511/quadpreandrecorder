#!/usr/bin/env python3
"""run_tests.py -- build and run the whole host test suite.

Vendor: Illicit Apothecary
Project: Quad Preamp and Recorder

    python3 run_tests.py

Compiles the REAL firmware sources for this computer and runs them. Works on
Windows, macOS and Linux; needs a C++ compiler (g++, clang++ or MSVC's cl) and
python3 with numpy. `ffmpeg` is optional and only used for the last check.

What this proves, without any hardware:
  1. qpr_dsp.cpp produces the same audio as the Python model you tune by ear,
     linear and in limiting.
  2. qpr_recorder.cpp keeps four files sample-aligned through a microSD stall,
     and drops audio collectively when it has to.
  3. The WAV files it writes are valid and open in ordinary tools.

What it CANNOT prove: anything electrical. SAI, eDMA, I2C, the display and the
analog path all need the board -- see docs/BRINGUP.md.

Options:
    --keep      leave the scratch SD directory in place for inspection
    --cxx PATH  use a specific compiler
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILD = HERE / "build"

SHIM = HERE / "shim"
INCLUDES = [
    SHIM,
    ROOT / "lib" / "qpr_board",
    ROOT / "lib" / "qpr_sai",
    ROOT / "lib" / "qpr_dsp",
    ROOT / "lib" / "qpr_recorder",
]

PROGRAMS = {
    "test_dsp": [
        HERE / "test_dsp.cpp",
        SHIM / "SdFat.cpp",
        ROOT / "lib" / "qpr_dsp" / "qpr_dsp.cpp",
        ROOT / "lib" / "qpr_dsp" / "qpr_coeffs.cpp",
    ],
    "test_recorder": [
        HERE / "test_recorder.cpp",
        SHIM / "SdFat.cpp",
        ROOT / "lib" / "qpr_recorder" / "qpr_recorder.cpp",
    ],
}

BOLD = "\033[1m" if sys.stdout.isatty() else ""
OFF = "\033[0m" if sys.stdout.isatty() else ""


def step(title: str) -> None:
    print(f"\n{BOLD}=== {title} ==={OFF}")


def find_compiler(explicit: str | None) -> tuple[list[str], str]:
    """Returns (command prefix, flavour)."""
    if explicit:
        return [explicit], "msvc" if explicit.lower().endswith("cl") else "gcc"
    for name in ("g++", "clang++", "c++"):
        p = shutil.which(name)
        if p:
            return [p], "gcc"
    if shutil.which("cl"):
        return ["cl"], "msvc"
    return [], ""


def compile_one(cxx: list[str], flavour: str, name: str,
                sources: list[Path]) -> Path | None:
    BUILD.mkdir(parents=True, exist_ok=True)
    exe = BUILD / (name + (".exe" if os.name == "nt" else ""))

    if flavour == "msvc":
        cmd = cxx + ["/nologo", "/std:c++17", "/O2", "/EHsc"]
        cmd += [f"/I{p}" for p in INCLUDES]
        cmd += [str(s) for s in sources]
        cmd += [f"/Fe:{exe}", f"/Fo:{BUILD}\\"]
    else:
        cmd = cxx + ["-std=gnu++17", "-O2", "-Wall", "-Wextra",
                     "-Wno-unused-parameter"]
        cmd += [f"-I{p}" for p in INCLUDES]
        cmd += [str(s) for s in sources]
        cmd += ["-o", str(exe), "-lm"]

    print(f"  building {name} ...", end=" ", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED")
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        return None
    print("ok")
    return exe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true",
                    help="leave the scratch SD directory for inspection")
    ap.add_argument("--cxx", default=None, help="path to a C++ compiler")
    args = ap.parse_args()

    failures = 0

    # ---- 1. build ----------------------------------------------------------
    step("1/4  build the real firmware sources for this computer")
    cxx, flavour = find_compiler(args.cxx)
    if not cxx:
        print("  no C++ compiler found.")
        print("  Windows : install MSYS2 (pacman -S mingw-w64-x86_64-gcc), or")
        print("            'Build Tools for Visual Studio' and run this from a")
        print("            Developer Command Prompt.")
        print("  macOS   : xcode-select --install")
        print("  Linux   : apt install build-essential")
        return 2
    print(f"  compiler {' '.join(cxx)}  ({flavour})")

    exes = {}
    for name, srcs in PROGRAMS.items():
        exe = compile_one(cxx, flavour, name, srcs)
        if exe is None:
            return 1
        exes[name] = exe
    print("  --> PASS")

    # ---- 2. DSP equivalence -------------------------------------------------
    step("2/4  monitor DSP: firmware vs the Python model")
    r = subprocess.run([sys.executable, str(HERE / "compare_firmware_to_model.py")])
    if r.returncode != 0:
        failures += 1
        print("  --> FAIL")
    else:
        print("  --> PASS")

    # ---- 3. recorder --------------------------------------------------------
    step("3/4  recorder: four streams through a simulated card stall")
    sd_dir = Path(tempfile.gettempdir()) / "qpr_sd"
    if sd_dir.exists():
        shutil.rmtree(sd_dir, ignore_errors=True)
    sd_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(exes["test_recorder"]), str(sd_dir)])
    if r.returncode != 0:
        failures += 1
        print("  --> FAIL")
    else:
        print("  --> PASS")

    # ---- 4. the WAV files it wrote -----------------------------------------
    step("4/4  the WAV files the recorder just wrote")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print("  ffprobe not installed, skipping (install ffmpeg for this check)")
        print("  --> SKIPPED")
    else:
        bad = 0
        files = sorted(sd_dir.glob("*.WAV"))
        if not files:
            print("  no files were written")
            bad = 1
        for f in files:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries",
                 "stream=codec_name,sample_rate,channels,duration",
                 "-of", "default=nw=1:nk=1", str(f)],
                capture_output=True, text=True)
            info = " ".join(r.stdout.split())
            ok = r.returncode == 0 and "pcm_s24le" in r.stdout
            print(f"  {f.name:<18} {info if ok else 'UNREADABLE'}")
            if not ok:
                bad = 1
        failures += bad
        print(f"  --> {'PASS' if not bad else 'FAIL'}")

    if not args.keep:
        shutil.rmtree(sd_dir, ignore_errors=True)
    else:
        print(f"\nscratch SD left at {sd_dir}")

    print()
    if failures == 0:
        print(f"{BOLD}ALL HOST TESTS PASSED{OFF}")
        print("The DSP and the recorder behave correctly. Everything electrical")
        print("still needs the board -- run bringup/ t01..t06 before trusting it.")
    else:
        print(f"{BOLD}SOME HOST TESTS FAILED{OFF}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
