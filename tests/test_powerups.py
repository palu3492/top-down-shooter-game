import pygame
import pytest

import shooter.entities.powerups as powerups
from shooter.entities.powerups import PowerUps
from shooter.entities.zombie import Zombie

LIFETIME = 1200
INSTAKILL, NUKE, MAX_AMMO, MAX_HEALTH = 1, 2, 3, 4
EVERY_KIND = [INSTAKILL, NUKE, MAX_AMMO, MAX_HEALTH]


@pytest.fixture
def make_powerup():
    """Build a power-up of a chosen kind.

    select_powerup currently hardcodes randint(2, 2), so every power-up is a
    nuke. Tests must not rely on that -- AT5 restores the full 1..4 range.
    """

    def build(kind=NUKE):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(powerups.random, "randint", lambda low, high: kind)
            return PowerUps()

    return build


@pytest.fixture
def powerup(make_powerup):
    return make_powerup()


@pytest.fixture
def far_away():
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((10, 10))
    sprite.rect = pygame.Rect(-9999, -9999, 10, 10)
    return sprite


def touching(powerup):
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((10, 10))
    sprite.rect = powerup.rect.copy()
    return sprite


def is_transparent(surface):
    return surface.get_at((surface.get_width() // 2, surface.get_height() // 2)).a == 0


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_survives_its_whole_lifetime_then_expires(make_powerup, far_away, display, kind):
    powerup = make_powerup(kind)
    group = pygame.sprite.Group()

    for frame in range(LIFETIME + 1):
        if powerup.update(far_away, group, display, 0, 0):
            assert frame == LIFETIME
            return

    raise AssertionError("never expired")


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_blinks_before_expiring(make_powerup, far_away, display, kind):
    powerup = make_powerup(kind)
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


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_walking_into_any_kind_consumes_it(make_powerup, display, kind):
    powerup = make_powerup(kind)

    assert powerup.update(touching(powerup), pygame.sprite.Group(), display, 0, 0) is True


def test_nuke_clears_the_horde(make_powerup, window, cash, display):
    powerup = make_powerup(NUKE)
    group = pygame.sprite.Group(*[Zombie(window, cash) for _ in range(6)])

    powerup.update(touching(powerup), group, display, 0, 0)

    assert len(group) == 0


@pytest.mark.parametrize("kind", [INSTAKILL, MAX_AMMO, MAX_HEALTH])
def test_other_kinds_leave_the_horde_alone(make_powerup, window, cash, display, kind):
    powerup = make_powerup(kind)
    group = pygame.sprite.Group(*[Zombie(window, cash) for _ in range(6)])

    powerup.update(touching(powerup), group, display, 0, 0)

    assert len(group) == 6


def test_it_tracks_the_camera(powerup, far_away, display):
    start = powerup.rect.topleft

    powerup.update(far_away, pygame.sprite.Group(), display, -10, 5)

    assert powerup.rect.topleft == (start[0] - 10, start[1] + 5)


@pytest.mark.xfail(strict=True, reason="selection is hardcoded to randint(2, 2)")
def test_every_kind_can_spawn():
    kinds = {PowerUps().powerup_selected for _ in range(100)}

    assert kinds == set(EVERY_KIND)
