"""Pause menu and the screen stack it drives."""

import ast
from pathlib import Path

import pygame
import pygame_gui
import pytest

from shooter import config, game
from shooter import session
from shooter.ui import menu
from shooter.ui.settings_screen import SettingsScreen
from shooter.ui.dev import DevScreen
from shooter.scenes import Scene, SceneStack

CAP = 600


class LoopRanAwayError(Exception):
    pass


@pytest.fixture
def stack(window, display):
    built = SceneStack(window)
    yield built
    built.clear()


def press(*keys):
    return [pygame.event.Event(pygame.KEYDOWN, key=key) for key in keys]


def click(button):
    return pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)


def button_labelled(screen, text):
    return next(b for b in screen.actions if b.text == text)


def test_the_stack_starts_empty(stack):
    assert not stack
    assert stack.top is None


def test_pushing_opens_a_screen(stack, window):
    stack.push(menu.PauseScreen(window, stack.manager))

    assert stack
    assert len(stack) == 1
    assert stack.top.title == "PAUSED"


def test_settings_stacks_on_top_of_pause(stack, window):
    stack.push(menu.PauseScreen(window, stack.manager))
    stack.push(SettingsScreen(window, stack.manager))

    assert len(stack) == 2
    assert stack.top.title == "SETTINGS"


def test_closing_settings_returns_to_pause(stack, window):
    """The reason this is a stack: back has somewhere to go."""
    stack.push(menu.PauseScreen(window, stack.manager))
    stack.push(SettingsScreen(window, stack.manager))

    stack.pop()

    assert len(stack) == 1
    assert stack.top.title == "PAUSED"


def test_clearing_closes_everything(stack, window):
    stack.push(menu.PauseScreen(window, stack.manager))
    stack.push(DevScreen(window, stack.manager))

    stack.clear()

    assert not stack


def test_a_closed_screen_leaves_no_widgets_behind(stack, window):
    screen = menu.PauseScreen(window, stack.manager)
    stack.push(screen)
    assert screen.elements

    stack.pop()

    assert screen.elements == []


def test_pause_overlays_the_game_and_a_full_screen_does_not(window, stack):
    assert menu.PauseScreen(window, stack.manager).opaque is False
    assert DevScreen(window, stack.manager).opaque is True


def test_escape_resumes_from_pause(stack, window):
    stack.push(menu.PauseScreen(window, stack.manager))

    assert stack.handle(press(pygame.K_ESCAPE)[0]) == menu.RESUME


def test_the_pause_buttons_report_their_actions(stack, window):
    screen = menu.PauseScreen(window, stack.manager)
    stack.push(screen)

    for label, expected in [
        ("RESUME", menu.RESUME),
        ("SETTINGS", menu.SETTINGS),
        ("QUIT", menu.QUIT),
    ]:
        assert stack.handle(click(button_labelled(screen, label))) == expected


def test_dev_is_offered_when_dev_tools_are_on(stack, window, monkeypatch):
    monkeypatch.setattr(config, "DEV_TOOLS", True)
    screen = menu.PauseScreen(window, stack.manager)
    stack.push(screen)

    assert "DEV" in [b.text for b in screen.actions]


def test_dev_is_hidden_when_dev_tools_are_off(stack, window, monkeypatch):
    """The menu must not offer an entry it cannot open."""
    monkeypatch.setattr(config, "DEV_TOOLS", False)
    screen = menu.PauseScreen(window, stack.manager)
    stack.push(screen)

    assert "DEV" not in [b.text for b in screen.actions]


def test_the_pointer_comes_back_for_menus_and_leaves_again(stack, window):
    """Gameplay draws its own crosshair with the system pointer hidden."""
    pygame.mouse.set_visible(False)

    stack.push(menu.PauseScreen(window, stack.manager))
    assert pygame.mouse.get_visible() is True

    stack.push(SettingsScreen(window, stack.manager))
    assert pygame.mouse.get_visible() is True

    stack.pop()
    assert pygame.mouse.get_visible() is True

    stack.clear()
    assert pygame.mouse.get_visible() is False


def test_the_crosshair_is_not_drawn_while_a_menu_is_up():
    """There is no frozen frame any more -- pause draws the live world beneath
    its veil. The ghost crosshair that replaced is prevented by the shell
    drawing the crosshair only while the top scene is the one being played.
    """
    tree = ast.parse(Path(game.__file__).read_text())

    guarded = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and node.test.attr == "simulates"
        and any(
            isinstance(inner, ast.Name) and inner.id == "cursor"
            for statement in node.body
            for inner in ast.walk(statement)
        )
    ]

    assert guarded, "the crosshair blit is not behind a `scenes.simulates` check"


def test_a_bare_screen_refuses_to_be_used_directly(window, stack):
    with pytest.raises(NotImplementedError):
        Scene(window, stack.manager).open()


def drive(events, monkeypatch):
    queued = list(events)
    real_flip = pygame.display.flip
    counter = {"n": 0}

    def flip():
        counter["n"] += 1
        if counter["n"] > CAP:
            raise LoopRanAwayError(f"still running after {CAP} frames")
        if counter["n"] >= 20 and counter["n"] % 6 == 0 and queued:
            pygame.event.post(queued.pop(0))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    return counter


def test_escape_then_quit_leaves_the_game(straight_to_game, monkeypatch):
    """Quit lives on the pause menu now, not on a bare keypress."""
    live = {}
    real_init = SceneStack.__init__

    def remember(self, window):
        real_init(self, window)
        live["stack"] = self

    monkeypatch.setattr(SceneStack, "__init__", remember)

    real_flip = pygame.display.flip
    counter = {"n": 0}

    def flip():
        counter["n"] += 1
        if counter["n"] > CAP:
            raise LoopRanAwayError(f"still running after {CAP} frames")
        if counter["n"] == 20:
            pygame.event.post(press(pygame.K_ESCAPE)[0])
        stack = live.get("stack")
        if counter["n"] > 25 and stack and stack.top and stack.top.title == "PAUSED":
            pygame.event.post(click(button_labelled(stack.top, "QUIT")))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)

    game.game_loop()

    assert pygame.display.get_init() is False


def test_the_world_stops_while_a_screen_is_open(straight_to_game, monkeypatch):
    ticks = []
    real = session.Human.update_anim

    def counting(self, kind, dt=config.SIM_DT):
        ticks.append(kind)
        return real(self, kind, dt)

    monkeypatch.setattr(session.Human, "update_anim", counting)
    frames = drive(press(pygame.K_ESCAPE, pygame.K_ESCAPE), monkeypatch)

    with pytest.raises(LoopRanAwayError):
        game.game_loop()

    assert len(ticks) < frames["n"]
