"""Where zombies come from.

The bug was not that zombies spawned in a bad place -- it is that they spawned
in the *same* place however far the player had walked, so a wave that was a
fight at one end of the map was a long stroll at the other. The test that
matters is therefore about the spread of spawn distances across the world, not
about any single spawn.
"""

import math

import pygame
import pytest

from shooter import config, game
from shooter.entities.zombie import Zombie, spawn_margin
from shooter.systems.waves import WaveSystem
from shooter.viewport import visible_world

WINDOW = (1080, 720)
CORNERS = [
    (0, 0),
    (-(config.WORLD[0] - WINDOW[0]), 0),
    (0, -(config.WORLD[1] - WINDOW[1])),
    (-(config.WORLD[0] - WINDOW[0]), -(config.WORLD[1] - WINDOW[1])),
    (-2000, -1500),
]


def furthest_possible():
    """Centre of the viewport to the corner of the ring around it."""
    half_width = WINDOW[0] / 2 + spawn_margin()
    half_height = WINDOW[1] / 2 + spawn_margin()
    return math.hypot(half_width, half_height)


def spawn_distances(camera, count=60):
    visible = visible_world(camera, WINDOW)
    player = visible.center
    return [
        math.dist(Zombie(WINDOW, None, visible).get_position(), player)
        for _ in range(count)
    ]


def test_the_visible_world_is_the_window_offset_by_the_camera():
    assert visible_world((0, 0), WINDOW) == pygame.Rect(0, 0, 1080, 720)
    assert visible_world((-2000, -1500), WINDOW) == pygame.Rect(2000, 1500, 1080, 720)


