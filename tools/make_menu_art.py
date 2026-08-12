"""Bake the pixel-art menu background from the original painting.

Run when `Assets/Backgrounds/menu_1.jpg` or the palette changes:

    uv run --no-sync python tools/make_menu_art.py

The mapping is a nearest-colour search per pixel, which takes about a second in
Python. That is nothing here and unacceptable at startup, which is why the
result is committed rather than computed when the game launches.

The output is 135x90 -- exactly an eighth of the 1080x720 render surface, so the
default resolution gets whole square pixels rather than a mix of eight- and
nine-wide blocks.
"""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Assets" / "Backgrounds" / "menu_1.jpg"
TARGET = ROOT / "Assets" / "Backgrounds" / "menu_pixel.png"

WINDOW = (1080, 720)
BLOCKS = (135, 90)

# A sunset ramp: night, dusk, the teal band, the glow, the low sun, its centre.
PALETTE = (
    (16, 19, 28),
    (31, 48, 74),
    (45, 106, 106),
    (214, 120, 54),
    (240, 192, 90),
    (250, 238, 178),
)


def nearest(colour):
    red, green, blue = colour
    return min(
        PALETTE,
        key=lambda p: (p[0] - red) ** 2 + (p[1] - green) ** 2 + (p[2] - blue) ** 2,
    )


def fitted(art):
    """Scale to the window width and sit it on the ground, sky continued above.

    The painting is a 2:1 banner and the window is 3:2. Cropping to fill would
    cut the shooter off the left edge.
    """
    height = round(art.get_height() * WINDOW[0] / art.get_width())
    scaled = pygame.transform.smoothscale(art, (WINDOW[0], height))
    surface = pygame.Surface(WINDOW)
    surface.fill(scaled.get_at((0, 0)))
    surface.blit(scaled, (0, WINDOW[1] - height))
    return surface


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))

    small = pygame.transform.smoothscale(fitted(pygame.image.load(SOURCE)), BLOCKS)
    seen = {}
    pixels = pygame.PixelArray(small)
    for x in range(BLOCKS[0]):
        for y in range(BLOCKS[1]):
            colour = small.unmap_rgb(pixels[x, y])[:3]
            if colour not in seen:
                seen[colour] = nearest(colour)
            pixels[x, y] = seen[colour]
    pixels.close()

    pygame.image.save(small, TARGET)
    print(f"wrote {TARGET.relative_to(ROOT)} at {BLOCKS[0]}x{BLOCKS[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
