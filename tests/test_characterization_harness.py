"""Small deterministic tools used by migration characterization tests."""

import pygame

from shooter import config
from shooter.entities.powerups import PowerUps
from shooter.entities.zombie import Zombie
from shooter.weapons import SHOTGUN, Gun


def test_fixed_steps_advance_exactly(advance_steps):
    seen = []

    elapsed = advance_steps(seen.append, 12)

    assert seen == [config.SIM_DT] * 12
    assert elapsed == 12 * config.SIM_DT


def test_input_samples_do_not_poll_pygame(input_frame):
    sampled = input_frame(pygame.K_w, pygame.K_r, pointer=(18, 27), trigger=True)

    assert sampled.pressed[pygame.K_w] is True
    assert sampled.pressed[pygame.K_r] is True
    assert sampled.pressed[pygame.K_s] is False
    assert sampled.pointer == (18, 27)
    assert sampled.trigger is True


def test_seeded_sources_are_isolated_and_repeatable(seeded_rng):
    first = seeded_rng(7429)
    second = seeded_rng(7429)

    assert [first.random() for _ in range(5)] == [second.random() for _ in range(5)]


def test_zombie_construction_uses_the_supplied_source(window, cash, seeded_rng):
    first = Zombie(window, cash, rng=seeded_rng(31))
    second = Zombie(window, cash, rng=seeded_rng(31))

    assert first.pace == second.pace
    assert first.get_position() == second.get_position()


def test_weapon_spread_uses_the_supplied_source(seeded_rng):
    first = Gun(SHOTGUN, rng=seeded_rng(91))
    second = Gun(SHOTGUN, rng=seeded_rng(91))

    first_shots = first.attack((0, 0), (100, 0), first.damage)
    second_shots = second.attack((0, 0), (100, 0), second.damage)

    assert [shot.small_change_y for shot in first_shots] == [
        shot.small_change_y for shot in second_shots
    ]


def test_powerup_selection_uses_the_supplied_source(seeded_rng):
    first = PowerUps(rng=seeded_rng(18))
    second = PowerUps(rng=seeded_rng(18))

    assert first.powerup_selected == second.powerup_selected
