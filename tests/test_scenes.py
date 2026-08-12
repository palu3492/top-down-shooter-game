"""Gameplay as a scene on the same stack as everything else.

The point of the ticket is not that the stack grew an entry. It is that
starting and ending a game became `push` and `pop`, that pausing stopped being
a special case in the loop, and that the world survives being covered.
"""

import pygame
import pytest

from shooter import config, game
from shooter.gameplay import PAUSE, GameplayScene
from shooter.scenes import Scene, SceneStack
from shooter.settings import Settings
from shooter.ui import menu
from shooter.ui.settings_screen import SettingsScreen
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    yield made
    made.clear()


@pytest.fixture
def playing(stack):
    scene = GameplayScene(stack.window, stack.manager)
    stack.push(scene)
    return scene


def inputs(**pressed):
    keys = dict.fromkeys(range(512), False)
    for name, value in pressed.items():
        keys[getattr(pygame, name)] = value
    return game.Inputs(keys, (800, 300))


def test_starting_a_game_is_a_push(stack):
    assert len(stack) == 0
    stack.push(GameplayScene(stack.window, stack.manager))
    assert len(stack) == 1
    assert stack.top.simulates is True


def test_ending_a_game_is_a_pop(stack, playing):
    stack.pop()
    assert len(stack) == 0
    assert stack.top is None


def test_a_new_game_owes_nothing_to_the_last(stack):
    stack.push(GameplayScene(stack.window, stack.manager))
    stack.top.session.cash.increase_cash(500)
    stack.pop()

    stack.push(GameplayScene(stack.window, stack.manager))
    assert stack.top.session.cash.cash_amount == 0


def test_pausing_does_not_destroy_the_world(stack, playing):
    """`push` closes the scene beneath it so two menus cannot both be live.
    Gameplay has no widgets to close, so the session comes through untouched."""
    playing.session.cash.increase_cash(250)
    session = playing.session

    stack.push(menu.PauseScreen(stack.window, stack.manager))
    stack.pop()

    assert stack.top is playing
    assert stack.top.session is session
    assert session.cash.cash_amount == 250


def test_the_world_stops_while_a_menu_is_up(stack, playing):
    stack.push(menu.PauseScreen(stack.window, stack.manager))
    before = [z.get_position() for z in playing.session.zombies]

    for _ in range(20):
        stack.update(inputs(K_d=True), config.SIM_DT)

    assert [z.get_position() for z in playing.session.zombies] == before


def test_the_world_moves_again_once_the_menu_closes(stack, playing):
    stack.push(menu.PauseScreen(stack.window, stack.manager))
    stack.pop()

    before = [z.get_position() for z in playing.session.zombies]
    for _ in range(20):
        stack.update(inputs(K_d=True), config.SIM_DT)

    assert [z.get_position() for z in playing.session.zombies] != before


def test_only_gameplay_simulates(stack, playing):
    assert stack.simulates is True
    stack.push(menu.PauseScreen(stack.window, stack.manager))
    assert stack.simulates is False
    stack.pop()
    assert stack.simulates is True


def test_pause_shows_the_world_beneath_it(stack, playing):
    """The frozen frame is gone: pause is transparent, so the stack draws the
    live world under its veil rather than a screenshot taken when it opened."""
    pause = menu.PauseScreen(stack.window, stack.manager)
    stack.push(pause)

    assert pause.opaque is False
    assert stack.visible() == [playing, pause]


def test_a_full_screen_hides_what_is_under_it(stack, playing):
    settings = SettingsScreen(stack.window, stack.manager, Settings())
    stack.push(settings)

    assert settings.opaque is True
    assert stack.visible() == [settings], "nothing below an opaque scene is drawn"


def test_nesting_reaches_back_down_to_the_world(stack, playing):
    pause = menu.PauseScreen(stack.window, stack.manager)
    stack.push(pause)
    stack.push(SettingsScreen(stack.window, stack.manager, Settings()))
    stack.pop()

    assert stack.top is pause
    assert stack.visible() == [playing, pause]


def test_escape_asks_to_pause_rather_than_pausing_itself(playing):
    """A scene reports what happened; the shell decides what that means."""
    action = playing.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert action == PAUSE


def test_gameplay_passes_other_events_to_the_session(playing):
    playing.session.aim_at((900, 300))
    playing.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    assert len(playing.session.bullets) == 1


def test_the_pointer_is_hidden_only_while_playing(stack, playing):
    assert pygame.mouse.get_visible() is False

    stack.push(menu.PauseScreen(stack.window, stack.manager))
    assert pygame.mouse.get_visible() is True

    stack.pop()
    assert pygame.mouse.get_visible() is False


def test_drawing_an_empty_stack_is_harmless(stack):
    stack.draw(pygame.Surface(WINDOW), 0.0)


def test_a_bare_scene_refuses_to_be_used_directly(stack):
    with pytest.raises(NotImplementedError):
        Scene(stack.window, stack.manager).open()


def test_routing_turns_actions_into_stack_moves(stack, playing):
    settings = Settings()

    assert game.route(PAUSE, stack, stack.window, settings) is True
    assert isinstance(stack.top, menu.PauseScreen)

    assert game.route(menu.SETTINGS, stack, stack.window, settings) is True
    assert isinstance(stack.top, SettingsScreen)

    assert game.route(menu.BACK, stack, stack.window, settings) is True
    assert isinstance(stack.top, menu.PauseScreen)

    assert game.route(menu.RESUME, stack, stack.window, settings) is True
    assert stack.top is playing

    assert game.route(menu.QUIT, stack, stack.window, settings) is False


def test_an_unknown_action_leaves_the_stack_alone(stack, playing):
    assert game.route(None, stack, stack.window, Settings()) is True
    assert stack.top is playing
    assert len(stack) == 1


def test_a_resize_reaches_every_scene(stack, playing):
    stack.push(menu.PauseScreen(stack.window, stack.manager))
    bigger = Viewport((1920, 1080))

    stack.resize(bigger)

    assert stack.window == (1920, 1080)
    assert all(scene.window == (1920, 1080) for scene in stack.visible())
