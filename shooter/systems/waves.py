import pygame

from shooter import config
from shooter.entities.zombie import Zombie


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

    def draw(self, screen):
        remaining = max(0, int(config.WAVE_INTERVAL_SECONDS - self.wave_seconds))
        screen.blit(
            pygame.font.Font(None, 40).render(
                "Time until next round " + str(remaining), True, config.WHITE
            ),
            (400, 150),
        )
        screen.blit(
            pygame.font.Font(None, 40).render(
                "or press [SPACE] to continue", True, config.WHITE
            ),
            (370, 180),
        )
        pygame.draw.rect(screen, (100, 100, 100), (300, 210, 500, 100))
        pygame.draw.rect(screen, (100, 255, 100), (300, 210, 500, 10))
        screen.blit(
            pygame.font.Font(None, 40).render(
                "   [AMMO]        [HEALTH]        [GUN]", True, config.WHITE
            ),
            (300, 230),
        )
