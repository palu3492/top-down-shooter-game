import pygame
import pytest

import shooter.entities.powerups as powerups
from shooter import config
from shooter.entities.player import Human
from shooter.entities.powerups import (
    EXPIRED,
    INSTAKILL,
    LIFETIME,
    MAX_AMMO,
    MAX_HEALTH,
    NUKE,
    PowerUps,
)
from shooter.entities.zombie import Zombie
from shooter.game import INSTAKILL_SECONDS, collect_powerup
from shooter.ui.hud import GunData

EVERY_KIND = [INSTAKILL, NUKE, MAX_AMMO, MAX_HEALTH]


@pytest.fixture
def make_powerup():
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


def test_every_kind_can_spawn():
    kinds = {PowerUps().powerup_selected for _ in range(200)}

    assert kinds == set(EVERY_KIND)


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_survives_its_whole_lifetime_then_expires(make_powerup, far_away, kind):
    powerup = make_powerup(kind)

    dt = config.SIM_DT
    for frame in range(int(LIFETIME * config.SIM_HZ) + 2):
        result = powerup.update(far_away, 0, 0, dt)
        if result is not None:
            assert result == EXPIRED
            assert frame == pytest.approx(LIFETIME * config.SIM_HZ, abs=2)
            return

    raise AssertionError("never expired")


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_blinks_before_expiring(make_powerup, far_away, kind):
    powerup = make_powerup(kind)
    transparent = visible = 0

    dt = config.SIM_DT
    for _ in range(int(LIFETIME * config.SIM_HZ)):
        if powerup.update(far_away, 0, 0, dt) is not None:
            break
        if powerup.alive_seconds > config.POWERUP_BLINK_AFTER:
            if is_transparent(powerup.image):
                transparent += 1
            else:
                visible += 1

    assert transparent > 0
    assert visible > 0


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_walking_into_it_reports_its_kind(make_powerup, kind):
    powerup = make_powerup(kind)

    assert powerup.update(touching(powerup), 0, 0) == kind


def test_it_tracks_the_camera(powerup, far_away):
    start = powerup.rect.topleft

    powerup.update(far_away, -10, 5)

    assert powerup.rect.topleft == (start[0] - 10, start[1] + 5)


def test_collecting_applies_nothing_by_itself(powerup, window, cash):
    group = pygame.sprite.Group(*[Zombie(window, cash) for _ in range(4)])

    powerup.update(touching(powerup), 0, 0)

    assert len(group) == 4


def test_nuke_clears_the_horde(window, cash):
    group = pygame.sprite.Group(*[Zombie(window, cash) for _ in range(6)])

    collect_powerup(NUKE, None, group, None)

    assert len(group) == 0


def test_max_health_restores_the_player(window):
    human = Human(window)
    human.remove_health(60)

    collect_powerup(MAX_HEALTH, human, None, None)

    assert human.get_health() == 100


def test_max_ammo_refills_the_reserve(window):
    gun = GunData(window)
    gun.ammo_amount = 7

    collect_powerup(MAX_AMMO, None, None, gun)

    assert gun.ammo_amount == GunData.RESERVE


def test_max_ammo_leaves_the_clip_alone(window):
    gun = GunData(window)
    gun.clip_size = 12
    gun.ammo_amount = 0

    collect_powerup(MAX_AMMO, None, None, gun)

    assert gun.clip_size == 12


def test_instakill_grants_thirty_seconds():
    granted = collect_powerup(INSTAKILL, None, None, None)

    assert granted == INSTAKILL_SECONDS
    assert granted == 30.0


@pytest.mark.parametrize("kind", [NUKE, MAX_AMMO, MAX_HEALTH])
def test_other_kinds_grant_no_buff(window, cash, kind):
    granted = collect_powerup(
        kind, Human(window), pygame.sprite.Group(), GunData(window)
    )

    assert granted == 0


def test_a_normal_bullet_does_not_kill_a_fresh_zombie(window, cash):
    from shooter.entities.projectiles import Shot

    zombie = Zombie(window, cash)
    bullet = Shot(0, 0, 1, 0)
    zombie.rect.topleft = bullet.rect.topleft

    assert bullet.bullet_touching_zombie(zombie) is True
    assert zombie.zombie_health > 0
    assert cash.received == []


def test_an_instakill_bullet_kills_in_one_hit(window, cash):
    from shooter.entities.projectiles import LETHAL, Shot

    zombie = Zombie(window, cash)
    bullet = Shot(0, 0, 1, 0, damage=LETHAL)
    zombie.rect.topleft = bullet.rect.topleft

    assert bullet.bullet_touching_zombie(zombie) is True
    assert zombie.zombie_health <= 0
    assert cash.received == [50]
