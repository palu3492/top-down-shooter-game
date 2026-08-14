"""Guns as data, and what a loaded one does.

The firing and reloading cases are the ones `test_gun_data.py` already held --
the point of this ticket is that they still hold with the four hand-written
reload branches replaced by one, and with the literal `60` gone from all of
them.
"""

import math

import pygame
import pytest

from shooter import config, items
from shooter.assets import load_image
from shooter.entities.projectiles import Shot, Swing
from shooter.entities.zombie import Zombie
from shooter.ui import hud
from shooter.ui.anchor import inside
from shooter.ui.hud import WeaponPanel
from shooter.weapons import (
    NO_AMMO,
    RELOAD,
    KNIFE,
    M16,
    Blade,
    RIFLE_ROUNDS,
    Gun,
    UnknownWeaponError,
    Weapon,
    equip,
    weapon,
    weapon_ids,
)


@pytest.fixture
def gun():
    return Gun()


# ----------------------------------------------------------------------
# Firing and reloading
# ----------------------------------------------------------------------


def test_starts_with_a_full_clip_and_two_spares(gun):
    assert (gun.loaded, gun.reserve) == (60, 120)


def test_firing_consumes_one_round(gun):
    assert gun.fire() is None
    assert (gun.loaded, gun.reserve) == (59, 120)


def test_emptying_the_clip_triggers_an_automatic_reload(gun):
    for _ in range(59):
        assert gun.fire() is None
    assert gun.loaded == 1

    assert gun.fire() == RELOAD
    assert (gun.loaded, gun.reserve) == (60, 60)


def test_firing_every_round_ends_in_no_ammo(gun):
    shots = 0
    while gun.status != NO_AMMO:
        if gun.ready:
            gun.fire()
            shots += 1
        else:
            gun.tick(gun.weapon.reload_seconds)
        assert shots < 1000, "the gun never ran dry"

    assert (gun.loaded, gun.reserve) == (0, 0)
    assert shots == 180


def test_manual_reload_tops_up_a_partial_clip(gun):
    gun.loaded = 30

    assert gun.manual_reload() == RELOAD
    assert (gun.loaded, gun.reserve) == (60, 90)


def test_manual_reload_with_too_little_reserve_takes_what_is_left(gun):
    gun.loaded = 30
    gun.reserve = 10

    assert gun.manual_reload() == RELOAD
    assert (gun.loaded, gun.reserve) == (40, 0)


def test_manual_reload_on_an_empty_reserve_and_partial_clip_is_a_no_op(gun):
    gun.loaded = 30
    gun.reserve = 0

    assert gun.manual_reload() is None
    assert (gun.loaded, gun.reserve) == (30, 0)


def test_manual_reload_with_nothing_left_reports_no_ammo(gun):
    gun.loaded = 0
    gun.reserve = 0

    assert gun.manual_reload() == NO_AMMO


def test_a_full_clip_is_never_overfilled(gun):
    """One expression replaces four branches, so it has to be the one that
    cannot take rounds out of a clip that is already full."""
    assert gun.manual_reload() == RELOAD
    assert (gun.loaded, gun.reserve) == (60, 120)


def test_reload_counts_down_then_clears(gun):
    dt = config.SIM_DT
    assert gun.locked_for == 0, "a fresh gun is not reloading"

    gun.loaded = 0
    gun.reload()
    assert gun.locked_for == config.RELOAD_SECONDS

    elapsed = 0.0
    while gun.tick(dt) == RELOAD:
        elapsed += dt
        assert elapsed < config.RELOAD_SECONDS * 5, "the reload never finished"

    assert elapsed == pytest.approx(config.RELOAD_SECONDS, abs=dt)
    assert gun.locked_for == 0
    assert gun.ready


def test_two_guns_do_not_share_ammo(gun):
    other = Gun()
    gun.fire()

    assert other.loaded == 60


