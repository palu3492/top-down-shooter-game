"""A game as an object.

The suite that already existed proves the refactor changed no behaviour. What
is worth testing here is what the refactor made *possible*: building a game,
throwing it away, building another, and having the second owe nothing to the
first.
"""

import ast
from pathlib import Path

import pygame
import pytest

from shooter import config, game
from shooter.session import Session
from shooter.viewport import Viewport

WINDOW = (1080, 720)


class CountingRules:
    """A stand-in for WaveSystem, to show the slot a campaign mode would fill."""

    def __init__(self, window, zombies, cash, visible):
        self.window = window
        self.advances = 0
        self.drawn = 0

    def advance(self, window, zombies, cash, dt, visible=None):
        self.advances += 1

    def draw(self, screen, window=None):
        self.drawn += 1


@pytest.fixture
def session(display):
    return Session(Viewport(WINDOW))


def pressed_nothing():
    return dict.fromkeys(range(512), False)


def test_a_game_can_be_built(session):
    assert session.human.alive()
    assert session.human.get_health() == config.PLAYER_HEALTH
    assert len(session.zombies) == config.WAVE_BASE


def test_two_games_share_nothing(display):
    first = Session(Viewport(WINDOW))
    first.human.remove_health(40)
    first.cash.increase_cash(500)
    first.gun.shooting_bullet()

    second = Session(Viewport(WINDOW))

    assert second.human.get_health() == config.PLAYER_HEALTH
    assert second.cash.cash_amount == 0
    assert second.gun.clip_size == config.CLIP_SIZE
    assert second.zombies is not first.zombies


def test_discarding_a_game_leaves_nothing_behind(display):
    """Sprite groups are the usual way state outlives its owner."""
    first = Session(Viewport(WINDOW))
    zombies = first.zombies
    del first

    second = Session(Viewport(WINDOW))
    assert second.zombies is not zombies
    assert len(second.zombies) == config.WAVE_BASE


def test_a_step_advances_the_world(session):
    before = [z.get_position() for z in session.zombies]
    for _ in range(10):
        session.step(pressed_nothing(), config.SIM_DT)
    assert [z.get_position() for z in session.zombies] != before


def test_walking_moves_the_camera(session):
    """`d` walks away from the origin. `a` from a standing start does nothing,
    because the camera clamps at the world edge and that is where it starts."""
    pressed = pressed_nothing()
    pressed[pygame.K_d] = True

    session.step(pressed, config.SIM_DT)

    assert session.camera_x < 0


def test_walking_into_the_world_edge_does_nothing(session):
    pressed = pressed_nothing()
    pressed[pygame.K_a] = True

    session.step(pressed, config.SIM_DT)

    assert session.camera_x == 0


def test_the_camera_is_clamped_to_the_world(session):
    pressed = pressed_nothing()
    pressed[pygame.K_d] = True
    for _ in range(2000):
        session.step(pressed, config.SIM_DT)

    assert session.camera_x >= -(config.WORLD[0] - WINDOW[0])


def test_shooting_spends_a_bullet(session):
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(session.bullets) == 1
    assert session.gun.clip_size == config.CLIP_SIZE - 1


def test_a_grenade_is_spent_when_thrown(session):
    before = session.grenade_data.grenade_amount
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))

    assert len(session.grenades) == 1
    assert session.grenade_data.grenade_amount == before - 1


def test_a_grenade_cannot_be_thrown_without_one(session):
    session.grenade_data.grenade_amount = 0
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
    assert len(session.grenades) == 0


def test_the_rules_are_a_collaborator(display):
    """`WaveSystem` is the freeplay rules; a campaign replaces it here."""
    session = Session(Viewport(WINDOW), rules=CountingRules)

    assert isinstance(session.rules, CountingRules)
    assert len(session.zombies) == 0

    session.step(pressed_nothing(), config.SIM_DT)
    assert session.rules.advances == 1


def test_drawing_does_not_advance_the_world(session):
    surface = pygame.Surface(WINDOW)
    session.step(pressed_nothing(), config.SIM_DT)
    before = [z.get_position() for z in session.zombies]

    for _ in range(5):
        session.draw(surface, 0.5)

    assert [z.get_position() for z in session.zombies] == before


def test_a_session_follows_a_resize(session):
    session.resize(Viewport((1920, 1080)))
    assert session.window == (1920, 1080)
    assert session.human.rect.centerx == pytest.approx(960, abs=1)


def test_world_state_holds_no_surfaces(session):
    """The save-game seam: numbers a future save file would need must not be
    tangled up with the surfaces used to draw them."""
    for name in ("camera_x", "camera_y", "instakill_seconds"):
        assert isinstance(getattr(session, name), int | float)

    for zombie in session.zombies:
        assert isinstance(zombie.zombie_x, int | float)
        assert isinstance(zombie.zombie_health, int | float)


def test_the_shell_no_longer_holds_the_world():
    """game_loop kept fifty locals; the point of the ticket is that it does not."""
    tree = ast.parse(Path(game.__file__).read_text())
    loop = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "game_loop"
    )
    assigned = {
        target.id
        for node in ast.walk(loop)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert len(assigned) < 20, sorted(assigned)
    assert not assigned & {"zombie_group", "bullets", "human", "camera_x", "camera_y"}
