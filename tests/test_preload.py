"""Nothing reads from disk while the game is running.

Lazy caching is the right default and the wrong thing to discover mid-frame.
These tests spy on `pygame.image.load` itself rather than on any wrapper, so a
new sprite loaded through a new helper is caught just the same.
"""

import pygame
import pytest

from shooter import config, preload
from shooter.assets import (
    load_animation,
    load_image,
    load_sheet,
    load_sized,
)
from shooter.background import BackgroundSheet
from shooter.entities import powerups
from shooter.entities.powerups import PowerUps
from shooter.session import Session
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def reads(monkeypatch):
    """Every path pygame actually opens, however it was asked for."""
    seen = []
    real = pygame.image.load

    def spy(path, *args, **kwargs):
        seen.append(str(path).rsplit("Assets/", 1)[-1])
        return real(path, *args, **kwargs)

    monkeypatch.setattr(pygame.image, "load", spy)
    return seen


@pytest.fixture
def warmed(display):
    preload.preload()
    return preload


def pressed_nothing():
    return dict.fromkeys(range(512), False)


def play(session, frames=400):
    surface = pygame.Surface(WINDOW)
    pressed = pressed_nothing()
    pressed[pygame.K_d] = True
    session.aim_at((800, 300))
    for frame in range(frames):
        if frame == 5:
            session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        if frame == 10:
            session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
        if frame == 15:
            session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        if frame == 20:
            session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        session.step(pressed, config.SIM_DT)
        session.draw(surface, 0.0)


def test_building_a_session_reads_nothing(warmed, reads):
    Session(Viewport(WINDOW))
    assert reads == []


def test_playing_reads_nothing(warmed, reads):
    """The assertion the ticket exists for: a hitch cannot appear mid-frame if
    nothing opens a file mid-frame."""
    session = Session(Viewport(WINDOW))
    reads.clear()

    play(session)

    assert reads == [], f"{len(reads)} assets were read during play: {reads}"


@pytest.mark.parametrize(
    "kind", [powerups.INSTAKILL, powerups.NUKE, powerups.MAX_AMMO, powerups.MAX_HEALTH]
)
def test_every_powerup_kind_is_already_loaded(warmed, reads, monkeypatch, kind):
    """Only one of the four is built per session, so the other three would each
    be a first read at whatever moment they happened to spawn."""
    monkeypatch.setattr(powerups.random, "randint", lambda low, high: kind)
    PowerUps()
    assert reads == []


def test_a_second_session_reads_nothing(warmed, reads):
    first = Session(Viewport(WINDOW))
    reads.clear()

    second = Session(Viewport(WINDOW))

    assert reads == []
    assert second.background.sheet is first.background.sheet


def test_the_background_is_shared_rather_than_reloaded(warmed):
    """5000x5000 and 180ms: paid once for the process, not once per game."""
    assert (
        BackgroundSheet(preload.SHEETS[0]).sheet
        is BackgroundSheet(preload.SHEETS[0]).sheet
    )


def test_preload_can_be_called_twice(warmed, reads):
    preload.preload()
    assert reads == []


def test_every_listed_asset_exists(display):
    from shooter.assets import ASSETS_DIR

    for relative, _ in preload.SPRITES:
        assert (ASSETS_DIR / relative).is_file(), relative
    for relative in preload.SHEETS:
        assert (ASSETS_DIR / relative).is_file(), relative
    assert (ASSETS_DIR / preload.ZOMBIE_STILL).is_file()


def test_the_manifest_matches_what_a_cold_start_actually_needs(display):
    """Clears every cache, preloads, then plays -- so the list is checked
    against a genuinely cold process rather than one warmed by other tests."""
    for cache in (load_image, load_sheet, load_sized, load_animation):
        cache.cache_clear()

    preload.preload()

    seen = []
    real = pygame.image.load

    def spy(path, *args, **kwargs):
        seen.append(str(path).rsplit("Assets/", 1)[-1])
        return real(path, *args, **kwargs)

    pygame.image.load = spy
    try:
        play(Session(Viewport(WINDOW)))
    finally:
        pygame.image.load = real

    assert seen == [], f"missing from the manifest: {sorted(set(seen))}"


ASKED_BOTH_WAYS = (
    ("HUD/gunAK47.png", False),
    ("Projectiles/bullet.png", True),
)


@pytest.mark.parametrize(("relative", "alpha"), ASKED_BOTH_WAYS)
def test_a_default_argument_does_not_mint_a_second_copy(display, relative, alpha):
    """`functools.cache` keys on the call as written, so `load_image(path)` and
    `load_image(path, False)` were two entries, two reads and two surfaces.
    Call sites legitimately differ -- the gun readout omits the flag, the manifest
    passes it -- so the loaders normalise before the cache sees anything."""
    load_image.cache_clear()

    explicit = load_image(relative, alpha)
    implicit = load_image(relative) if alpha is False else load_image(relative, True)

    assert explicit is implicit
    assert load_image.cache_info().currsize == 1


def test_the_cache_does_not_grow_across_repeated_sessions(warmed):
    """AT29 builds one of these every time a game starts."""
    before = load_image.cache_info().currsize
    for _ in range(3):
        play(Session(Viewport(WINDOW)), frames=60)
    assert load_image.cache_info().currsize == before
