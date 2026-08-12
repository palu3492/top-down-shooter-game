"""Rendering between simulation steps.

The rule carried over from AT16: `rect` is simulation state that collision
reads, so drawing must never write to it. These tests pin both the maths and
that rule.
"""

import pygame
import pytest

from shooter import config
from shooter.entities.powerups import PowerUps
from shooter.entities.projectiles import (
    Grenade,
    GrenadeDetonation,
    Shot,
    StunDetonation,
    StunGrenade,
)
from shooter.entities.zombie import Zombie
from shooter.render import Interpolated, blit_group, lerp


@pytest.fixture
def movers(window, cash):
    return {
        "Zombie": Zombie(window, cash),
        "Shot": Shot(0, 0, 1, 1),
        "Grenade": Grenade(0, 0, 40, 40),
        "StunGrenade": StunGrenade(0, 0, 40, 40),
        "GrenadeDetonation": GrenadeDetonation(10, 20),
        "StunDetonation": StunDetonation(10, 20),
        "PowerUps": PowerUps(),
    }


def test_lerp_endpoints():
    assert lerp(10, 20, 0.0) == 10
    assert lerp(10, 20, 1.0) == 20
    assert lerp(10, 20, 0.5) == 15


@pytest.mark.parametrize(
    "name",
    [
        "Zombie",
        "Shot",
        "Grenade",
        "StunGrenade",
        "GrenadeDetonation",
        "StunDetonation",
        "PowerUps",
    ],
)
def test_every_mover_is_interpolated(movers, name):
    entity = movers[name]

    assert isinstance(entity, Interpolated)
    assert hasattr(entity, "world_x") and hasattr(entity, "world_y")
    assert hasattr(entity, "prev_x") and hasattr(entity, "prev_y")


def test_alpha_zero_draws_where_it_was(window, cash):
    zombie = Zombie(window, cash)
    zombie.set_position(500, 600)
    zombie.remember_position()
    zombie.set_position(900, 1000)

    assert zombie.draw_position(0, 0, 0.0) == (500, 600)


def test_alpha_one_draws_where_it_is(window, cash):
    zombie = Zombie(window, cash)
    zombie.set_position(500, 600)
    zombie.remember_position()
    zombie.set_position(900, 1000)

    assert zombie.draw_position(0, 0, 1.0) == (900, 1000)


def test_half_alpha_draws_between(window, cash):
    zombie = Zombie(window, cash)
    zombie.set_position(500, 600)
    zombie.remember_position()
    zombie.set_position(900, 1000)

    assert zombie.draw_position(0, 0, 0.5) == (700, 800)


def test_the_camera_offsets_the_drawn_position(window, cash):
    zombie = Zombie(window, cash)
    zombie.set_position(500, 600)
    zombie.remember_position()

    assert zombie.draw_position(-100, 25, 1.0) == (400, 625)


def test_drawing_never_moves_the_collision_rect(display, window, cash, movers):
    """The AT16 lesson: rect is simulation state, drawing must not touch it."""
    before = {name: e.rect.topleft for name, e in movers.items()}

    for entity in movers.values():
        entity.draw_position(-250, 400, 0.5)
    group = pygame.sprite.Group(*movers.values())
    blit_group(display, group, -250, 400, 0.5)

    assert {name: e.rect.topleft for name, e in movers.items()} == before


def test_a_moving_zombie_is_drawn_between_its_steps(window, cash):
    zombie = Zombie(window, cash)
    zombie.set_position(2000, 2000)
    zombie.move_position(0, 0)

    zombie.move_toward_center(0, 0, config.SIM_DT)
    start = zombie.draw_position(0, 0, 0.0)
    end = zombie.draw_position(0, 0, 1.0)
    middle = zombie.draw_position(0, 0, 0.5)

    assert start != end
    assert min(start[0], end[0]) <= middle[0] <= max(start[0], end[0])


def test_render_and_simulation_rates_are_independent():
    assert config.FPS != config.SIM_HZ
    assert config.SIM_DT == 1 / config.SIM_HZ
