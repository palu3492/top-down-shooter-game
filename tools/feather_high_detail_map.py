#!/usr/bin/env python3
"""Blend overlapping generated regions into a seamless 10,000px master."""

from pathlib import Path
import subprocess

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "Assets" / "map_10000_high_detail"
GENERATED = ASSET / "generated"
STRIPES = ASSET / "feather_stripes"
GRID = 8
CELL = 1250
OVERLAP = 125
WINDOW = CELL + OVERLAP * 2
WORLD = 10000
STRIPE_HEIGHT = 1000


def window_origin(index: int) -> int:
    return min(max(0, index * CELL - OVERLAP), WORLD - WINDOW)


def axis_weights(index: int) -> np.ndarray:
    origin = window_origin(index)
    cell_start = index * CELL
    cell_end = cell_start + CELL
    positions = np.arange(origin, origin + WINDOW, dtype=np.float32)
    weights = np.ones(WINDOW, dtype=np.float32)
    if origin < cell_start:
        weights = np.where(
            positions < cell_start,
            (positions - origin + 1) / (cell_start - origin + 1),
            weights,
        )
    window_end = origin + WINDOW
    if window_end > cell_end:
        weights = np.where(
            positions >= cell_end,
            (window_end - positions) / (window_end - cell_end + 1),
            weights,
        )
    return np.clip(weights, 1e-4, 1.0)


def blend_stripe(top: int) -> Path:
    height = min(STRIPE_HEIGHT, WORLD - top)
    accum = np.zeros((height, WORLD, 3), dtype=np.float32)
    total = np.zeros((height, WORLD, 1), dtype=np.float32)

    for row in range(GRID):
        region_top = window_origin(row)
        region_bottom = region_top + WINDOW
        use_top = max(top, region_top)
        use_bottom = min(top + height, region_bottom)
        if use_top >= use_bottom:
            continue
        local_top = use_top - region_top
        local_bottom = use_bottom - region_top
        wy = axis_weights(row)[local_top:local_bottom, None]

        for col in range(GRID):
            region_left = window_origin(col)
            source = GENERATED / f"generated_r{row:02d}_c{col:02d}.png"
            with Image.open(source) as opened:
                region = opened.convert("RGB").resize(
                    (WINDOW, WINDOW), Image.Resampling.LANCZOS
                )
                pixels = np.asarray(
                    region.crop((0, local_top, WINDOW, local_bottom)),
                    dtype=np.float32,
                )
            weight = wy * axis_weights(col)[None, :]
            target_y0 = use_top - top
            target_y1 = use_bottom - top
            accum[target_y0:target_y1, region_left : region_left + WINDOW] += (
                pixels * weight[..., None]
            )
            total[target_y0:target_y1, region_left : region_left + WINDOW] += (
                weight[..., None]
            )

    blended = np.clip(accum / np.maximum(total, 1e-6), 0, 255).astype(np.uint8)
    output = STRIPES / f"stripe_{top:05d}.png"
    Image.fromarray(blended, "RGB").save(output, compress_level=4)
    return output


def main() -> None:
    STRIPES.mkdir(parents=True, exist_ok=True)
    stripes = [blend_stripe(top) for top in range(0, WORLD, STRIPE_HEIGHT)]
    master = ASSET / "map_master_10000_high_detail_feathered.png"
    subprocess.run(
        [
            "vips",
            "arrayjoin",
            " ".join(map(str, stripes)),
            str(master),
            "--across",
            "1",
        ],
        check=True,
    )
    subprocess.run(
        ["magick", str(master), "-resize", "1250x1250", str(ASSET / "map_preview_high_detail_feathered.png")],
        check=True,
    )


if __name__ == "__main__":
    main()
