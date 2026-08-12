"""The dev screen gallery.

Nothing here is wired to gameplay yet, so these tests ask the two questions
that still matter: does it build without the library complaining, and does
everything it builds land inside the window.
"""

import warnings

import pygame
import pygame_gui
import pytest

from shooter import config
from shooter.ui import menu, widgets
from shooter.ui.dev import DevScreen
from shooter.ui.screens import ScreenStack

WINDOW = (1080, 720)


@pytest.fixture
def stack(display):
    made = ScreenStack(WINDOW)
    yield made
    made.clear()


@pytest.fixture
def dev(stack):
    screen = DevScreen(WINDOW, stack.manager)
    stack.push(screen)
    return screen


def test_the_gallery_builds_without_a_single_warning(stack):
    """pygame_gui warns rather than raises when a rect is too small for its
    text or an object id has no theming, so the warnings are the assertion."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        stack.push(DevScreen(WINDOW, stack.manager))


def test_every_widget_lands_inside_the_window(dev):
    window = pygame.Rect((0, 0), WINDOW)
    outside = [
        element
        for element in dev.elements
        if not window.contains(element.get_abs_rect())
    ]
    assert outside == []


def test_the_gallery_actually_contains_the_primitives(dev):
    built = {type(element) for element in dev.elements}
    assert built >= {
        pygame_gui.elements.UILabel,
        pygame_gui.elements.UIButton,
        pygame_gui.elements.UICheckBox,
        pygame_gui.elements.UIDropDownMenu,
        pygame_gui.elements.UIHorizontalSlider,
        pygame_gui.elements.UISelectionList,
        pygame_gui.elements.UIPanel,
    }


def test_the_ruler_columns_are_evenly_sized(dev):
    panels = [
        element
        for element in dev.elements
        if isinstance(element, pygame_gui.elements.UIPanel)
    ]
    ruler = [panel for panel in panels if panel.get_abs_rect().top < WINDOW[1] // 2]
    widths = {panel.get_abs_rect().width for panel in ruler}
    assert len(ruler) == 12
    assert max(widths) - min(widths) <= 1


def test_escape_goes_back(dev):
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert dev.handle(event) == menu.BACK


def test_the_back_button_goes_back(dev):
    event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=dev.back)
    assert dev.handle(event) == menu.BACK


def test_an_unrelated_button_does_nothing(dev, stack):
    stray = widgets.button(pygame.Rect(0, 0, 100, 30), "STRAY", stack.manager)
    event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=stray)
    assert dev.handle(event) is None


def test_closing_leaves_no_widgets_behind(stack, dev):
    assert stack.manager.get_root_container().elements
    stack.clear()
    assert stack.manager.get_root_container().elements == []


def test_the_dev_screen_replaces_the_game_rather_than_veiling_it(dev):
    assert dev.covers_game is True


def test_dev_is_only_reachable_while_dev_tools_are_on(monkeypatch, window):
    monkeypatch.setattr(config, "DEV_TOOLS", False)
    assert menu.DEV not in [
        action for _, action in menu.PauseScreen(window, None).entries
    ]

    monkeypatch.setattr(config, "DEV_TOOLS", True)
    assert menu.DEV in [action for _, action in menu.PauseScreen(window, None).entries]


def test_a_checkbox_can_be_built_already_checked(stack):
    rect = pygame.Rect(0, 0, 120, 30)
    assert widgets.checkbox(rect, "", stack.manager, checked=True).get_state() is True
    assert widgets.checkbox(rect, "", stack.manager, checked=False).get_state() is False