# ----------------------------------------------------------------------
# The clip size is a number in one place
# ----------------------------------------------------------------------


def test_the_clip_size_setting_is_actually_obeyed(monkeypatch):
    """`reload_ammo` had `60` written into it in five places while the clip
    size was `config.CLIP_SIZE`. Changing the setting gave a gun that started
    with eight rounds and reloaded itself to sixty."""
    monkeypatch.setattr(config, "CLIP_SIZE", 8)
    gun = Gun()
    assert gun.loaded == 8

    gun.loaded = 0
    gun.reload()

    assert gun.loaded == 8
    assert gun.reserve == config.RESERVE_SIZE - 8


def test_a_short_reserve_still_only_fills_what_there_is(monkeypatch):
    monkeypatch.setattr(config, "CLIP_SIZE", 8)
    gun = Gun()
    gun.loaded = 2
    gun.reserve = 3

    gun.reload()

    assert (gun.loaded, gun.reserve) == (5, 0)


# ----------------------------------------------------------------------
# The table
# ----------------------------------------------------------------------


def test_the_knife_and_the_rifle_are_what_exist():
    assert weapon_ids() == (KNIFE.id, M16.id)


def test_a_weapon_carries_the_numbers_that_make_it_itself():
    rifle = weapon(M16.id)
    assert rifle.clip == config.CLIP_SIZE
    assert rifle.reserve == config.RESERVE_SIZE
    assert rifle.damage == config.BULLET_DAMAGE
    assert rifle.reload_seconds == config.RELOAD_SECONDS
    assert rifle.sprite == "HUD/gunAK47.png"
    assert rifle.ammo is RIFLE_ROUNDS


def test_a_weapon_is_an_item_the_backpack_can_hold():
    assert items.item(M16.id) is M16
    assert M16.kind == items.WEAPON
    assert M16.stack == 1

    assert items.item(RIFLE_ROUNDS.id) is RIFLE_ROUNDS
    assert RIFLE_ROUNDS.kind == items.AMMO


def test_a_weapon_nothing_declared_is_an_error():
    with pytest.raises(UnknownWeaponError):
        weapon("railgun")


def test_the_table_is_not_frozen_at_import(monkeypatch):
    """A weapon built once at import would go on reporting the reload time it
    read when the module loaded, and `RELOAD_SECONDS` is a setting the player
    can change -- which is the import-bound copy AT23's guard refuses."""
    monkeypatch.setattr(config, "RELOAD_SECONDS", 4.0)
    assert weapon(M16.id).reload_seconds == 4.0


def test_a_gun_can_be_asked_for_by_name_or_by_item():
    assert Gun(M16).weapon.id == M16.id
    assert Gun(M16.id).weapon.id == M16.id
    assert Gun(weapon(M16.id)).weapon.id == M16.id


def test_a_gun_deals_its_weapons_damage(gun):
    assert gun.damage == config.BULLET_DAMAGE


# ----------------------------------------------------------------------
# The readout
# ----------------------------------------------------------------------

SHOTGUN = Weapon(
    item=items.Item("test-shotgun", "Test Shotgun", items.WEAPON),
    ammo=items.Item("test-shells", "Test Shells", items.AMMO, stack=40),
    sprite="HUD/gunShotty.png",
    clip=8,
    reserve=24,
    damage=25,
    reload_seconds=1.5,
)


class Recorder(pygame.Surface):
    """A screen that remembers what was drawn onto it."""

    def __init__(self, size):
        super().__init__(size)
        self.drawn = {}

    @property
    def sources(self):
        return list(self.drawn.values())

    def blit(self, source, dest, *args, **kwargs):
        self.drawn[tuple(dest)[:2]] = source
        return super().blit(source, dest, *args, **kwargs)


