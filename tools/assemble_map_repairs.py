#!/usr/bin/env python3
"""Build non-destructive repair patches and a review master."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "Assets" / "map_10000_high_detail"
WORK = ASSET / "repair_work"
SOURCE = ASSET / "map_master_10000_high_detail_feathered.png"
PATCHES = WORK / "patches"
GENERATED = WORK / "generated"
REVIEW_MASTER = WORK / "map_master_repairs_review.png"
REVIEW_PREVIEW = WORK / "map_repairs_review_preview.png"
FEATHER_RADIUS = 96


def main() -> None:
    manifest = json.loads((WORK / "regions.json").read_text())
    PATCHES.mkdir(parents=True, exist_ok=True)

    with Image.open(SOURCE) as opened:
        master = opened.convert("RGBA")

    for region in manifest["regions"]:
        region_id = region["id"]
        crop_x, crop_y, crop_width, crop_height = region["crop"]
        repair_left, repair_top, repair_right, repair_bottom = region["repair_box"]

        with Image.open(GENERATED / f"{region_id}.png") as opened:
            repaired = opened.convert("RGBA").resize(
                (crop_width, crop_height), Image.Resampling.LANCZOS
            )

        local_box = (
            repair_left - crop_x,
            repair_top - crop_y,
            repair_right - crop_x,
            repair_bottom - crop_y,
        )
        alpha = Image.new("L", (crop_width, crop_height), 0)
        ImageDraw.Draw(alpha).rectangle(local_box, fill=255)
        alpha = alpha.filter(ImageFilter.GaussianBlur(FEATHER_RADIUS))
        repaired.putalpha(alpha)

        patch_path = PATCHES / f"{region_id}.png"
        repaired.save(patch_path, compress_level=4)
        master.alpha_composite(repaired, (crop_x, crop_y))
        region["patch"] = f"patches/{region_id}.png"
        region["placement_world_px"] = [crop_x, crop_y]

    master.convert("RGB").save(REVIEW_MASTER, compress_level=4)
    master.convert("RGB").resize((1250, 1250), Image.Resampling.LANCZOS).save(
        REVIEW_PREVIEW,
        compress_level=4,
    )
    manifest["review_master"] = REVIEW_MASTER.name
    manifest["review_preview"] = REVIEW_PREVIEW.name
    manifest["feather_radius_px"] = FEATHER_RADIUS
    (WORK / "repair_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
