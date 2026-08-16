"""Changing resolution while the game is running.

The claim being tested is not that the surface changes size -- it is that
nothing else does. World positions, health, ammo and the wave counter are not
measured in pixels, so a resolution change must leave every one of them alone.
"""

import json

import pygame
import pytest

from shooter import config, game
from shooter.entities.player import Human
from shooter.entities.zombie import Zombie
from shooter.gameplay import GameplayScene
from shooter.settings import CATALOGUE, LIVE, Settings
from shooter.ui.hud import HUD, Cash, HealthBar, WeaponPanel
from shooter.scenes import SceneStack
from shooter.ui.settings_screen import SettingsScreen
from shooter.viewport import Viewport

SMALL = (1080, 720)
LARGE = (1920, 1080)


@pytest.fixture
def viewport():
    return Viewport(SMALL)


def test_a_viewport_behaves_like_the_pair_it_replaces(viewport):
    assert viewport[0] == 1080
    assert viewport[1] == 720
    assert tuple(viewport) == SMALL
    assert viewport == SMALL
    assert len(viewport) == 2


def test_resizing_is_seen_by_whoever_is_holding_it(viewport):
    holder = viewport
    viewport.resize(LARGE)
    assert holder[0] == 1920
    assert holder.centre == (960.0, 540.0)


def test_the_health_bar_follows_the_viewport(display, viewport):
    bar = HealthBar(viewport)
    surface = pygame.Surface(LARGE)

    bar.draw(surface, 100)
    viewport.resize(LARGE)
    bar.draw(surface, 100)

    assert bar.window_size[1] == 1080


def test_the_gun_readout_follows_the_viewport(display, viewport):
    readout = WeaponPanel(viewport)
    viewport.resize(LARGE)
    assert readout.window[0] == 1920


def test_the_hud_places_itself_from_whatever_it_is_given(display):
    hud = HUD()
    small = hud.positions(SMALL)
    large = hud.positions(LARGE)
    assert small != large
    assert large[0][0] == 1920 - 263


def test_a_zombie_walks_at_the_new_centre_not_the_old_one(display, viewport):
    """`move_toward_center` uses half the window as the player's screen
    position, so a stale size sends existing zombies at the wrong point."""
    zombie = Zombie(viewport, Cash())
    viewport.resize(LARGE)
    assert zombie.window_size[0] == 1920


def test_a_zombie_keeps_its_world_position_across_a_resize(display, viewport):
    zombie = Zombie(viewport, Cash())
    zombie.set_position(2100, 3400)
    zombie.zombie_health = 42.0

    viewport.resize(LARGE)

    assert (zombie.zombie_x, zombie.zombie_y) == (2100, 3400)
    assert zombie.zombie_health == 42.0


def test_the_player_is_re_centred(display, viewport):
    human = Human(viewport)
    before = human.rect.center

    viewport.resize(LARGE)
    human.recentre(viewport)

    assert human.rect.center != before
    assert human.rect.centerx == pytest.approx(960, abs=1)
    assert human.rect.centery == pytest.approx(540, abs=1)


def test_re_centring_does_not_touch_health(display, viewport):
    human = Human(viewport)
    human.remove_health(30)
    hurt = human.health

    viewport.resize(LARGE)
    human.recentre(viewport)

    assert human.health == hurt


def test_the_screen_stack_rebuilds_against_the_new_size(display, tmp_path):
    stack = SceneStack(SMALL)
    stack.push(SettingsScreen(SMALL, stack.manager, Settings(path=tmp_path / "s.json")))
    before = stack.top.elements[0].get_abs_rect().width

    stack.resize(LARGE)

    assert stack.window == LARGE
    assert stack.top.window == LARGE
    assert stack.top.elements[0].get_abs_rect().width != before
    stack.clear()


def test_a_rebuilt_form_does_not_stack_duplicate_fields(display, tmp_path):
    stack = SceneStack(SMALL)
    stack.push(SettingsScreen(SMALL, stack.manager, Settings(path=tmp_path / "s.json")))
    before = len(stack.top.form.fields)

    stack.resize(LARGE)

    assert len(stack.top.form.fields) == before
    stack.clear()


def test_everything_rebuilt_stays_inside_the_new_window(display, tmp_path):
    stack = SceneStack(SMALL)
    stack.push(SettingsScreen(SMALL, stack.manager, Settings(path=tmp_path / "s.json")))
    stack.resize(LARGE)

    window = pygame.Rect((0, 0), LARGE)
    assert all(window.contains(e.get_abs_rect()) for e in stack.top.elements)
    stack.clear()


def test_resolution_is_a_live_setting_now():
    setting = next(s for s in CATALOGUE if s.name == "WINDOW")
    assert setting.applies == LIVE


def test_nothing_happens_while_the_setting_matches(display, viewport, monkeypatch):
    monkeypatch.setattr(config, "WINDOW", SMALL)
    stack = SceneStack(SMALL)

    assert game.match_resolution(viewport, stack) is None
    stack.clear()


