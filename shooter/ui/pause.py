from functools import cache

import pygame

VEIL = (0, 0, 0, 170)
TITLE = (255, 255, 255)
HINT = (190, 190, 190)


def _font(size):
    return pygame.font.Font(None, size)


@cache
def _veil(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(VEIL)
    return surface


def draw(screen, window, snapshot):
    screen.blit(snapshot, (0, 0))
    screen.blit(_veil(window), (0, 0))

    centre_x, centre_y = window[0] // 2, window[1] // 2
    title = _font(96).render("PAUSED", True, TITLE)
    hint = _font(34).render("Esc resume     Q quit", True, HINT)
    screen.blit(title, title.get_rect(center=(centre_x, centre_y - 24)))
    screen.blit(hint, hint.get_rect(center=(centre_x, centre_y + 44)))
