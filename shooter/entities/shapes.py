"""Small resource pickups that do not yet have production art."""

from functools import cache

import pygame

RAG = (128, 116, 96)
RAG_LIT = (162, 150, 128)


@cache
def cloth(width=38, height=30):
    """A torn rag."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(
        surface,
        RAG,
        ((2, height - 6), (0, 8), (width // 2, 0), (width, 10), (width - 6, height)),
    )
    pygame.draw.polygon(
        surface, RAG_LIT, ((8, height - 10), (width // 3, 6), (width - 12, 12))
    )
    return surface
