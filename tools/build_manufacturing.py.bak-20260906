"""Generate the checked PCBWay fabrication and assembly handoff.

This script intentionally depends only on Python's standard library and the
KiCad 10 command-line tools.  Run it from any directory with:

    python tools/build_manufacturing.py
"""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT / "hardware"
SCHEMATIC = HARDWARE / "QuadPreRecorder.kicad_sch"
BOARD = HARDWARE / "QuadPreRecorder.kicad_pcb"
OUT = HARDWARE / "manufacturing"
GERBERS = OUT / "gerbers"
EXPORTS = HARDWARE / "exports"
FAB = HARDWARE / "fabrication"
KICAD_CLI = Path(os.environ.get("KICAD_CLI", "")) if os.environ.get("KICAD_CLI") else (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad" / "10.0" / "bin" / "kicad-cli.exe"
)


def run(*args: str, capture: bool = False) -> str:
    command = [str(KICAD_CLI), *args]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def drc_is_manufacturing_acceptable(report: str) -> bool:
    """Allow only assembly-courtyard DRC errors; block electrical/fab issues."""

    if "Found 0 unconnected pads" not in report:
        return False
    violation_kinds = {
        line.split("]", 1)[0][1:]
        for line in report.splitlines()
        if line.startswith("[") and "]:" in line
    }
    return not violation_kinds or violation_kinds <= {"courtyards_overlap"}


def reset_generated_directory(path: Path) -> None:
    resolved = path.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset path outside repository: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def build_cpl() -> None:
    raw = OUT / "QuadPreRecorder-CPL-KiCad.csv"
    run(
        "pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "both", "--exclude-dnp", "-o", str(raw), str(BOARD),
    )
    with raw.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))

    normalized = OUT / "QuadPreRecorder-CPL-PCBWay.csv"
    with normalized.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "Designator": row["Ref"],
                "Mid X": f'{float(row["PosX"]):.4f}mm',
                "Mid Y": f'{float(row["PosY"]):.4f}mm',
                "Layer": "Top" if row["Side"].lower() == "top" else "Bottom",
                "Rotation": f'{float(row["Rot"]):.2f}',
            })


def write_checksums() -> None:
    files = sorted(
        path for path in OUT.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt" and path.suffix != ".zip"
    )
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")


def make_zip(destination: Path, files: list[Path], base: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(base).as_posix())