def test_the_game_changes_resolution_without_losing_the_world(
    straight_to_game, _settings_isolated, monkeypatch
):
    """The real flow: pause, change resolution, come back to the same world.

    Resizing while paused is what makes this exact rather than approximate --
    the simulation is frozen, so any movement at all would be the resize
    disturbing the world rather than zombies doing their job.
    """
    seen = {}
    real_flip = pygame.display.flip

    def flip():
        frame = seen.get("frames", 0)
        seen["frames"] = frame + 1

        if frame == 5:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        if frame == 10:
            zombie = seen["zombies"][0]
            zombie.set_position(2100, 3400)
            seen["before"] = (zombie.zombie_x, zombie.zombie_y)
            seen["health"] = seen["human"].health
            seen["ammo"] = seen["human"].health
            config.WINDOW = LARGE
        if frame == 16:
            zombie = seen["zombies"][0]
            seen["after"] = (zombie.zombie_x, zombie.zombie_y)
            seen["health_after"] = seen["human"].health
            seen["surface"] = pygame.display.get_surface().get_size()
            seen["zombie_sees"] = tuple(zombie.window_size)
            seen["player_at"] = seen["human"].rect.center
            stack = seen["stack"]
            seen["menu_size"] = stack.window
            # the title label spans the window, so its width is proof the
            # menu was laid out again rather than merely still fitting
            seen["menu_title_width"] = stack.top.elements[0].get_abs_rect().width
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    def remember(original, key):
        def made(self, *args):
            original(self, *args)
            seen.setdefault(key, []).append(self)

        return made

    real_human = Human.__init__

    def human_made(self, window_size):
        real_human(self, window_size)
        seen["human"] = self

    real_stack = SceneStack.__init__

    def stack_made(self, window):
        real_stack(self, window)
        seen["stack"] = self

    monkeypatch.setattr(SceneStack, "__init__", stack_made)
    monkeypatch.setattr(Human, "__init__", human_made)
    monkeypatch.setattr(Zombie, "__init__", remember(Zombie.__init__, "zombies"))
    monkeypatch.setattr(pygame.display, "flip", flip)

    game.game_loop()

    assert seen["surface"] == LARGE, "the display never changed size"
    assert seen["after"] == seen["before"], "a world position moved"
    assert seen["health_after"] == seen["health"], "health changed"
    assert seen["zombie_sees"] == LARGE, "an existing zombie kept the old size"
    assert seen["player_at"] == (960, 540), "the player is no longer centred"
    assert seen["menu_size"] == LARGE, "the open menu kept the old size"
    assert seen["menu_title_width"] == LARGE[0], "the open menu was not rebuilt"


def test_saving_a_new_resolution_no_longer_asks_for_a_restart(display, tmp_path):
    store = Settings(path=tmp_path / "s.json")
    stack = SceneStack(SMALL)
    screen = SettingsScreen(SMALL, stack.manager, store)
    stack.push(screen)
    screen.draft.apply_at_startup(config)

    chosen = next(f for f in screen.form.fields if f.setting.name == "WINDOW")
    chosen.control.selected_option = ("1920 x 1080", "1920 x 1080")
    screen.save()

    assert screen.confirming is None, "resolution should no longer warn"
    assert json.loads(store.path.read_text())["WINDOW"] == [1920, 1080]
    stack.clear()


RESOLUTION_WALK = [(1280, 720), (1600, 900), (1920, 1080), (1080, 720), (2560, 1440)]


def test_many_resolution_changes_do_not_bring_the_process_down(display, monkeypatch):
    """A crash cannot be asserted, only survived.

    `set_mode` with SCALED *and* RESIZABLE aborts inside SDL on a second call --
    reliably on Linux, roughly one run in six on macOS. AT25 put that call
    behind a settings screen, so this walks the sizes a player could actually
    pick. Reaching the end is the assertion.
    """
    stack = SceneStack(SMALL)
    viewport = Viewport(SMALL)
    stack.push(GameplayScene(viewport, stack.manager))

    for size in RESOLUTION_WALK:
        monkeypatch.setattr(config, "WINDOW", size)
        assert game.match_resolution(viewport, stack) is not None
        assert viewport == size

    stack.clear()
    game.open_display(Viewport(config.WINDOW))


def test_the_display_does_not_ask_for_a_resizable_window():
    """The flag combination that aborts is SCALED with RESIZABLE, and only on a
    second call -- which is exactly what changing resolution does."""
    flags = []
    real = pygame.display.set_mode

    def spy(size, flag=0, *args, **kwargs):
        flags.append(flag)
        return real(size, flag, *args, **kwargs)

    original = pygame.display.set_mode
    pygame.display.set_mode = spy
    try:
        game.open_display(Viewport(SMALL))
    finally:
        pygame.display.set_mode = original

    assert flags
    assert not flags[0] & pygame.RESIZABLE
    assert flags[0] & pygame.SCALED
