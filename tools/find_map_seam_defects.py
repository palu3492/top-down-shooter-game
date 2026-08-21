#!/usr/bin/env python3
"""Rank likely structural defects along high-detail map generation seams.

The detector compares the hard-cut and feathered previews. Large differences
near a known generation boundary indicate that neighboring source regions
disagreed and feathering had to reconcile them. Results are diagnostic only;
neither master image is modified.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "Assets" / "map_10000_high_detail"
HARD_PREVIEW = ASSET / "map_preview_high_detail.png"
FEATHERED_PREVIEW = ASSET / "map_preview_high_detail_feathered.png"
OUTPUT = ASSET / "seam_diagnostics"

WORLD_SIZE = 10_000
GENERATION_CELL = 1_250
PATCH_SIZE = 1_000
SCAN_STEP = 250
SEAM_BAND = 320
MAX_CANDIDATES = 24


def clamp_patch(cx: int, cy: int) -> tuple[int, int, int, int]:
    left = min(max(0, cx - PATCH_SIZE // 2), WORLD_SIZE - PATCH_SIZE)
    top = min(max(0, cy - PATCH_SIZE // 2), WORLD_SIZE - PATCH_SIZE)
    return left, top, left + PATCH_SIZE, top + PATCH_SIZE


def overlaps_existing(
    box: tuple[int, int, int, int],
    selected: list[dict[str, object]],
) -> bool:
    left, top, right, bottom = box
    for item in selected:
        other_left, other_top, other_right, other_bottom = item["box_world_px"]
        intersection = max(0, min(right, other_right) - max(left, other_left)) * max(
            0, min(bottom, other_bottom) - max(top, other_top)
        )
        if intersection > PATCH_SIZE * PATCH_SIZE * 0.45:
            return True
    return False


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hard_image = Image.open(HARD_PREVIEW).convert("RGB")
    feathered_image = Image.open(FEATHERED_PREVIEW).convert("RGB")
    if hard_image.size != feathered_image.size:
        raise ValueError("Map previews must have identical dimensions")

    preview_width, preview_height = hard_image.size
    scale_x = preview_width / WORLD_SIZE
    scale_y = preview_height / WORLD_SIZE
    difference = ImageChops.difference(hard_image, feathered_image)

    raw: list[dict[str, object]] = []
    half_band = SEAM_BAND // 2
    for seam in range(GENERATION_CELL, WORLD_SIZE, GENERATION_CELL):
        for center in range(PATCH_SIZE // 2, WORLD_SIZE, SCAN_STEP):
            for orientation in ("vertical", "horizontal"):
                cx, cy = (seam, center) if orientation == "vertical" else (center, seam)
                world_box = clamp_patch(cx, cy)
                if orientation == "vertical":
                    band_world = (
                        seam - half_band,
                        world_box[1],
                        seam + half_band,
                        world_box[3],
                    )
                else:
                    band_world = (
                        world_box[0],
                        seam - half_band,
                        world_box[2],
                        seam + half_band,
                    )
                preview_box = (
                    round(band_world[0] * scale_x),
                    round(band_world[1] * scale_y),
                    round(band_world[2] * scale_x),
                    round(band_world[3] * scale_y),
                )
                raw.append(
                    {
                        "orientation": orientation,
                        "seam_world_px": seam,
                        "center_world_px": [cx, cy],
                        "box_world_px": list(world_box),
                        # RMS emphasizes doubled structural edges more than
                        # minor color drift.
                        "difference_score": sum(
                            ImageStat.Stat(difference.crop(preview_box)).rms
                        )
                        / 3,
                    }
                )

    selected: list[dict[str, object]] = []
    ranked = sorted(raw, key=lambda item: item["difference_score"], reverse=True)
    for candidate in ranked:
        if not overlaps_existing(tuple(candidate["box_world_px"]), selected):
            selected.append(candidate)
        if len(selected) == MAX_CANDIDATES:
            break

    for rank, candidate in enumerate(selected, 1):
        candidate["id"] = f"seam-{rank:02d}"
        candidate["rank"] = rank
        candidate["difference_score"] = round(candidate["difference_score"], 3)

    manifest = {
        "method": (
            "RMS difference between hard-cut and feathered previews near known seams"
        ),
        "world_size_px": [WORLD_SIZE, WORLD_SIZE],
        "generation_cell_px": GENERATION_CELL,
        "suggested_patch_size_px": [PATCH_SIZE, PATCH_SIZE],
        "candidate_count": len(selected),
        "candidates": selected,
    }
    (OUTPUT / "seam_candidates.json").write_text(json.dumps(manifest, indent=2) + "\n")

    annotated = feathered_image.copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()
    for candidate in selected:
        left, top, right, bottom = candidate["box_world_px"]
        preview_box = (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
        draw.rectangle(preview_box, outline=(255, 70, 40), width=2)
        label = f'{candidate["rank"]}: {candidate["difference_score"]:.1f}'
        label_x, label_y = preview_box[0] + 3, preview_box[1] + 3
        text_box = draw.textbbox((label_x, label_y), label, font=font)
        draw.rectangle(text_box, fill=(15, 15, 15))
        draw.text((label_x, label_y), label, fill=(255, 235, 90), font=font)
    annotated.save(OUTPUT / "seam_candidates_overview.png")


if __name__ == "__main__":
    main()
