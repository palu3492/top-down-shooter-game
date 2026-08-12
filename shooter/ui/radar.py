import pygame

from shooter import config


class RadarScreen:
    def __init__(self):
        pass

    def _blip(self, screen, colour, x, y):
        left, top = config.RADAR_ORIGIN
        pygame.draw.rect(
            screen,
            colour,
            (
                left + int(x / config.RADAR_SCALE),
                top + int(y / config.RADAR_SCALE),
                config.RADAR_BLIP,
                config.RADAR_BLIP,
            ),
        )

    def draw(self, screen, x, y):
        left, top = config.RADAR_ORIGIN
        size = config.RADAR_SIZE
        pygame.draw.rect(screen, config.RADAR_BACKGROUND, (left, top, size, size))
        pygame.draw.line(
            screen,
            config.BLACK,
            (left, top + size // 2),
            (left + size, top + size // 2),
        )
        pygame.draw.line(
            screen,
            config.BLACK,
            (left + size // 2, top),
            (left + size // 2, top + size),
        )
        self._blip(screen, config.RADAR_PLAYER, x, y)

    def update_zom(self, screen, zombie):
        x, y = zombie.get_position()
        self._blip(screen, config.RADAR_ZOMBIE, x, y)
