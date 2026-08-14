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

from shooter import config, game, weapons
from shooter.entities import powerups
from shooter.entities.projectiles import LETHAL, Shot, Swing
from shooter.session import Session, collect_powerup
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
    arm(first).equipped.fire()

    second = Session(Viewport(WINDOW))

    assert second.human.get_health() == config.PLAYER_HEALTH
    assert second.cash.cash_amount == 0
    assert arm(second).equipped.loaded == config.CLIP_SIZE
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


def arm(session):
    """Hold the rifle. The knife is what a session starts with now."""
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
    return session


def test_shooting_spends_a_bullet(session):
    arm(session)
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(session.bullets) == 1
    assert session.equipped.loaded == config.CLIP_SIZE - 1


def test_a_bullet_carries_the_damage_the_weapon_declares(display, monkeypatch):
    """Damage was read from a copy `projectiles` bound at import. Putting it in
    the weapon table is only worth anything if the shot actually reads it."""
    monkeypatch.setattr(config, "BULLET_DAMAGE", 77)
    session = arm(Session(Viewport(WINDOW)))
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert session.equipped.damage == 77
    assert [shot.damage for shot in session.bullets] == [77]


@pytest.mark.parametrize("button", [2, 3, 4, 5])
def test_only_the_left_button_fires(session, button):
    """Firing ran on any `MOUSEBUTTONDOWN` with no check at all, so a
    right-click, a middle-click and both side buttons each emptied a round --
    and `E` being the interaction key means those buttons have jobs coming."""
    arm(session)
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button))

    assert len(session.bullets) == 0
    assert session.equipped.loaded == config.CLIP_SIZE


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
    assert tuple(session.weapon_display.window) == (1920, 1080)
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
    session = arm(Session(Viewport(WINDOW)))

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


# ----------------------------------------------------------------------
# Holding one thing at a time
# ----------------------------------------------------------------------


def press_key(session, key):
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def test_a_new_session_starts_with_the_knife_in_hand(session):
    assert session.equipped.weapon.id == weapons.KNIFE.id
    assert session.equipped.loaded is None


def test_the_number_keys_choose_what_is_held(session):
    press_key(session, pygame.K_2)
    assert session.equipped.weapon.id == weapons.M16.id

    press_key(session, pygame.K_1)
    assert session.equipped.weapon.id == weapons.KNIFE.id


def test_a_slot_with_nothing_in_it_changes_nothing(session):
    """`3`, `4` and `5` are the shotgun, sniper and crossbow, and none of them
    have been built. Pressing one must not put an empty hand on the screen."""
    press_key(session, pygame.K_2)

    for key in (pygame.K_3, pygame.K_4, pygame.K_5):
        press_key(session, key)
        assert session.equipped.weapon.id == weapons.M16.id


def test_swinging_the_knife_makes_no_bullet(session):
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(session.bullets) == 1
    assert isinstance(next(iter(session.bullets)), Swing)


def test_what_is_held_decides_what_shooting_does(session):
    """The one line the session runs is the same for both; only the weapon
    differs. That is the seam the armoury is built on."""
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    swung = next(iter(session.bullets))

    session.bullets.empty()
    press_key(session, pygame.K_2)
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    fired = next(iter(session.bullets))

    assert isinstance(swung, Swing)
    assert isinstance(fired, Shot)


def test_a_knife_swing_spends_no_ammunition(session):
    session.aim_at((900, 300))
    for _ in range(20):
        session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    press_key(session, pygame.K_2)

    assert session.equipped.loaded == config.CLIP_SIZE
    assert session.equipped.reserve == config.RESERVE_SIZE


def steps(session, seconds):
    idle = dict.fromkeys(range(512), False)
    for _ in range(int(seconds * config.SIM_HZ)):
        session.step(idle, config.SIM_DT)


def test_a_reload_survives_being_put_away(session):
    """The lockout is the entire cost of reloading, because `reload` puts the
    rounds in the clip the moment it is called. Clearing it on a weapon change
    let the player cancel every reload by tapping `1` then `2`."""
    arm(session)
    press_key(session, pygame.K_r)
    assert session.ammo_count == weapons.RELOAD

    press_key(session, pygame.K_1)
    press_key(session, pygame.K_2)

    assert session.ammo_count == weapons.RELOAD


