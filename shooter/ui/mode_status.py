"""Pygame presentation for immutable mode-status snapshots."""

import pygame

from shooter import config
from shooter.ui.anchor import CENTRE, TOP, place

BANNER_SIZE = (500, 60)
BANNER_INSET = (0, 150)


class SurvivalStatusDisplay:
    def draw(self, screen, status, window=config.WINDOW):
        if status.outcome is not None:
            return
        banner = place(BANNER_SIZE, window, CENTRE, TOP, BANNER_INSET)
        if status.wave_target is None:
            first = f"Time until next round {int(status.preparation_remaining)}"
        else:
            first = f"{status.title}  --  WAVE {status.wave} OF {status.wave_target}"
        self._centred(screen, first, banner, 0)
        self._centred(
            screen,
            f"next in {int(status.preparation_remaining)}, or [SPACE]",
            banner,
            30,
        )

    @staticmethod
    def _centred(screen, message, banner, top):
        text = pygame.font.Font(None, 40).render(message, True, config.WHITE)
        screen.blit(text, (banner.centerx - text.get_width() // 2, banner.top + top))
