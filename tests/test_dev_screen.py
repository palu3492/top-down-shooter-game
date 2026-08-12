"""The dev screen gallery.

Nothing here is wired to gameplay yet, so these tests ask the two questions
that still matter: does it build without the library complaining, and does
everything it builds land inside the window.
"""

import warnings

import pygame
import pygame_gui
import pytest

from shooter import config, game
from shooter.ui import menu, widgets
from shooter.ui import dev as dev_screen
from shooter.ui.dev import DevScreen
from shooter.ui.layout import LayoutOverflowError
from shooter.scenes import SceneStack

WINDOW = (1080, 720)
TINY = (1080, 300)


@pytest.fixture
def stack(display):
    made = SceneStack(WINDOW)
    yield made
    made.clear()


@pytest.fixture
def dev(stack):
    screen = DevScreen(WINDOW, stack.manager)
    stack.push(screen)
    return screen


def test_the_screen_builds_without_a_single_warning(stack):
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


def test_the_screen_offers_every_tunable(dev):
    shown = {field.setting.name for field in dev.form.fields}
    assert shown == set(dev_screen.LIVE_TUNABLES) | set(dev_screen.SPAWN_TUNABLES)


def test_dev_tools_is_not_offered_here(dev):
    """Turning it off from this screen removes the only way back to it."""
    assert "DEV_TOOLS" not in {field.setting.name for field in dev.form.fields}


def test_a_control_is_chosen_from_the_setting_type(dev):
    controls = {
        field.setting.name: type(field.control).__name__ for field in dev.form.fields
    }
    assert controls["ZOMBIE_SPEED"] == "UIHorizontalSlider"
    assert controls["PLAYER_REGEN"] == "UIHorizontalSlider"


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
    assert dev.opaque is True


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


def test_building_a_checked_checkbox_announces_nothing(stack):
    """set_state posts UI_CHECK_BOX_CHECKED, which a settings form would read
    as the player editing a field it was still drawing."""
    pygame.event.clear()
    box = widgets.checkbox(pygame.Rect(0, 0, 120, 30), "", stack.manager, checked=True)
    assert pygame.event.get() == []
    assert box.get_state() is True


def test_opening_the_screen_leaves_no_events_behind(stack):
    pygame.event.clear()
    stack.push(DevScreen(WINDOW, stack.manager))
    assert pygame.event.get() == []


def test_a_dropdown_takes_any_iterable_of_options(stack):
    made = widgets.dropdown(
        pygame.Rect(0, 0, 150, 30), (name for name in ["A", "B"]), stack.manager
    )
    assert made.selected_option[0] == "A"


def test_a_dropdown_refuses_to_be_built_empty(stack):
    with pytest.raises(ValueError):
        widgets.dropdown(pygame.Rect(0, 0, 150, 30), [], stack.manager)


@pytest.mark.parametrize("height", [640, 720, 900, 1440])
def test_the_screen_builds_at_every_window_it_claims_to_support(display, height):
    stack = SceneStack((1080, height))
    stack.push(DevScreen((1080, height), stack.manager))
    window = pygame.Rect(0, 0, 1080, height)
    assert all(window.contains(e.get_abs_rect()) for e in stack.top.elements)
    stack.clear()


def test_a_screen_too_big_for_the_window_leaves_the_stack_alone(display):
    """Building the new screen before tearing down the old one is what makes
    a failure a no-op rather than a menu that has already been destroyed."""
    stack = SceneStack(TINY)
    stack.push(menu.PauseScreen(TINY, stack.manager))
    survivors = list(stack.top.elements)

    with pytest.raises(LayoutOverflowError):
        stack.push(DevScreen(TINY, stack.manager))

    assert len(stack) == 1
    assert stack.top.elements == survivors
    assert all(element.alive() for element in survivors)
    assert pygame.mouse.get_visible() is True
    stack.clear()


def test_the_game_stays_up_when_a_screen_will_not_fit(display):
    stack = SceneStack(TINY)
    stack.push(menu.PauseScreen(TINY, stack.manager))
    game.open_scene(stack, DevScreen(TINY, stack.manager))
    assert isinstance(stack.top, menu.PauseScreen)
    stack.clear()


WRAPPERS = {
    "title": lambda rect, manager: widgets.title(rect, "x", manager),
    "hint": lambda rect, manager: widgets.hint(rect, "x", manager),
    "caption": lambda rect, manager: widgets.caption(rect, "x", manager),
    "button": lambda rect, manager: widgets.button(rect, "x", manager),
    "checkbox": lambda rect, manager: widgets.checkbox(rect, "x", manager),
    "checked checkbox": lambda rect, manager: widgets.checkbox(
        rect, "x", manager, checked=True
    ),
    "dropdown": lambda rect, manager: widgets.dropdown(rect, ["A", "B"], manager),
    "preselected dropdown": lambda rect, manager: widgets.dropdown(
        rect, ["A", "B"], manager, selected="B"
    ),
    "slider": lambda rect, manager: widgets.slider(rect, manager, 5, (0, 10)),
    "selector": lambda rect, manager: widgets.selector(rect, ["A", "B"], manager),
    "panel": lambda rect, manager: widgets.panel(rect, manager),
}


@pytest.mark.parametrize("name", WRAPPERS)
def test_building_a_widget_announces_nothing(stack, name):
    """A widget that emits while a screen is being built is indistinguishable
    from the player using it. AT24 reads these events as edits to a form, so
    every wrapper has to stay quiet until someone actually touches it."""
    pygame.event.clear()
    WRAPPERS[name](pygame.Rect(0, 0, 200, 120), stack.manager)
    assert pygame.event.get() == []