def test_the_readout_draws_the_equipped_guns_sprite(display, window):
    """The panel used to load one gun by name in its constructor, which
    looked right while there was one gun and is exactly what AT39 needs to stop
    being true before it can equip a second."""
    screen = Recorder(window)

    WeaponPanel(window).draw(screen, Gun(SHOTGUN))

    assert load_image(SHOTGUN.sprite) in screen.sources
    assert load_image(weapon(M16.id).sprite) not in screen.sources


def test_the_readout_reports_the_gun_it_is_given(display, window):
    gun = Gun(SHOTGUN)
    assert (gun.loaded, gun.reserve) == (8, 24)
    assert gun.damage == 25


def test_the_clip_and_the_reserve_each_go_in_their_own_place(display, window):
    """Both numbers are drawn on the same panel in the same colour, so swapping
    them changes nothing about where anything lands -- only what it says."""
    screen = Recorder(window)

    WeaponPanel(window).draw(screen, Gun(SHOTGUN))

    panel = hud.BOTTOM_RIGHT.rect(window)
    assert _pixels(screen.drawn[inside(panel, hud.CLIP_READOUT)]) == _pixels(
        pygame.font.Font(None, 55).render("8", True, config.WHITE)
    )
    assert _pixels(screen.drawn[inside(panel, hud.RESERVE_READOUT)]) == _pixels(
        pygame.font.Font(None, 44).render("24", True, config.WHITE)
    )


def _pixels(surface):
    return (surface.get_size(), pygame.image.tobytes(surface, "RGBA"))


# ----------------------------------------------------------------------
# The knife
# ----------------------------------------------------------------------


def test_a_knife_has_no_ammunition_at_all():
    """`None` rather than zero: a knife does not have an empty magazine, it
    has no magazine, and the readout has to tell those apart."""
    knife = equip(KNIFE)

    assert isinstance(knife, Blade)
    assert (knife.loaded, knife.reserve) == (None, None)


def test_a_knife_never_runs_out_and_never_reloads():
    knife = equip(KNIFE)

    for _ in range(500):
        assert knife.fire() is None

    assert knife.manual_reload() is None
    assert knife.tick(config.SIM_DT) is None


def test_a_knife_is_a_tool_the_backpack_can_hold():
    assert items.item(KNIFE.id) is KNIFE
    assert KNIFE.kind == items.TOOL


def test_equipping_builds_whichever_kind_was_asked_for():
    assert isinstance(equip(KNIFE), Blade)
    assert isinstance(equip(M16), Gun)
    assert isinstance(equip("knife"), Blade)
    assert isinstance(equip("m16"), Gun)


def test_a_knife_swings_and_a_rifle_shoots():
    """The whole difference between the two, in the one call the session
    makes. Melee is not a gun with range zero -- it produces something that
    does not travel."""
    swing = equip(KNIFE).attack((0, 0), (1, 0), 50)
    shot = equip(M16).attack((0, 0), (1, 0), 20)

    assert isinstance(swing, Swing)
    assert isinstance(shot, Shot)
    assert not hasattr(swing, "SPEED")


# ----------------------------------------------------------------------
# What a swing reaches
# ----------------------------------------------------------------------


def zombie_at(cash, x, y):
    made = Zombie((1080, 720), cash)
    made.rect.center = (x, y)
    return made


def swing_at(zombies, aim=(1, 0), damage=config.KNIFE_DAMAGE):
    """One swing from the origin, resolved the way a step resolves it."""
    hit = Swing(
        0, 0, *aim, damage=damage, reach=config.KNIFE_REACH, arc=config.KNIFE_ARC
    )
    group = pygame.sprite.Group(*zombies)
    pygame.sprite.Group(hit).update(0, 0, group, config.SIM_DT)
    return hit


def test_a_swing_hits_what_is_in_front_and_close(display, cash):
    near = zombie_at(cash, config.KNIFE_REACH - 20, 0)

    swing_at([near])

    assert near.zombie_health == config.ZOMBIE_HEALTH - config.KNIFE_DAMAGE