def main() -> None:
    if not KICAD_CLI.exists():
        raise RuntimeError(f"kicad-cli not found: {KICAD_CLI}")
    for required in (SCHEMATIC, BOARD):
        if not required.exists():
            raise FileNotFoundError(required)

    OUT.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    FAB.mkdir(parents=True, exist_ok=True)
    reset_generated_directory(GERBERS)

    run("sch", "erc", "--severity-all", "-o", str(FAB / "QuadPreRecorder-erc.rpt"), str(SCHEMATIC))
    run(
        "pcb", "drc", "--all-track-errors", "--schematic-parity", "--severity-error",
        "-o", str(FAB / "QuadPreRecorder-drc.rpt"), str(BOARD),
    )
    erc = (FAB / "QuadPreRecorder-erc.rpt").read_text(encoding="utf-8-sig")
    drc = (FAB / "QuadPreRecorder-drc.rpt").read_text(encoding="utf-8-sig")
    if "ERC messages: 0  Errors 0  Warnings 0" not in erc:
        raise RuntimeError("ERC is not clean; fabrication package not generated")
    if not drc_is_manufacturing_acceptable(drc):
        raise RuntimeError("DRC has electrical/fabrication errors; fabrication package not generated")

    run(
        "pcb", "export", "gerbers", "--check-zones", "--subtract-soldermask",
        "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts",
        "-o", str(GERBERS), str(BOARD),
    )
    run("pcb", "export", "ipcd356", "-o", str(GERBERS / "QuadPreRecorder.d356"), str(BOARD))
    run(
        "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--excellon-separate-th", "--generate-map",
        "--map-format", "pdf", "--generate-report",
        "--report-path", str(OUT / "QuadPreRecorder-drill-report.txt"),
        "-o", str(GERBERS), str(BOARD),
    )

    run(
        "sch", "export", "bom", "-o", str(OUT / "QuadPreRecorder-BOM.csv"),
        "--fields", "Reference,Value,Footprint,Manufacturer,MPN,Datasheet,QUANTITY,DNP",
        "--labels", "Designator,Comment,Footprint,Manufacturer,Manufacturer Part Number,Datasheet,Quantity,DNP",
        "--group-by", "Value,Footprint,Manufacturer,MPN,DNP", "--sort-field", "Reference",
        str(SCHEMATIC),
    )
    build_cpl()

    run("sch", "export", "pdf", "-o", str(EXPORTS / "QuadPreRecorder-schematic.pdf"), str(SCHEMATIC))
    run(
        "pcb", "export", "pdf", "--mode-single", "--black-and-white", "--scale", "1",
        "--sketch-pads-on-fab-layers", "--crossout-DNP-footprints-on-fab-layers",
        "--layers", "F.Fab,F.Silkscreen,Edge.Cuts", "-o", str(OUT / "QuadPreRecorder-assembly-top.pdf"), str(BOARD),
    )
    run(
        "pcb", "export", "pdf", "--mode-single", "--black-and-white", "--scale", "1", "--mirror",
        "--sketch-pads-on-fab-layers", "--crossout-DNP-footprints-on-fab-layers",
        "--layers", "B.Fab,B.Silkscreen,Edge.Cuts", "-o", str(OUT / "QuadPreRecorder-assembly-bottom.pdf"), str(BOARD),
    )
    run(
        "pcb", "export", "pdf", "--mode-single", "--scale", "1", "--check-zones",
        "--layers", "F.Cu,F.Mask,F.Silkscreen,Edge.Cuts",
        "-o", str(EXPORTS / "QuadPreRecorder-top.pdf"), str(BOARD),
    )
    run(
        "pcb", "export", "pdf", "--mode-single", "--scale", "1", "--mirror", "--check-zones",
        "--layers", "B.Cu,B.Mask,B.Silkscreen,Edge.Cuts",
        "-o", str(EXPORTS / "QuadPreRecorder-bottom.pdf"), str(BOARD),
    )
    run(
        "pcb", "export", "svg", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet",
        "--check-zones", "--layers", "F.Cu,F.Mask,F.Silkscreen,Edge.Cuts",
        "-o", str(EXPORTS / "QuadPreRecorder-top.svg"), str(BOARD),
    )
    run(
        "pcb", "export", "svg", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet",
        "--mirror", "--check-zones", "--layers", "B.Cu,B.Mask,B.Silkscreen,Edge.Cuts",
        "-o", str(EXPORTS / "QuadPreRecorder-bottom.svg"), str(BOARD),
    )
    run(
        "pcb", "export", "step", "--force", "--no-dnp", "--subst-models",
        "-o", str(OUT / "QuadPreRecorder-RevA.step"), str(BOARD),
    )
    for side in ("top", "bottom"):
        run(
            "pcb", "render", "--side", side, "--quality", "high", "--background", "opaque",
            "--width", "2200", "--height", "1400",
            "-o", str(EXPORTS / f"QuadPreRecorder-{side}.png"), str(BOARD),
        )
    run(
        "pcb", "render", "--quality", "high", "--background", "opaque", "--perspective", "--floor",
        "--rotate", "-35,0,35", "--width", "2200", "--height", "1400",
        "-o", str(EXPORTS / "QuadPreRecorder-isometric.png"), str(BOARD),
    )

    run(
        "pcb", "export", "stats", "--format", "report", "--units", "mm",
        "-o", str(OUT / "QuadPreRecorder-board-stats.txt"), str(BOARD),
    )
    shutil.copy2(FAB / "QuadPreRecorder-erc.rpt", OUT / "QuadPreRecorder-erc.rpt")
    shutil.copy2(FAB / "QuadPreRecorder-drc.rpt", OUT / "QuadPreRecorder-drc.rpt")
    shutil.copy2(EXPORTS / "QuadPreRecorder-schematic.pdf", OUT / "QuadPreRecorder-schematic.pdf")
    shutil.copy2(HARDWARE / "connector-pinout.md", OUT / "connector-pinout.md")
    shutil.copy2(HARDWARE / "mechanical.md", OUT / "mechanical.md")

    gerber_files = sorted(path for path in GERBERS.iterdir() if path.is_file() and path.suffix.lower() != ".pdf")
    make_zip(OUT / "QuadPreRecorder-RevA-Gerbers.zip", gerber_files, GERBERS)
    write_checksums()
    handoff_files = [
        path for path in OUT.rglob("*")
        if path.is_file() and path.name != "QuadPreRecorder-RevA-PCBWay-handoff.zip"
    ]
    make_zip(OUT / "QuadPreRecorder-RevA-PCBWay-handoff.zip", handoff_files, OUT)

    print(f"Manufacturing package: {OUT}")


if __name__ == "__main__":
    main()