def test_the_player_stands_at_the_centre_of_the_visible_world():
    """The player is always drawn at the middle of the screen, so their world
    position is the middle of the world rectangle currently on screen."""
    camera = (-2000, -1500)
    visible = visible_world(camera, WINDOW)
    assert visible.center == (2000 + WINDOW[0] // 2, 1500 + WINDOW[1] // 2)


@pytest.mark.parametrize("camera", CORNERS)
def test_a_zombie_never_appears_on_screen(display, camera):
    visible = visible_world(camera, WINDOW)
    for _ in range(60):
        assert not visible.collidepoint(*Zombie(WINDOW, None, visible).get_position())


@pytest.mark.parametrize("camera", CORNERS)
def test_a_zombie_arrives_on_the_ring_not_just_anywhere_outside(display, camera):
    visible = visible_world(camera, WINDOW)
    ring = visible.inflate(2 * spawn_margin(), 2 * spawn_margin())

    for _ in range(60):
        x, y = Zombie(WINDOW, None, visible).get_position()
        assert not visible.collidepoint(x, y)
        # compared explicitly: a Rect excludes its own right and bottom edges,
        # and a spawn at `right + margin` sits exactly on the ring's
        assert ring.left <= x <= ring.right
        assert ring.top <= y <= ring.bottom


def test_the_margin_clears_a_whole_sprite(display, monkeypatch):
    """A one-pixel margin, as the old ring used, would pop half a zombie into
    view the instant it appeared. The floor holds even at the slowest settings."""
    assert max(config.ZOMBIE_SIZE) <= spawn_margin()

    monkeypatch.setattr(config, "ZOMBIE_SPEED", 30)
    monkeypatch.setattr(config, "SPAWN_LEAD_SECONDS", 0.5)
    assert max(config.ZOMBIE_SIZE) <= spawn_margin()


def test_a_wave_takes_the_stated_time_to_come_into_view(display, monkeypatch):
    """The point of the setting: seconds of warning, not pixels of distance."""
    monkeypatch.setattr(config, "ZOMBIE_SPEED", 360)
    monkeypatch.setattr(config, "SPAWN_LEAD_SECONDS", 3.0)
    assert spawn_margin() / config.ZOMBIE_SPEED == pytest.approx(3.0)


def test_a_faster_zombie_starts_further_out(display, monkeypatch):
    """So the warning stays the same however the tunables are set."""
    monkeypatch.setattr(config, "SPAWN_LEAD_SECONDS", 4.0)

    monkeypatch.setattr(config, "ZOMBIE_SPEED", 360)
    slow = spawn_margin()
    monkeypatch.setattr(config, "ZOMBIE_SPEED", 720)
    fast = spawn_margin()

    assert fast == 2 * slow
    assert fast / 720 == pytest.approx(slow / 360)


def test_the_lead_is_read_at_spawn_not_bound_at_import(display, monkeypatch):
    """ZOMBIE_SPEED is a setting, so a margin copied once would ignore it."""
    monkeypatch.setattr(config, "SPAWN_LEAD_SECONDS", 3.0)
    monkeypatch.setattr(config, "ZOMBIE_SPEED", 360)
    near = spawn_margin()

    monkeypatch.setattr(config, "ZOMBIE_SPEED", 1500)
    assert spawn_margin() > near


def test_a_wave_starts_much_further_out_than_it_used_to(display):
    """The ring used to sit 130px away -- about a third of a second's walk."""
    assert spawn_margin() > 4 * 130


@pytest.mark.parametrize("camera", CORNERS)
def test_a_wave_always_starts_within_reach(display, camera):
    """The whole ticket: the furthest a zombie can start is bounded by the
    viewport, not by where the player happens to be standing."""
    assert max(spawn_distances(camera)) <= furthest_possible() + 1


def test_difficulty_no_longer_depends_on_where_the_player_stands(display):
    """At the far corner of a 5000x5000 world the old ring left zombies
    thousands of pixels away; every corner now gives the same spread."""
    averages = [sum(spawn_distances(c)) / len(spawn_distances(c)) for c in CORNERS]
    assert max(averages) - min(averages) < 0.35 * furthest_possible()


def test_the_old_origin_ring_would_have_failed_that(display):
    """Guards the guard: the property is one the previous behaviour breaks.

    Stated as approach time, which is what the player actually feels -- the old
    ring left a far-corner wave walking for the better part of a minute, while
    the new one is bounded wherever they stand.
    """
    far_camera = (-(config.WORLD[0] - WINDOW[0]), -(config.WORLD[1] - WINDOW[1]))
    player = visible_world(far_camera, WINDOW).center

    from_origin = math.dist((960, 540), player) / config.ZOMBIE_SPEED
    from_the_ring = furthest_possible() / config.ZOMBIE_SPEED

    assert from_the_ring < 8.0, "a wave should not take that long to arrive"
    assert from_origin > 2 * from_the_ring


@pytest.mark.parametrize("camera", CORNERS)
def test_every_side_is_used(display, camera):
    visible = visible_world(camera, WINDOW)
    sides = set()
    for _ in range(200):
        x, y = Zombie(WINDOW, None, visible).get_position()
        sides.add(
            "above"
            if y < visible.top
            else "below"
            if y > visible.bottom
            else "left"
            if x < visible.left
            else "right"
        )
    assert sides == {"above", "below", "left", "right"}


def test_without_a_camera_the_ring_sits_around_the_window(display):
    """Nothing has moved yet, so the visible world genuinely is the window."""
    window_rect = pygame.Rect((0, 0), WINDOW)
    for _ in range(40):
        assert not window_rect.collidepoint(*Zombie(WINDOW, None).get_position())


def test_a_wave_spawns_around_the_player(display, cash):
    camera = (-3000, -2500)
    visible = visible_world(camera, WINDOW)
    group = pygame.sprite.Group()
    WaveSystem(WINDOW, group, cash, visible)

    assert len(group) == config.WAVE_BASE
    for zombie in group:
        assert math.dist(zombie.get_position(), visible.center) <= (
            furthest_possible() + 1
        )


def test_later_waves_also_arrive_around_the_player(display, cash, cash_factory):
    camera = (-3000, -2500)
    visible = visible_world(camera, WINDOW)
    group = pygame.sprite.Group()
    waves = WaveSystem(WINDOW, group, cash, visible)
    group.empty()

    waves.wave_seconds = config.WAVE_INTERVAL_SECONDS
    waves.advance(WINDOW, group, cash_factory(), config.SIM_DT, visible)

    assert len(group) == config.WAVE_BASE + 1
    for zombie in group:
        assert math.dist(zombie.get_position(), visible.center) <= (
            furthest_possible() + 1
        )


def test_the_origin_anchored_spawn_area_is_gone():
    assert not hasattr(config, "SPAWN_AREA")


def test_the_loop_always_tells_the_spawner_where_the_player_is(monkeypatch):
    """Wiring, not arithmetic: every zombie the running game creates must be
    given the visible world, or it falls back to the ring at the origin."""
    given = []
    spawned = []
    real_init = Zombie.__init__

    def remember(self, window_size, cash, visible=None):
        given.append(visible)
        spawned.append(self)
        real_init(self, window_size, cash, visible)

    monkeypatch.setattr(Zombie, "__init__", remember)

    frames = {"n": 0}
    real_flip = pygame.display.flip

    def flip():
        frames["n"] += 1
        if frames["n"] == 20:
            # a later wave only arrives once the field is clear
            for zombie in list(spawned):
                zombie.kill()
        if frames["n"] > 40:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    monkeypatch.setattr(config, "WAVE_INTERVAL_SECONDS", 0.01)

    game.game_loop()

    assert given, "no zombies were spawned at all"
    assert all(seen is not None for seen in given), (
        f"{given.count(None)} of {len(given)} spawns fell back to the origin ring"
    )
    assert len(given) > config.WAVE_BASE, (
        "no later wave arrived, so only the first was checked"
    )
