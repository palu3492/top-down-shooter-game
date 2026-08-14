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
