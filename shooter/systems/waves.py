import pygame

from shooter import config
from shooter.entities.zombie import Zombie
from shooter.ui.anchor import CENTRE, TOP, place

BANNER_SIZE = (500, 160)
BANNER_INSET = (0, 150)
BOARD_SIZE = (500, 100)
BOARD_TOP = 60
TIMER_LINE = 0
PROMPT_LINE = 30
OPTIONS_LINE = 80
BOARD_BACKGROUND = (100, 100, 100)
BOARD_STRIPE = (100, 255, 100)


class WaveSystem:
    def __init__(self, window, zombie_group, player_cash):
        self.wave_count = 0
        self.wave_seconds = 0.0
        for _ in range(config.WAVE_BASE):
            zombie_group.add(Zombie(window, player_cash))

    def wave_gui(self, screen):
        return True

    def advance(self, window, zombie_group, player_cash, dt=config.SIM_DT):
        """Move the between-wave timer forward and spawn when it elapses."""
        if self.wave_seconds >= config.WAVE_INTERVAL_SECONDS:
            self.wave_count += 1
            for _ in range(config.WAVE_BASE + pow(self.wave_count, 2)):
                zombie_group.add(Zombie(window, player_cash))
            self.wave_seconds = 0.0
        else:
            self.wave_seconds += dt

        if pygame.key.get_pressed()[pygame.K_SPACE]:
            self.wave_seconds = config.WAVE_INTERVAL_SECONDS

    def draw(self, screen, window=config.WINDOW):
        """The banner is centred on the window rather than pinned at x=300,
        which only ever looked right at one resolution."""
        remaining = max(0, int(config.WAVE_INTERVAL_SECONDS - self.wave_seconds))
        banner = place(BANNER_SIZE, window, CENTRE, TOP, BANNER_INSET)

        self._centred(screen, f"Time until next round {remaining}", banner, TIMER_LINE)
        self._centred(screen, "or press [SPACE] to continue", banner, PROMPT_LINE)

        board = pygame.Rect(banner.left, banner.top + BOARD_TOP, *BOARD_SIZE)
        pygame.draw.rect(screen, BOARD_BACKGROUND, board)
        pygame.draw.rect(screen, BOARD_STRIPE, (*board.topleft, board.width, 10))
        self._centred(screen, "[AMMO]     [HEALTH]     [GUN]", banner, OPTIONS_LINE)

    def _centred(self, screen, message, banner, top):
        text = pygame.font.Font(None, 40).render(message, True, config.WHITE)
        screen.blit(text, (banner.centerx - text.get_width() // 2, banner.top + top))
