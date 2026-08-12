import pygame

from shooter import config
from shooter.entities.zombie import Zombie


class WaveSystem:
    wave_count = 0
    wave_timer = 0

    def __init__(self, window, zombie_group, player_cash):
        for _ in range(config.WAVE_BASE):
            zombie_group.add(Zombie(window, player_cash))

    def wave_gui(self, screen):
        return True

    def wave_control(self, screen, window, zombie_group, player_cash):
        # tick and next wave spawner
        if self.wave_timer == config.WAVE_INTERVAL_FRAMES:
            self.wave_count += 1
            num_spawn = config.WAVE_BASE + pow(self.wave_count, 2)
            for _ in range(num_spawn):
                zombie_group.add(Zombie(window, player_cash))
            self.wave_timer = 0
        else:
            self.wave_timer += 1

        # Updating timer to screen
        screen.blit(
            pygame.font.Font(None, 40).render(
                "Time until next round " + str(15 - (int(self.wave_timer / 100))),
                True,
                config.WHITE,
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

        # Checks if player is pressing SPACE
        # if so, then timer is set to 0 and
        # next round starts
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_SPACE]:
            self.wave_timer = config.WAVE_INTERVAL_FRAMES
