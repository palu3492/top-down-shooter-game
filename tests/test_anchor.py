"""Anchored placement, and the HUD built on it.

The first half is arithmetic and enumerable. The second half holds two
properties that matter more than any individual number: the HUD is unchanged at
the resolution it was hand-tuned for, and every piece tracks its own corner at
every other one.
"""

import itertools

import pygame
import pytest

from shooter import config
from shooter.systems import waves as waves_module
from shooter.systems.waves import WaveSystem
from shooter.ui import hud
from shooter.ui.anchor import (
    BOTTOM,
    CENTRE,
    LEFT,
    MIDDLE,
    RIGHT,
    TOP,
    UnknownEdgeError,
    inside,
    place,
)

SIZE = (200, 100)
WINDOW = (1080, 720)
SIZES = [(1080, 720), (1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]


def test_the_top_left_corner_is_the_inset_itself():
    assert place(SIZE, WINDOW, LEFT, TOP, (40, 30)).topleft == (40, 30)


def test_the_bottom_right_corner_is_measured_inward():
    placed = place(SIZE, WINDOW, RIGHT, BOTTOM, (40, 30))
    assert WINDOW[0] - placed.right == 40
    assert WINDOW[1] - placed.bottom == 30


def test_centring_leaves_equal_margins():
    placed = place(SIZE, WINDOW, CENTRE, MIDDLE)
    assert placed.left == WINDOW[0] - placed.right
    assert placed.top == WINDOW[1] - placed.bottom


@pytest.mark.parametrize(
    ("horizontal", "vertical"),
    list(itertools.product((LEFT, CENTRE, RIGHT), (TOP, MIDDLE, BOTTOM))),
)
@pytest.mark.parametrize("window", SIZES)
def test_placing_never_changes_the_size(horizontal, vertical, window):
    """Scaling is not layout: an anchored element keeps its own dimensions."""
    assert place(SIZE, window, horizontal, vertical).size == SIZE


@pytest.mark.parametrize("window", SIZES)
def test_a_corner_element_keeps_its_distance_from_that_corner(window):
    placed = place(SIZE, window, RIGHT, BOTTOM, (40, 30))
    assert (window[0] - placed.right, window[1] - placed.bottom) == (40, 30)


@pytest.mark.parametrize("window", SIZES)
def test_a_centred_element_stays_centred(window):
    placed = place(SIZE, window, CENTRE, TOP)
    assert placed.centerx == pytest.approx(window[0] / 2)


def test_an_unknown_edge_is_refused():
    with pytest.raises(UnknownEdgeError):
        place(SIZE, WINDOW, "middle-ish", TOP)
    with pytest.raises(UnknownEdgeError):
        place(SIZE, WINDOW, LEFT, "up")


def test_inside_measures_from_the_panel_not_the_window():
    panel = pygame.Rect(800, 600, 200, 100)
    assert inside(panel, (13, 57)) == (813, 657)


HISTORIC = {
    "blHUD": (40, 720 - 76),
    "brHUD": (1080 - 263, 720 - 162),
    "tmHUD": (1080 / 2.0 - 225, 0),
    "health": (70, 720 - 77),
    "meter": (480, 10),
    "clip": (1080 - 250, 720 - 105),
    "reserve": (1080 - 170, 720 - 102),
    "gun": (1080 - 125, 720 - 120),
    "cash": (400, 7),
}


def current_positions(display, window=WINDOW):
    bottom_left = hud.BOTTOM_LEFT.rect(window)
    bottom_right = hud.BOTTOM_RIGHT.rect(window)
    top_middle = hud.TOP_MIDDLE.rect(window)
    return {
        "blHUD": bottom_left.topleft,
        "brHUD": bottom_right.topleft,
        "tmHUD": top_middle.topleft,
        "health": inside(bottom_left, hud.HEALTH_READOUT),
        "meter": inside(top_middle, hud.HEALTH_METER),
        "clip": inside(bottom_right, hud.CLIP_READOUT),
        "reserve": inside(bottom_right, hud.RESERVE_READOUT),
        "gun": inside(bottom_right, hud.GUN_ICON),
        "cash": inside(top_middle, hud.CASH_READOUT),
    }


@pytest.mark.parametrize("name", HISTORIC)
def test_the_hud_is_unchanged_at_the_resolution_it_was_tuned_for(display, name):
    """Anchoring is meant to change what happens at *other* sizes. At 1080x720
    every piece must land on the pixel it always did."""
    placed = current_positions(display)[name]
    assert tuple(map(int, placed)) == tuple(map(int, HISTORIC[name]))


@pytest.mark.parametrize("window", SIZES)
def test_every_hud_panel_stays_inside_the_window(display, window):
    for panel in hud.PANELS:
        assert pygame.Rect((0, 0), window).contains(panel.rect(window))


@pytest.mark.parametrize("window", SIZES)
def test_the_bottom_right_panel_tracks_the_bottom_right(display, window):
    panel = hud.BOTTOM_RIGHT.rect(window)
    assert (window[0] - panel.right, window[1] - panel.bottom) == (40, 41)


@pytest.mark.parametrize("window", SIZES)
def test_the_top_panel_stays_centred(display, window):
    panel = hud.TOP_MIDDLE.rect(window)
    assert panel.centerx == pytest.approx(window[0] / 2)
    assert panel.top == 0


@pytest.mark.parametrize("window", SIZES)
def test_readouts_ride_with_the_panel_they_are_drawn_on(display, window):
    """The number and the artwork under it can never drift apart."""
    panel = hud.BOTTOM_RIGHT.rect(window)
    for offset in (hud.CLIP_READOUT, hud.RESERVE_READOUT, hud.GUN_ICON):
        left, top = inside(panel, offset)
        assert panel.left <= left <= panel.right
        assert panel.top <= top <= panel.bottom


def test_the_hud_panels_move_when_the_window_does(display):
    small = current_positions(display, (1080, 720))
    large = current_positions(display, (1920, 1080))
    assert small["brHUD"] != large["brHUD"]
    assert small["blHUD"][0] == large["blHUD"][0], "the left edge should not move"
    assert small["blHUD"][1] != large["blHUD"][1], "the bottom edge should"


@pytest.mark.parametrize("window", SIZES)
def test_the_wave_banner_is_centred_rather_than_pinned(display, window, cash):
    """It used to start at x=300 whatever the window was."""
    surface = pygame.Surface(window)
    waves = WaveSystem(window, pygame.sprite.Group(), cash)
    waves.draw(surface, window)

    banner = place(
        waves_module.BANNER_SIZE, window, CENTRE, TOP, waves_module.BANNER_INSET
    )
    assert banner.centerx == pytest.approx(window[0] / 2)
    assert pygame.Rect((0, 0), window).contains(banner)


def test_the_wave_banner_still_draws_at_the_default(display, cash):
    surface = pygame.Surface(config.WINDOW)
    waves = WaveSystem(config.WINDOW, pygame.sprite.Group(), cash)
    waves.draw(surface)
    assert surface.get_at((config.WINDOW[0] // 2, 260))[:3] != (0, 0, 0)


class RecordingSurface(pygame.Surface):
    """A surface that remembers where things were actually drawn.

    Checking the anchor arithmetic is not the same as checking the draw call
    uses it -- a readout can quietly go back to a window-relative offset and
    every arithmetic test still passes.
    """

    def __init__(self, size):
        super().__init__(size)
        self.blits = []

    def blit(self, source, dest, *args, **kwargs):
        self.blits.append(tuple(dest)[:2] if hasattr(dest, "__iter__") else dest)
        return super().blit(source, dest, *args, **kwargs)


@pytest.mark.parametrize("window", SIZES)
def test_the_ammo_readout_is_drawn_on_its_panel(display, window):
    surface = RecordingSurface(window)
    hud.GunData(window).update(surface)

    panel = hud.BOTTOM_RIGHT.rect(window)
    assert surface.blits, "nothing was drawn"
    for left, top in surface.blits:
        assert panel.left <= left <= panel.right, (left, panel)
        assert panel.top <= top <= panel.bottom, (top, panel)


@pytest.mark.parametrize("window", SIZES)
def test_the_health_readout_is_drawn_on_its_panel(display, window):
    surface = RecordingSurface(window)
    hud.HealthBar(window).draw(surface, 100)

    panel = hud.BOTTOM_LEFT.rect(window)
    left, top = surface.blits[0]
    assert panel.left <= left <= panel.right
    assert panel.top - 5 <= top <= panel.bottom


@pytest.mark.parametrize("window", SIZES)
def test_the_cash_readout_is_drawn_on_its_panel(display, window):
    surface = RecordingSurface(window)
    hud.Cash().update(surface, window)

    panel = hud.TOP_MIDDLE.rect(window)
    left, top = surface.blits[0]
    assert panel.left <= left <= panel.right
    assert panel.top <= top <= panel.bottom


@pytest.mark.parametrize("window", SIZES)
def test_the_hud_art_is_drawn_where_the_anchors_say(display, window):
    surface = RecordingSurface(window)
    hud.HUD().update(surface, window)

    assert surface.blits == [panel.rect(window).topleft for panel in hud.PANELS]


@pytest.mark.parametrize("window", SIZES)
def test_the_health_meter_is_drawn_on_the_top_panel(display, window, monkeypatch):
    """The meter is a filled rect rather than a blit, so it needs its own
    recorder -- it was one of the two positions that really were absolute."""
    drawn = []
    real_rect = pygame.draw.rect

    def record(surface, colour, rect, *args, **kwargs):
        drawn.append(pygame.Rect(rect))
        return real_rect(surface, colour, rect, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", record)
    hud.HealthBar(window).draw(pygame.Surface(window), 100)

    panel = hud.TOP_MIDDLE.rect(window)
    assert drawn, "the meter was never drawn"
    for meter in drawn:
        assert panel.contains(meter), (meter, panel)
