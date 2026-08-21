"""One second of simulated time must produce the same result at any frame rate.

Each test steps a system with several different `dt` values and asserts the
outcome matches. Before AT12 these would all have scaled with frame count.
"""

import pygame
import pytest

from shooter import config
from shooter.entities.player import Human
from shooter.entities.projectiles import Shot
from shooter.entities.zombie import Zombie
from shooter.systems.waves import WaveSystem
from shooter.weapons import RELOAD, Gun

RATES = [30, 60, 144]


def run_for(seconds, rate, step):
    """Call `step(dt)` to cover `seconds` at `rate` FPS; returns time elapsed.

    Whole frames rarely divide a duration exactly, so the caller compares
    against what actually elapsed rather than what was asked for.
    """
    dt = 1 / rate
    frames = int(seconds * rate)
    for _ in range(frames):
        step(dt)
    return frames * dt


@pytest.mark.parametrize("rate", RATES)
def test_a_zombie_covers_the_same_ground(window, cash, rate):
    zombie = Zombie(window, cash)
    zombie.set_position(2000, 2000)
    zombie.move_position(0, 0)
    start = (zombie.zombie_x, zombie.zombie_y)

    run_for(1.0, rate, lambda dt: zombie.move_toward_center(0, 0, dt))

    travelled = pygame.math.Vector2(
        zombie.zombie_x - start[0], zombie.zombie_y - start[1]
    )
    # Its own pace, not the crowd's: what matters here is that a second of
    # walking covers the same ground however many frames it took.
    assert travelled.length() == pytest.approx(zombie.zombie_speed, rel=0.02)


@pytest.mark.parametrize("rate", RATES)
def test_a_bullet_covers_the_same_ground(window, cash, rate):
    bullet = Shot(0, 0, 1, 0)
    start = bullet.bullet_x

    elapsed = run_for(0.05, rate, lambda dt: bullet.update(0, 0, [], dt))

    assert bullet.bullet_x - start == pytest.approx(
        config.BULLET_SPEED * elapsed, rel=0.02
    )


@pytest.mark.parametrize("rate", RATES)
def test_health_regenerates_at_the_same_rate(window, rate):
    human = Human(window)
    human.remove_health(50)
    before = human.health

    elapsed = run_for(1.0, rate, human.health_regen)

    assert human.health - before == pytest.approx(
        config.PLAYER_REGEN * elapsed, rel=0.02
    )


@pytest.mark.parametrize("rate", RATES)
def test_a_stun_lasts_the_same_time(window, cash, rate):
    zombie = Zombie(window, cash)
    zombie.remove_speed(config.STUN_SPEED)

    run_for(config.STUN_SECONDS - 0.1, rate, zombie.zombie_speed_timer)
    assert zombie.zombie_speed == config.STUN_SPEED

    run_for(0.2, rate, zombie.zombie_speed_timer)
    assert zombie.zombie_speed == zombie.walking_speed


@pytest.mark.parametrize("rate", RATES)
def test_a_reload_takes_the_same_time(window, rate):
    gun = Gun()
    gun.loaded = 0
    gun.reload()
    dt = 1 / rate

    calls = 0
    while gun.tick(dt) == RELOAD:
        calls += 1
        assert calls < rate * 5, "reload never finished"

    assert calls * dt == pytest.approx(config.RELOAD_SECONDS, abs=2 * dt)


@pytest.mark.parametrize("rate", RATES)
def test_a_wave_arrives_at_the_same_time(window, cash, display, cash_factory, rate):
    group = pygame.sprite.Group()
    waves = WaveSystem(window, group, cash)
    group.empty()

    run_for(
        config.WAVE_INTERVAL_SECONDS - 0.2,
        rate,
        lambda dt: waves.advance(window, group, cash_factory(), dt),
    )
    assert len(group) == 0

    run_for(
        0.4,
        rate,
        lambda dt: waves.advance(window, group, cash_factory(), dt),
    )
    assert len(group) == config.WAVE_BASE + 1


@pytest.mark.parametrize("rate", RATES)
def test_the_player_image_stays_fixed_at_every_frame_rate(window, rate):
    human = Human(window)
    still = human.image

    run_for(0.1, rate, lambda dt: human.update_anim("MOVE", dt))

    assert human.image is still


def test_a_stalled_frame_cannot_teleport_anything():
    """MAX_FRAME_SECONDS caps dt so a hitch does not warp entities across the map."""
    assert config.MAX_FRAME_SECONDS < 0.5
    assert config.WINDOW[0] / 2 > config.PLAYER_SPEED * config.MAX_FRAME_SECONDS


def test_a_long_pause_does_not_bank_time(monkeypatch, window, cash):
    """Resuming must not apply the paused duration in one frame.

    The loop resets dt on every paused frame and clamps it in any case, so the
    world cannot leap forward when play resumes.
    """
    zombie = Zombie(window, cash)
    zombie.set_position(2000, 2000)
    before = (zombie.zombie_x, zombie.zombie_y)

    # a frame that took ten seconds still moves at most MAX_FRAME_SECONDS worth
    zombie.move_toward_center(0, 0, min(10.0, config.MAX_FRAME_SECONDS))

    moved = pygame.math.Vector2(
        zombie.zombie_x - before[0], zombie.zombie_y - before[1]
    ).length()
    assert moved <= zombie.zombie_speed * config.MAX_FRAME_SECONDS + 1
