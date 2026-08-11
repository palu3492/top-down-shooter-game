import pygame
import pytest

from shooter.systems.waves import Wave_System


@pytest.fixture
def group():
    return pygame.sprite.Group()


@pytest.fixture
def waves(group, window, make_cash):
    return Wave_System(window, group, make_cash())


def test_first_wave_spawns_five(waves, group):
    assert len(group) == 5


def test_timer_ticks_up_between_waves(waves, group, display, window, make_cash):
    waves.wave_control(display, window, group, make_cash())

    assert waves.Wave_Timer == 1


@pytest.mark.parametrize(
    "wave, expected",
    [(1, 6), (2, 9), (3, 14), (4, 21), (5, 30)],
)
def test_spawn_count_follows_five_plus_wave_squared(
    waves, group, display, window, make_cash, wave, expected
):
    waves.Wave_Count = wave - 1
    waves.Wave_Timer = 1500
    group.empty()

    waves.wave_control(display, window, group, make_cash())

    assert waves.Wave_Count == wave
    assert len(group) == expected


def test_spawning_resets_the_timer(waves, group, display, window, make_cash):
    waves.Wave_Timer = 1500

    waves.wave_control(display, window, group, make_cash())

    assert waves.Wave_Timer == 0


def test_two_wave_systems_do_not_share_progress(waves, group, display, window, make_cash):
    waves.Wave_Timer = 1500
    waves.wave_control(display, window, group, make_cash())

    fresh = Wave_System(window, pygame.sprite.Group(), make_cash())

    assert fresh.Wave_Count == 0
