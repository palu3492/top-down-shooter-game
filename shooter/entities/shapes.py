"""Stand-in art, drawn rather than loaded.

There is no tree, rock or plane sprite in the repository, and the trees the
player can already see are painted into the 5000x5000 background -- so a
choppable tree stands next to an identical one that is only scenery. That is
worth fixing with art; it is not worth waiting for.

Drawn in code rather than committed as placeholder PNGs so that replacing one
means deleting a function, not hunting for which file was temporary. Cached, so
thirty trees share one surface the way `load_image` shares a file.
"""

from functools import cache

import pygame

TRUNK = (86, 62, 40)
CANOPY = (48, 104, 44)
CANOPY_LIT = (74, 138, 58)
STONE = (118, 118, 124)
LOG = (122, 88, 54)
LOG_END = (158, 122, 82)
METAL = (140, 146, 156)
METAL_LIT = (188, 194, 204)
STONE_LIT = (156, 156, 162)


@cache
def tree(width=120, height=140):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    trunk = pygame.Rect(0, 0, max(6, width // 6), height // 2)
    trunk.midbottom = (width // 2, height)
    pygame.draw.rect(surface, TRUNK, trunk)

    canopy = width // 2
    pygame.draw.circle(surface, CANOPY, (width // 2, canopy), canopy)
    pygame.draw.circle(
        surface,
        CANOPY_LIT,
        (width // 2 - canopy // 5, canopy - canopy // 5),
        canopy // 2,
    )
    return surface


@cache
def rock(width=100, height=80):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    body = (
        (0, height),
        (width // 6, height // 3),
        (width // 2, 0),
        (width - width // 5, height // 4),
        (width, height),
    )
    pygame.draw.polygon(surface, STONE, body)
    pygame.draw.polygon(
        surface,
        STONE_LIT,
        (
            (width // 4, height),
            (width // 2, height // 4),
            (width // 2 + width // 8, height),
        ),
    )
    return surface


@cache
def wood(width=44, height=30):
    """A short log, seen from above."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(surface, LOG, (0, height // 4, width, height // 2))
    pygame.draw.ellipse(surface, LOG_END, (0, height // 4, width // 5, height // 2))
    return surface


@cache
def metal(width=40, height=28):
    """A plate of scrap."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(
        surface,
        METAL,
        ((0, height - 4), (width // 6, 4), (width - 2, 0), (width, height)),
    )
    pygame.draw.polygon(
        surface, METAL_LIT, ((width // 5, height - 6), (width // 2, 6), (width - 8, 8))
    )
    return surface
