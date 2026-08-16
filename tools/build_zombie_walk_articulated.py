"""Build a fixed-torso, two-leg zombie walk-cycle draft.

This is intentionally deterministic: one body plate and one painted set of leg
parts are reused in every frame.  Only the articulated joint positions change.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import tempfile


CANVAS = (288, 311)
FRAME_COUNT = 16
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARTS = (
    ROOT / "Assets" / "Zombie Animations" / "zombie_walk_articulated" / "_rig"
)


def run(*args: str | Path) -> None:
    subprocess.run([str(arg) for arg in args], check=True)


def point_on_cycle(
    side: str, frame: int
) -> tuple[tuple[float, float], tuple[float, float], bool]:
    """Return hip, ankle, and stance-state for one persistent leg."""
    phase = frame if side == "left" else (frame + FRAME_COUNT // 2) % FRAME_COUNT
    hip_x = 130.0 if side == "left" else 158.0
    ankle_x = 118.0 if side == "left" else 170.0
    hip = (hip_x, 151.0)

    if phase <= 8:
        # Planted foot travels steadily from north to south relative to the body.
        t = phase / 8.0
        ankle_y = 62.0 + 176.0 * t
        ankle_x += (-2.5 if side == "left" else 2.5) * math.sin(math.pi * t)
        stance = True
    else:
        # The unweighted foot returns quickly through the middle of the stride.
        t = (phase - 8) / 8.0
        eased = t * t * (3.0 - 2.0 * t)
        ankle_y = 238.0 - 176.0 * eased
        ankle_x += (-5.0 if side == "left" else 5.0) * math.sin(math.pi * t)
        stance = False

    return hip, (ankle_x, ankle_y), stance


def knee_for(
    side: str,
    hip: tuple[float, float],
    ankle: tuple[float, float],
    stance: bool,
    frame: int,
) -> tuple[float, float]:
    phase = frame if side == "left" else (frame + FRAME_COUNT // 2) % FRAME_COUNT
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    distance = max(1.0, math.hypot(dx, dy))
    midpoint = ((hip[0] + ankle[0]) / 2.0, (hip[1] + ankle[1]) / 2.0)
    perpendicular = (-dy / distance, dx / distance)
    outward = (
        1.0
        if (side == "left" and perpendicular[0] < 0)
        or (side == "right" and perpendicular[0] > 0)
        else -1.0
    )

    if stance:
        t = phase / 8.0
        bend = 3.0 * math.sin(math.pi * t)
    else:
        t = (phase - 8) / 8.0
        bend = 31.0 * math.sin(math.pi * t)

    return (
        midpoint[0] + perpendicular[0] * bend * outward,
        midpoint[1] + perpendicular[1] * bend * outward,
    )


def transform_segment(
    source: Path,
    output: Path,
    start: tuple[float, float],
    end: tuple[float, float],
    overlap: int,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = max(15, round(math.hypot(dx, dy)))
    angle = math.degrees(math.atan2(dy, dx)) - 90.0
    pivot_y = overlap / 2.0
    run(
        "magick",
        source,
        "-filter",
        "Mitchell",
        "-resize",
        f"54x{length + overlap}!",
        "-alpha",
        "on",
        "-background",
        "none",
        "-virtual-pixel",
        "transparent",
        "-set",
        "option:distort:viewport",
        f"{CANVAS[0]}x{CANVAS[1]}+0+0",
        "-distort",
        "SRT",
        f"27,{pivot_y:.2f} 1 {angle:.4f} {start[0]:.2f},{start[1]:.2f}",
        output,
    )


def transform_boot(
    source: Path,
    output: Path,
    ankle: tuple[float, float],
    angle: float,
) -> None:
    run(
        "magick",
        source,
        "-alpha",
        "on",
        "-background",
        "none",
        "-virtual-pixel",
        "transparent",
        "-set",
        "option:distort:viewport",
        f"{CANVAS[0]}x{CANVAS[1]}+0+0",
        "-distort",
        "SRT",
        f"27,2 1 {angle:.4f} {ankle[0]:.2f},{ankle[1]:.2f}",
        output,
    )


def build_leg(parts: Path, temporary: Path, side: str, frame: int) -> tuple[Path, bool]:
    hip, ankle, stance = point_on_cycle(side, frame)
    knee = knee_for(side, hip, ankle, stance, frame)
    suffix = "-right" if side == "right" else ""
    thigh_source = parts / f"thigh-crop-v2{suffix}.png"
    shin_source = parts / f"shin-crop-v2{suffix}.png"
    boot_source = parts / f"boot-crop-v2{suffix}.png"
    thigh = temporary / f"{frame:02d}-{side}-thigh.png"
    shin = temporary / f"{frame:02d}-{side}-shin.png"
    boot = temporary / f"{frame:02d}-{side}-boot.png"
    leg = temporary / f"{frame:02d}-{side}-leg.png"

    transform_segment(thigh_source, thigh, hip, knee, overlap=8)
    transform_segment(shin_source, shin, knee, ankle, overlap=8)

    # Both boots keep facing north.  A planted foot no longer flips 180 degrees
    # merely because it has moved behind the body.
    swing_tilt = 0.0
    if not stance:
        phase = frame if side == "left" else (frame + FRAME_COUNT // 2) % FRAME_COUNT
        t = (phase - 8) / 8.0
        swing_tilt = (-10.0 if side == "left" else 10.0) * math.sin(math.pi * t)
    transform_boot(boot_source, boot, ankle, 180.0 + swing_tilt)

    run(
        "magick",
        "-size",
        f"{CANVAS[0]}x{CANVAS[1]}",
        "canvas:none",
        thigh,
        "-compose",
        "over",
        "-composite",
        shin,
        "-composite",
        boot,
        "-composite",
        leg,
    )
    return leg, stance


def build(output: Path, parts: Path) -> None:
    body = parts / "body-patched-288.png"
    required = [
        body,
        parts / "thigh-crop-v2.png",
        parts / "shin-crop-v2.png",
        parts / "boot-crop-v2.png",
        parts / "thigh-crop-v2-right.png",
        parts / "shin-crop-v2-right.png",
        parts / "boot-crop-v2-right.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing rig sources: " + ", ".join(missing))

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zombie-walk-") as temporary_name:
        temporary = Path(temporary_name)
        for frame in range(FRAME_COUNT):
            left, left_stance = build_leg(parts, temporary, "left", frame)
            right, right_stance = build_leg(parts, temporary, "right", frame)
            if left_stance and not right_stance:
                back, front = right, left
            elif right_stance and not left_stance:
                back, front = left, right
            else:
                back, front = (right, left) if frame < 8 else (left, right)
            destination = output / f"zombie-walk-{frame}.png"
            run(
                "magick",
                "-size",
                f"{CANVAS[0]}x{CANVAS[1]}",
                "canvas:none",
                back,
                "-compose",
                "over",
                "-composite",
                front,
                "-composite",
                body,
                "-composite",
                destination,
            )

    frames = [output / f"zombie-walk-{frame}.png" for frame in range(FRAME_COUNT)]
    run(
        "magick",
        "montage",
        *frames,
        "-background",
        "#202124",
        "-geometry",
        "216x233+5+5",
        "-tile",
        "4x4",
        output / "articulated-sheet-v3.png",
    )
    run(
        "magick",
        "-delay",
        "12",
        "-dispose",
        "background",
        "-loop",
        "0",
        *frames,
        output / "articulated-preview-v3.gif",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parts", type=Path, default=DEFAULT_PARTS)
    args = parser.parse_args()
    if shutil.which("magick") is None:
        raise SystemExit("ImageMagick 'magick' is required")
    build(args.output, args.parts)


if __name__ == "__main__":
    main()