def test_a_cancelled_reload_still_blocks_the_shot(session):
    arm(session)
    press_key(session, pygame.K_r)
    press_key(session, pygame.K_1)
    press_key(session, pygame.K_2)
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(session.bullets) == 0


def test_a_reload_finishes_while_the_knife_is_out(session):
    """It goes on reloading in the holster. Pausing it would only move the
    cancel from one keystroke to two."""
    arm(session)
    press_key(session, pygame.K_r)
    press_key(session, pygame.K_1)

    steps(session, config.RELOAD_SECONDS + 0.1)
    press_key(session, pygame.K_2)

    assert session.ammo_count is None


def test_the_reload_after_a_swap_is_not_a_short_one(session):
    """The countdown was left stranded wherever the swap caught it, so the
    next reload was short by however much had already elapsed -- and repeated
    interrupts ratcheted it down."""
    arm(session)
    press_key(session, pygame.K_r)
    steps(session, config.RELOAD_SECONDS / 2)
    press_key(session, pygame.K_1)
    press_key(session, pygame.K_2)
    steps(session, config.RELOAD_SECONDS)

    press_key(session, pygame.K_r)
    waited = 0.0
    while session.ammo_count == weapons.RELOAD:
        steps(session, config.SIM_DT)
        waited += config.SIM_DT
        assert waited < config.RELOAD_SECONDS * 5, "the reload never finished"

    assert waited == pytest.approx(config.RELOAD_SECONDS, abs=2 * config.SIM_DT)


def test_an_empty_gun_fires_nothing_however_often_it_is_swapped(session):
    """The projectile was spawned before the weapon was asked whether it could
    attack, so the `NO_AMMO` latch was the only guard -- and swapping cleared
    it, making ammunition unlimited for two keystrokes."""
    arm(session)
    session.equipped.loaded = 0
    session.equipped.reserve = 0
    session.aim_at((900, 300))

    for _ in range(5):
        session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        press_key(session, pygame.K_1)
        press_key(session, pygame.K_2)

    assert len(session.bullets) == 0


def test_the_last_round_leaves_the_gun_saying_it_is_empty(session):
    """Spending the final round with nothing in reserve used to report
    nothing at all, which left one more click able to spawn a bullet."""
    arm(session)
    session.equipped.loaded = 1
    session.equipped.reserve = 0
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    assert len(session.bullets) == 1
    assert session.ammo_count == weapons.NO_AMMO

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    assert len(session.bullets) == 1


def test_the_knife_is_never_locked_out_by_the_rifle(session):
    """Status belongs to the weapon, so a reloading rifle must not stop a
    knife that has nothing to reload."""
    arm(session)
    press_key(session, pygame.K_r)
    press_key(session, pygame.K_1)
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert session.ammo_count is None
    assert len(session.bullets) == 1


def test_reaching_for_what_is_already_in_hand_does_nothing(session):
    arm(session)
    held = session.equipped
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    spent = session.equipped.loaded

    press_key(session, pygame.K_2)

    assert session.equipped is held, "a fresh gun would have a full clip again"
    assert session.equipped.loaded == spent


def test_instakill_makes_the_knife_lethal_too(session):
    session.instakill_seconds = 5.0
    session.aim_at((900, 300))

    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert next(iter(session.bullets)).damage == LETHAL


def test_max_ammo_refills_a_rifle_that_is_not_in_hand(display):
    """Walking over a pickup with the knife out used to refill the knife,
    which is to say nothing at all."""
    session = Session(Viewport(WINDOW))
    rifle = session.carried[1]
    rifle.reserve = 3

    collect_powerup(powerups.MAX_AMMO, session.human, session.zombies, session.carried)

    assert rifle.reserve == rifle.weapon.reserve


def test_a_frame_draws_with_a_knife_in_hand_and_a_swing_pending(session, display):
    """A swing sits in the group between the click and the step that resolves
    it, so it gets drawn once -- with no art and no ammunition behind it."""
    session.aim_at((900, 300))
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    session.draw(display, 0.5)
    session.step(dict.fromkeys(range(512), False), config.SIM_DT)
    session.draw(display, 0.5)

    assert len(session.bullets) == 0
