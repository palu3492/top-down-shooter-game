import pygame
import pytest

from conftest import WINDOW, FakeCash
from shooter.entities.powerups import PowerUps
from shooter.entities.zombie import Zombie

LIFETIME = 1200


@pytest.fixture
def powerup():
    return PowerUps()


@pytest.fixture
def far_away():
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((10, 10))
    sprite.rect = pygame.Rect(-9999, -9999, 10, 10)
    return sprite


def is_transparent(surface):
    return surface.get_at((surface.get_width() // 2, surface.get_height() // 2)).a == 0


def test_survives_its_whole_lifetime_then_expires(powerup, far_away, display):
    group = pygame.sprite.Group()

    for frame in range(LIFETIME + 1):
        if powerup.update(far_away, group, display, 0, 0):
            assert frame == LIFETIME
            return

    raise AssertionError("never expired")


def test_blinks_before_expiring(powerup, far_away, display):
    group = pygame.sprite.Group()
    transparent = visible = 0

    for _ in range(LIFETIME):
        if powerup.update(far_away, group, display, 0, 0):
            break
        if powerup.timer_count > 400:
            if is_transparent(powerup.image):
                transparent += 1
            else:
                visible += 1

    assert transparent > 0
    assert visible > 0


def test_walking_into_it_consumes_it(powerup, display):
    group = pygame.sprite.Group()
    player = pygame.sprite.Sprite()
    player.image = pygame.Surface((10, 10))
    player.rect = powerup.rect.copy()

    assert powerup.update(player, group, display, 0, 0) is True


def test_nuke_clears_the_horde(powerup, display):
    cash = FakeCash()
    group = pygame.sprite.Group(*[Zombie(WINDOW, cash) for _ in range(6)])
    player = pygame.sprite.Sprite()
    player.image = pygame.Surface((10, 10))
    player.rect = powerup.rect.copy()

    powerup.update(player, group, display, 0, 0)

    assert len(group) == 0


def test_it_tracks_the_camera(powerup, far_away, display):
    start = powerup.rect.topleft

    powerup.update(far_away, pygame.sprite.Group(), display, -10, 5)

    assert powerup.rect.topleft == (start[0] - 10, start[1] + 5)
