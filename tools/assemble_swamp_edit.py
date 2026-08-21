#!/usr/bin/env python3
"""Blend generated swamp quadrants and apply the TMX swamp polygon."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "Assets" / "map_10000_high_detail"
WORK = ASSET / "swamp_work"
SOURCE = ASSET / "map_master_10000_high_detail_feathered.png"
OUTPUT = ASSET / "map_master_10000_high_detail_swamp.png"
PREVIEW = ASSET / "map_preview_high_detail_swamp.png"

CROP_W, CROP_H = 2400, 1900
CANVAS_X, CANVAS_Y = 200, 6600
CANVAS_W, CANVAS_H = 4400, 3400
PLACEMENTS = {
    "swamp_nw.png": (0, 0),
    "swamp_ne.png": (2000, 0),
    "swamp_sw.png": (0, 1500),
    "swamp_se.png": (2000, 1500),
}

# Absolute map coordinates, copied from object 45 in world_1.tmx.
POLYGON = [
    (645.995, 6779.72),
    (959.302, 6908.919),
    (1291.99, 7264.216),
    (1711.885, 7438.635),
    (2367.575, 7645.353),
    (3271.965, 7755.172),
    (3427.005, 8317.19),
    (3885.655, 8821.06),
    (4354.005, 9266.80),
    (4357.235, 9418.61),
    (4082.685, 9615.64),
    (3013.565, 9631.79),
    (2025.195, 9402.46),
    (1311.37, 8956.72),
    (849.483, 8575.59),
    (487.726, 8178.30),
    (345.607, 7613.053),
    (539.406, 6879.849),
]


def axis_weight(length: int, start: int, canvas_length: int) -> np.ndarray:
    weight = np.ones(length, dtype=np.float32)
    overlap = 400
    if start > 0:
        weight[:overlap] = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
    if start + length < canvas_length:
        weight[-overlap:] = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
    return weight


def main() -> None:
    color_sum = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.float32)
    weight_sum = np.zeros((CANVAS_H, CANVAS_W, 1), dtype=np.float32)

    for filename, (x, y) in PLACEMENTS.items():
        image = Image.open(WORK / "generated" / filename).convert("RGB")
        image = image.resize((CROP_W, CROP_H), Image.Resampling.LANCZOS)
        pixels = np.asarray(image, dtype=np.float32)
        wx = axis_weight(CROP_W, x, CANVAS_W)
        wy = axis_weight(CROP_H, y, CANVAS_H)
        weight = (wy[:, None] * wx[None, :])[:, :, None]
        color_sum[y : y + CROP_H, x : x + CROP_W] += pixels * weight
        weight_sum[y : y + CROP_H, x : x + CROP_W] += weight

    blended = np.clip(color_sum / np.maximum(weight_sum, 1e-6), 0, 255).astype(np.uint8)
    swamp = Image.fromarray(blended, "RGB")

    mask = Image.new("L", (CANVAS_W, CANVAS_H), 0)
    points = [(round(x - CANVAS_X), round(y - CANVAS_Y)) for x, y in POLYGON]
    ImageDraw.Draw(mask).polygon(points, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(24))

    master = Image.open(SOURCE).convert("RGB")
    region = master.crop((CANVAS_X, CANVAS_Y, CANVAS_X + CANVAS_W, CANVAS_Y + CANVAS_H))
    composited = Image.composite(swamp, region, mask)
    master.paste(composited, (CANVAS_X, CANVAS_Y))
    master.save(OUTPUT, quality=95)
    master.resize((1250, 1250), Image.Resampling.LANCZOS).save(PREVIEW)


if __name__ == "__main__":
    main()
