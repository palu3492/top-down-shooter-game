#!/usr/bin/env python3
"""Assemble non-destructive occlusion-cleanup edits into a review master."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "Assets/map_10000_high_detail/repair_work/occlusion_cleanup"
SOURCE = ROOT / "Assets/map_10000_high_detail/map_master_10000_high_detail_feathered.png"
FEATHER_RADIUS = 48


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    manifest = json.loads((WORK / "regions.json").read_text())
    patches = WORK / "patches"
    patches.mkdir(exist_ok=True)
    placements: list[tuple[Path, int, int]] = []

    for region in manifest["regions"]:
        left, top, width, height = region["crop"]
        mask = patches / f"{region['id']}_mask.png"
        resized = patches / f"{region['id']}_resized.png"
        patch = patches / f"{region['id']}.png"
        draw = " ".join(
            f"rectangle {x0},{y0} {x1},{y1}"
            for x0, y0, x1, y1 in region["repair_boxes"]
        )
        run(
            "magick", "-size", f"{width}x{height}", "xc:black", "-fill", "white",
            "-draw", draw, "-blur", f"0x{FEATHER_RADIUS}", str(mask),
        )
        run(
            "magick", str(WORK / "generated" / f"{region['id']}.png"),
            "-resize", f"{width}x{height}!", str(resized),
        )
        run(
            "magick", str(resized), str(mask), "-alpha", "off", "-compose",
            "CopyOpacity", "-composite", str(patch),
        )
        placements.append((patch, left, top))

    review_master = WORK / "map_master_occlusion_review.png"
    command = ["magick", str(SOURCE)]
    for patch, left, top in placements:
        command.extend(
            [str(patch), "-geometry", f"+{left}+{top}", "-compose", "Over", "-composite"]
        )
    command.append(str(review_master))
    run(*command)
    run(
        "magick", str(review_master), "-resize", "1250x1250",
        str(WORK / "map_preview_occlusion_review.png"),
    )


if __name__ == "__main__":
    main()