def test_a_swing_cannot_touch_what_is_out_of_reach(display, cash):
    far = zombie_at(cash, config.KNIFE_REACH + 20, 0)

    swing_at([far])

    assert far.zombie_health == config.ZOMBIE_HEALTH


def test_a_swing_does_not_hit_what_is_behind_the_player(display, cash):
    """Short reach is only half of it. A knife that hits in every direction is
    a nuke with a small radius."""
    behind = zombie_at(cash, -(config.KNIFE_REACH - 20), 0)

    swing_at([behind], aim=(1, 0))

    assert behind.zombie_health == config.ZOMBIE_HEALTH


def test_a_swing_reaches_whatever_it_is_pointed_at(display, cash):
    above = zombie_at(cash, 0, -(config.KNIFE_REACH - 20))

    swing_at([above], aim=(0, 1))

    assert above.zombie_health == config.ZOMBIE_HEALTH - config.KNIFE_DAMAGE


def test_two_swings_put_a_zombie_down(display, cash):
    close = zombie_at(cash, 60, 0)

    swing_at([close])
    swing_at([close])

    assert close.zombie_health <= 0
    assert not close.alive()


def test_one_swing_cuts_everything_it_sweeps(display, cash):
    crowd = [zombie_at(cash, 60, 0), zombie_at(cash, 40, 40), zombie_at(cash, 90, -30)]

    swing_at(crowd)

    assert all(z.zombie_health < config.ZOMBIE_HEALTH for z in crowd)


def test_a_swing_lasts_one_step_and_no_longer(display, cash):
    """It is a moment, not a projectile: nothing to travel, nothing to expire
    off screen, nothing left in the group to update again."""
    hit = swing_at([])

    assert not hit.alive()


def test_the_readout_shows_no_ammunition_for_a_knife(display, window):
    """A knife with `0 / 0` beside it reads as a gun that has run out."""
    screen = Recorder(window)

    WeaponPanel(window).draw(screen, equip(KNIFE))

    panel = hud.BOTTOM_RIGHT.rect(window)
    assert inside(panel, hud.CLIP_READOUT) not in screen.drawn
    assert inside(panel, hud.RESERVE_READOUT) not in screen.drawn


def test_the_readout_names_a_weapon_that_has_no_picture(display, window):
    """There is no knife art. Drawing nothing at all would leave the corner of
    the screen looking broken, so it says what is held instead."""
    screen = Recorder(window)

    WeaponPanel(window).draw(screen, equip(KNIFE))

    panel = hud.BOTTOM_RIGHT.rect(window)
    assert _pixels(screen.drawn[inside(panel, hud.GUN_ICON)]) == _pixels(
        pygame.font.Font(None, 40).render("KNIFE", True, config.WHITE)
    )


def test_a_knife_reads_its_reach_from_config(monkeypatch):
    monkeypatch.setattr(config, "KNIFE_REACH", 999)
    monkeypatch.setattr(config, "KNIFE_DAMAGE", 12)

    knife = equip(KNIFE)

    assert knife.weapon.reach == 999
    assert knife.damage == 12


def test_a_knife_reads_its_arc_from_config_too(monkeypatch):
    """A dataclass field default is evaluated once, when the class is created,
    so `arc: float = config.KNIFE_ARC` was an import-bound copy while `reach`
    and `damage` beside it were live -- the exact thing `weapon()` exists to
    avoid."""
    monkeypatch.setattr(config, "KNIFE_ARC", 20)

    assert equip(KNIFE).weapon.arc == 20


def test_a_swing_is_given_its_arc_rather_than_assuming_one(monkeypatch):
    """`Swing`'s own default had the same problem, and the tests leaned on it."""
    monkeypatch.setattr(config, "KNIFE_ARC", 20)
    knife = equip(KNIFE)

    swing = knife.attack((0, 0), (1, 0), 10)

    assert swing.arc == math.radians(20)
