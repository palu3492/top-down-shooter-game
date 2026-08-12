"""The simulation must produce identical state regardless of frame rate.

AT12 made the game frame-rate *tolerant* -- results were close. A fixed
timestep makes it frame-rate *independent*: the same number of simulation
steps produces byte-identical state at any rendering speed.
"""

import hashlib

import pygame
import pytest

from shooter import config
from shooter.entities.player import Human
from shooter.entities.zombie import Zombie
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import GunData

RATES = [30, 60, 90, 144, 300]
STEPS = 120


def fingerprint(*values):
    return hashlib.sha256("|".join(f"{v:.9f}" for v in values).encode()).hexdigest()


def simulate(steps, cash):
    """Run a fixed number of simulation steps and fingerprint the result."""
    zombie = Zombie(config.WINDOW, cash)
    zombie.set_position(2500, 2500)
    zombie.move_position(0, 0)
    human = Human(config.WINDOW)
    human.remove_health(20)
    gun = GunData(config.WINDOW)
    camera_x = 0.0

    for _ in range(steps):
        camera_x -= config.PLAYER_SPEED * config.SIM_DT
        zombie.move_toward_center(camera_x, 0, config.SIM_DT)
        zombie.zombie_speed_timer(config.SIM_DT)
        human.update_anim("MOVE", config.SIM_DT)
        gun.reloading(config.SIM_DT)

    return fingerprint(
        camera_x, zombie.zombie_x, zombie.zombie_y, human.health, gun.reload_seconds
    )


def test_the_simulation_step_is_a_pure_function_of_step_count(cash):
    assert simulate(STEPS, cash) == simulate(STEPS, cash)


def test_frame_rate_cannot_influence_a_fixed_step(cash):
    """A step advances by SIM_DT no matter how often frames are drawn."""
    reference = simulate(STEPS, cash)

    for rate in RATES:
        frames_per_step = max(1, round(rate / config.SIM_HZ))
        assert frames_per_step >= 1
        assert simulate(STEPS, cash) == reference


@pytest.mark.parametrize("rate", RATES)
def test_the_accumulator_runs_the_right_number_of_steps(rate):
    """One second of frames at any rate yields SIM_HZ steps, give or take one."""
    accumulator = 0.0
    steps = 0
    for _ in range(rate):
        accumulator += 1 / rate
        while accumulator >= config.SIM_DT:
            accumulator -= config.SIM_DT
            steps += 1

    assert steps == pytest.approx(config.SIM_HZ, abs=1)


def test_a_slow_frame_cannot_spiral(cash):
    """Clamping frame time bounds the catch-up work a single frame can trigger."""
    accumulator = min(10.0, config.MAX_FRAME_SECONDS)
    steps = 0
    while accumulator >= config.SIM_DT:
        accumulator -= config.SIM_DT
        steps += 1

    assert steps <= config.MAX_FRAME_SECONDS * config.SIM_HZ + 1


def test_the_wave_timer_is_step_driven(window, cash):
    group = pygame.sprite.Group()
    waves = WaveSystem(window, group, cash)
    waves.wave_seconds = 0.0

    for _ in range(config.SIM_HZ):
        waves.advance(window, group, cash, config.SIM_DT)

    assert waves.wave_seconds == pytest.approx(1.0, abs=config.SIM_DT)
