"""A sky that moves without anything being redrawn.

The backdrop is six colours mapped from a painting, so changing *what those six
colours are* animates the whole picture at the cost of a colour swap. That is
palette cycling, and it is how the era this art is imitating did it -- the sun
becomes a moon and the sunset becomes a night without a second image.

The alternative, moving sprites over a static sky, would need artwork we do not
have and would cost more every frame than this costs twice a second.
"""

from itertools import pairwise

import pygame

from shooter.assets import load_image

ART = "Backgrounds/menu_pixel.png"

# The palette the art was baked with, darkest first. `tools/make_menu_art.py`
# holds the same ramp; these are the colours actually in the file.
DUSK = (
    (16, 19, 28),
    (31, 48, 74),
    (45, 106, 106),
    (214, 120, 54),
    (240, 192, 90),
    (250, 238, 178),
)
NIGHT = (
    (10, 11, 18),
    (16, 22, 42),
    (24, 44, 66),
    (44, 52, 92),
    (72, 84, 130),
    (188, 198, 235),
)
DAWN = (
    (22, 16, 26),
    (54, 38, 74),
    (120, 74, 110),
    (222, 124, 110),
    (246, 186, 150),
    (255, 238, 214),
)

# Where each palette sits in the cycle. Night is held so it is a place rather
# than a moment passed through.
KEYFRAMES = ((0.0, DUSK), (0.3, NIGHT), (0.55, NIGHT), (0.8, DAWN), (1.0, DUSK))

CYCLE_SECONDS = 54.0
STEPS = 108  # a rebuild about twice a second, imperceptible as a change


def blend(one, other, amount):
    return tuple(round(a + (b - a) * amount) for a, b in zip(one, other, strict=True))


def palette_at(phase):
    """The six colours in force at a point in the cycle, 0 to 1."""
    phase = phase % 1.0
    for (start, early), (end, late) in pairwise(KEYFRAMES):
        if start <= phase <= end:
            span = end - start
            amount = 0.0 if span == 0 else (phase - start) / span
            return tuple(blend(a, b, amount) for a, b in zip(early, late, strict=True))
    return DUSK


class Sky:
    """The backdrop at the size and time it is wanted.

    One surface is kept, not a cache of many: at full size each is three
    megabytes, and the whole point is that only one is ever on screen.
    """

    def __init__(self, size):
        self.size = tuple(size)
        self.step = None
        self.surface = None

    def phase(self, seconds):
        return (seconds % CYCLE_SECONDS) / CYCLE_SECONDS

    def at(self, seconds):
        step = int(self.phase(seconds) * STEPS)
        if step != self.step:
            self.step = step
            self.surface = self._build(step / STEPS)
        return self.surface

    def _build(self, phase):
        art = load_image(ART).copy()
        pixels = pygame.PixelArray(art)
        for original, shifted in zip(DUSK, palette_at(phase), strict=True):
            pixels.replace(original, shifted)
        pixels.close()
        # `scale`, not `smoothscale`: interpolating pixel art is what stops it
        # looking like pixel art.
        return pygame.transform.scale(art, self.size)
