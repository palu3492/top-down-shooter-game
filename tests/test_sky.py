"""The drifting sky.

Palette cycling: the picture never changes, only what its six colours mean. The
tests that matter are that it actually moves, that it comes back round, and that
moving costs nothing per frame -- an animation that rebuilds a full-screen
surface sixty times a second would be worse than a still image.
"""

import pygame
import pytest

from shooter.assets import load_image
from shooter.ui import sky, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def drifting(display):
    return sky.Sky(WINDOW)


def shades(surface):
    return {
        surface.get_at((x, y))[:3]
        for x in range(0, surface.get_width(), 7)
        for y in range(0, surface.get_height(), 7)
    }


def test_the_baked_art_holds_exactly_the_palette_being_cycled(display):
    """If the file and `DUSK` drift apart, `replace` silently misses a colour
    and part of the picture stops animating."""
    art = load_image(sky.ART)
    present = {
        art.get_at((x, y))[:3]
        for x in range(art.get_width())
        for y in range(art.get_height())
    }
    assert present <= set(sky.DUSK), sorted(present - set(sky.DUSK))


def test_every_palette_has_a_colour_for_every_other(display):
    for palette in (sky.DUSK, sky.NIGHT, sky.DAWN):
        assert len(palette) == len(sky.DUSK)


def test_the_cycle_starts_and_ends_at_the_painted_colours():
    assert sky.palette_at(0.0) == sky.DUSK
    assert sky.palette_at(1.0) == sky.DUSK


def test_night_is_held_rather_than_passed_through():
    """A moment of night would read as a flicker; it should be somewhere the
    menu sits for a while."""
    assert sky.palette_at(0.3) == sky.NIGHT
    assert sky.palette_at(0.45) == sky.NIGHT
    assert sky.palette_at(0.55) == sky.NIGHT


def test_the_sky_moves_between_keyframes():
    halfway = sky.palette_at(0.15)
    assert halfway != sky.DUSK
    assert halfway != sky.NIGHT
    for blended, night, dusk in zip(halfway, sky.NIGHT, sky.DUSK, strict=True):
        for channel, low, high in zip(blended, night, dusk, strict=True):
            assert min(low, high) <= channel <= max(low, high)


def test_the_cycle_comes_back_round():
    assert sky.palette_at(1.25) == sky.palette_at(0.25)


def test_the_picture_actually_changes_over_the_cycle(drifting):
    dusk = shades(drifting.at(0.0))
    night = shades(drifting.at(sky.CYCLE_SECONDS * 0.4))
    dawn = shades(drifting.at(sky.CYCLE_SECONDS * 0.8))

    assert dusk != night
    assert night != dawn
    assert dusk != dawn


def test_the_night_sky_is_darker_and_cooler(drifting):
    def warmth(surface):
        pixels = shades(surface)
        return sum(r - b for r, _, b in pixels) / len(pixels)

    assert warmth(drifting.at(0.0)) > warmth(drifting.at(sky.CYCLE_SECONDS * 0.4))


def test_it_returns_to_where_it_started(drifting):
    start = shades(drifting.at(0.0))
    assert shades(drifting.at(sky.CYCLE_SECONDS)) == start


# ----------------------------------------------------------------------
# Cost
# ----------------------------------------------------------------------


def test_a_frame_that_changes_nothing_rebuilds_nothing(drifting, monkeypatch):
    """The whole point of quantising the cycle into steps."""
    builds = []
    real = drifting._build
    monkeypatch.setattr(
        drifting, "_build", lambda phase: builds.append(phase) or real(phase)
    )

    drifting.at(0.0)
    assert len(builds) == 1

    for frame in range(60):
        drifting.at(frame / 600)  # a tenth of a second of frames
    assert len(builds) == 1, "the sky was rebuilt while it had not moved"


def test_it_rebuilds_when_the_step_changes(drifting):
    first = drifting.at(0.0)
    same = drifting.at(sky.CYCLE_SECONDS / sky.STEPS / 4)
    later = drifting.at(sky.CYCLE_SECONDS / sky.STEPS * 2)

    assert same is first, "within a step, the same surface is handed back"
    assert later is not first


def test_only_one_surface_is_kept(drifting):
    """At full size each is three megabytes, and only one is ever on screen."""
    for step in range(10):
        drifting.at(sky.CYCLE_SECONDS * step / sky.STEPS)
    assert isinstance(drifting.surface, pygame.Surface)
    assert drifting.surface is drifting.at(sky.CYCLE_SECONDS * 9 / sky.STEPS)


def test_the_sky_keeps_its_pixels_square(drifting):
    """Interpolating pixel art is what stops it looking like pixel art."""
    built = drifting.at(0.0)
    assert built.get_size() == WINDOW
    assert shades(built) <= set(sky.DUSK)


# ----------------------------------------------------------------------
# Wired into the scenes
# ----------------------------------------------------------------------


def test_the_menu_sky_advances_with_wall_time(display):
    from shooter.scenes import SceneStack

    stack = SceneStack(Viewport(WINDOW))
    scene = title.MainMenuScene(stack.window, stack.manager)
    stack.push(scene)

    assert scene.elapsed == 0.0
    stack.tick(0.5)
    assert scene.elapsed == 0.5
    stack.clear()


def test_the_splash_still_hands_over_while_the_sky_drifts(display):
    from shooter.scenes import SceneStack

    stack = SceneStack(Viewport(WINDOW))
    splash = title.SplashScene(stack.window, stack.manager)
    stack.push(splash)

    assert splash.tick(title.FADE_IN + title.HOLD) == title.MENU
    assert splash.elapsed > 0, "the sky needs the clock too"
    stack.clear()
