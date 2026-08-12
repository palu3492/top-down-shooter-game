import pygame
import pytest

from shooter import config

from shooter.systems.waves import WaveSystem


@pytest.fixture
def group():
    return pygame.sprite.Group()


@pytest.fixture
def waves(group, window, make_cash):
    return WaveSystem(window, group, make_cash())


def test_first_wave_spawns_five(waves, group):
    assert len(group) == 5


def test_timer_ticks_up_between_waves(waves, group, display, window, make_cash):
    waves.advance(window, group, make_cash())

    assert waves.wave_seconds == pytest.approx(config.SIM_DT)


@pytest.mark.parametrize(
    "wave, expected",
    [(1, 6), (2, 9), (3, 14), (4, 21), (5, 30)],
)
def test_spawn_count_follows_five_plus_wave_squared(
    waves, group, display, window, make_cash, wave, expected
):
    waves.wave_count = wave - 1
    waves.wave_seconds = config.WAVE_INTERVAL_SECONDS
    group.empty()

    waves.advance(window, group, make_cash())

    assert waves.wave_count == wave
    assert len(group) == expected


def test_spawning_resets_the_timer(waves, group, display, window, make_cash):
    waves.wave_seconds = config.WAVE_INTERVAL_SECONDS

    waves.advance(window, group, make_cash())

    assert waves.wave_seconds == 0.0


def test_two_wave_systems_do_not_share_progress(
    waves, group, display, window, make_cash
):
    waves.wave_seconds = config.WAVE_INTERVAL_SECONDS
    waves.advance(window, group, make_cash())

    fresh = WaveSystem(window, pygame.sprite.Group(), make_cash())

    assert fresh.wave_count == 0
