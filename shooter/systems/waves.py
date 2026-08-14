import pygame

from shooter import config
from shooter.systems import world
from shooter.entities.zombie import Zombie
from shooter.ui.anchor import CENTRE, TOP, place

BANNER_SIZE = (500, 60)
BANNER_INSET = (0, 150)
TIMER_LINE = 0
PROMPT_LINE = 30


class WaveSystem:
    """The freeplay rules: waves for as long as the player survives.

    `outcome` is the seam AT31 left for modes. Endless play has no finish line,
    so this never declares a win and a game only ends by being lost. A level
    (AT34) is this with a target.
    """

    outcome = None
    level = None
    layout = world.STARTER

    def __init__(self, window, zombie_group, player_cash, visible=None):
        self.wave_count = 0
        self.wave_seconds = 0.0
        for _ in range(config.WAVE_BASE):
            zombie_group.add(Zombie(window, player_cash, visible))

    def advance(
        self, window, zombie_group, player_cash, dt=config.SIM_DT, visible=None
    ):
        """Move the between-wave timer forward and spawn when it elapses."""
        if self.wave_seconds >= config.WAVE_INTERVAL_SECONDS:
            self.wave_count += 1
            for _ in range(config.WAVE_BASE + pow(self.wave_count, 2)):
                zombie_group.add(Zombie(window, player_cash, visible))
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

    def _centred(self, screen, message, banner, top):
        text = pygame.font.Font(None, 40).render(message, True, config.WHITE)
        screen.blit(text, (banner.centerx - text.get_width() // 2, banner.top + top))
