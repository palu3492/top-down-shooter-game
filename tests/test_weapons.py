"""Guns as data, and what a loaded one does.

The firing and reloading cases are the ones `test_gun_data.py` already held --
the point of this ticket is that they still hold with the four hand-written
reload branches replaced by one, and with the literal `60` gone from all of
them.
"""

import pygame
import pytest

from shooter import config, items
from shooter.assets import load_image
from shooter.ui import hud
from shooter.ui.anchor import inside
from shooter.ui.hud import GunPanel
from shooter.weapons import (
    NO_AMMO,
    RELOAD,
    M16,
    RIFLE_ROUNDS,
    Gun,
    UnknownWeaponError,
    Weapon,
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
    while gun.fire() != NO_AMMO:
        shots += 1
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
    assert gun.reload_seconds == config.RELOAD_SECONDS

    for _ in range(int(config.RELOAD_SECONDS * config.SIM_HZ)):
        assert gun.reloading(dt) == RELOAD

    assert gun.reloading(dt) is None
    assert gun.reload_seconds == config.RELOAD_SECONDS


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


def test_the_rifle_is_the_gun_that_exists():
    assert weapon_ids() == (M16.id,)


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

    GunPanel(window).draw(screen, Gun(SHOTGUN))

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

    GunPanel(window).draw(screen, Gun(SHOTGUN))

    panel = hud.BOTTOM_RIGHT.rect(window)
    assert _pixels(screen.drawn[inside(panel, hud.CLIP_READOUT)]) == _pixels(
        pygame.font.Font(None, 55).render("8", True, config.WHITE)
    )
    assert _pixels(screen.drawn[inside(panel, hud.RESERVE_READOUT)]) == _pixels(
        pygame.font.Font(None, 44).render("24", True, config.WHITE)
    )


def _pixels(surface):
    return (surface.get_size(), pygame.image.tobytes(surface, "RGBA"))
