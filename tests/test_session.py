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
    first.gun.fire()

    second = Session(Viewport(WINDOW))

    assert second.human.get_health() == config.PLAYER_HEALTH
    assert second.cash.cash_amount == 0
    assert second.gun.loaded == config.CLIP_SIZE
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
    assert session.gun.loaded == config.CLIP_SIZE - 1


def test_a_bullet_carries_the_damage_the_weapon_declares(display, monkeypatch):
    """Damage was read from a copy `projectiles` bound at import. Putting it in
    the weapon table is only worth anything if the shot actually reads it."""
    monkeypatch.setattr(config, "BULLET_DAMAGE", 77)
    session = Session(Viewport(WINDOW))
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert session.gun.damage == 77
    assert [shot.damage for shot in session.bullets] == [77]


@pytest.mark.parametrize("button", [2, 3, 4, 5])
def test_only_the_left_button_fires(session, button):
    """Firing ran on any `MOUSEBUTTONDOWN` with no check at all, so a
    right-click, a middle-click and both side buttons each emptied a round --
    and `E` being the interaction key means those buttons have jobs coming."""
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button))

    assert len(session.bullets) == 0
    assert session.gun.loaded == config.CLIP_SIZE


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


def test_everything_in_a_session_follows_a_resize(display):
    """The earlier version of this test passed a fresh Viewport and checked only
    `session.window` and the player -- the two things that did update -- while
    the readouts, the health bar and every zombie silently kept the old size.
    """
    window = Viewport(WINDOW)
    session = Session(window)
    zombie = next(iter(session.zombies))

    window.resize((1920, 1080))
    session.resize()

    assert session.window == (1920, 1080)
    assert session.human.rect.centerx == pytest.approx(960, abs=1)
    assert session.human.rect.centery == pytest.approx(540, abs=1)
    assert tuple(session.gun_display.window) == (1920, 1080)
    assert tuple(session.health_display.window_size) == (1920, 1080)
    assert tuple(zombie.window_size) == (1920, 1080), (
        "an existing zombie walks at half the window, so a stale size sends it "
        "at a point the player is not standing on"
    )


def test_resize_takes_no_window_to_pass_the_wrong_one(session):
    """There is only ever one viewport; accepting another would imply copies."""
    with pytest.raises(TypeError):
        session.resize(Viewport((1920, 1080)))


def test_the_opening_frame_aims_at_the_pointer(display, monkeypatch):
    """Input is handled before the loop first calls `aim_at`, so a click on the
    opening frame used to fire at atan2(0, 0) -- straight right."""
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (200, 360))
    session = Session(Viewport(WINDOW))

    assert session.aim != (0, 0)

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    bullet = next(iter(session.bullets))
    assert bullet.small_change_x < 0, "the pointer was left of centre"


def test_the_opening_aim_matches_a_later_sample(display, monkeypatch):
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (900, 100))
    session = Session(Viewport(WINDOW))
    opening = session.aim

    session.aim_at((900, 100))
    assert session.aim == opening


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
