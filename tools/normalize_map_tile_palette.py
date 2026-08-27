#!/usr/bin/env python3
"""Gently normalize dominant grass and road colors across generated map tiles."""

import argparse
import colorsys
from pathlib import Path

from PIL import Image


def normalize(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGB")
    pixels = []
    for red, green, blue in image.getdata():
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        degrees = hue * 360

        # Pull broad grass fields toward one hue/saturation without flattening texture.
        if 45 <= degrees <= 105 and saturation >= 0.38 and value >= 0.28:
            hue = ((degrees * 0.35) + (76 * 0.65)) / 360
            saturation = (saturation * 0.55) + (0.72 * 0.45)

        # Remove blue/brown tint from mid-value paving while retaining its shading.
        elif saturation <= 0.16 and 0.24 <= value <= 0.66:
            saturation *= 0.25

        nr, ng, nb = colorsys.hsv_to_rgb(hue, saturation, value)
        pixels.append((round(nr * 255), round(ng * 255), round(nb * 255)))

    image.putdata(pixels)
    image.save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    normalize(args.source, args.destination)


if __name__ == "__main__":
    main()
