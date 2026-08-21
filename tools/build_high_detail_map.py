#!/usr/bin/env python3
"""Prepare overlapping references and assemble native-detail generated regions."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "Assets" / "map_10000_high_detail"
SOURCE = ROOT / "Assets" / "map_10000" / "map_master_generated_1254.png"
REFERENCE = ASSET / "references"
GENERATED = ASSET / "generated"
FINAL = ASSET / "tiles"
GRID = 8
CELL = 1250
OVERLAP = 125
REFERENCE_SIZE = CELL + OVERLAP * 2
MODEL_SIZE = 1254


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def prepare() -> None:
    for directory in (REFERENCE, GENERATED, FINAL):
        directory.mkdir(parents=True, exist_ok=True)

    for row in range(GRID):
        for col in range(GRID):
            window = CELL + OVERLAP * 2
            left_world = min(max(0, col * CELL - OVERLAP), 10000 - window)
            top_world = min(max(0, row * CELL - OVERLAP), 10000 - window)
            right_world = left_world + window
            bottom_world = top_world + window
            scale = MODEL_SIZE / 10000
            left = round(left_world * scale)
            top = round(top_world * scale)
            right = round(right_world * scale)
            bottom = round(bottom_world * scale)
            width, height = right - left, bottom - top
            output = REFERENCE / f"reference_r{row:02d}_c{col:02d}.png"
            run(
                "magick",
                str(SOURCE),
                "-crop",
                f"{width}x{height}+{left}+{top}",
                "+repage",
                "-resize",
                f"{MODEL_SIZE}x{MODEL_SIZE}!",
                str(output),
            )


def assemble() -> None:
    """Extract each region's authoritative cell and join the 8x8 grid."""
    window = CELL + OVERLAP * 2
    for row in range(GRID):
        for col in range(GRID):
            left_world = min(max(0, col * CELL - OVERLAP), 10000 - window)
            top_world = min(max(0, row * CELL - OVERLAP), 10000 - window)
            x0 = round((col * CELL - left_world) * MODEL_SIZE / window)
            y0 = round((row * CELL - top_world) * MODEL_SIZE / window)
            x1 = round((col * CELL + CELL - left_world) * MODEL_SIZE / window)
            y1 = round((row * CELL + CELL - top_world) * MODEL_SIZE / window)
            source = GENERATED / f"generated_r{row:02d}_c{col:02d}.png"
            output = FINAL / f"map_r{row:02d}_c{col:02d}.png"
            run(
                "magick",
                str(source),
                "-crop",
                f"{x1 - x0}x{y1 - y0}+{x0}+{y0}",
                "+repage",
                "-filter",
                "Lanczos",
                "-resize",
                f"{CELL}x{CELL}!",
                "-strip",
                str(output),
            )

    ordered = [
        str(FINAL / f"map_r{row:02d}_c{col:02d}.png")
        for row in range(GRID)
        for col in range(GRID)
    ]
    run(
        "vips",
        "arrayjoin",
        " ".join(ordered),
        str(ASSET / "map_master_10000_high_detail.png"),
        "--across",
        str(GRID),
    )
    run(
        "magick",
        str(ASSET / "map_master_10000_high_detail.png"),
        "-resize",
        "1250x1250",
        str(ASSET / "map_preview_high_detail.png"),
    )


if __name__ == "__main__":
    import sys

    assemble() if "--assemble" in sys.argv else prepare()
