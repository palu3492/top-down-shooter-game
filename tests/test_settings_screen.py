"""The settings form.

The interesting behaviour is not that controls appear -- it is that nothing
reaches disk or the running game until Save, and that a change needing a restart
says so before it is written.
"""

import json

import pygame
import pygame_gui
import pytest

from shooter import config
from shooter.settings import InvalidSettingError, Settings
from shooter.ui import form
from shooter.ui.dev import DevScreen
from shooter.ui.menu import BACK
from shooter.ui.screens import ScreenStack
from shooter.ui.settings_screen import DISPLAY, SettingsScreen

WINDOW = (1080, 720)


@pytest.fixture
def store(tmp_path):
    return Settings(path=tmp_path / "settings.json")


@pytest.fixture
def stack(display):
    made = ScreenStack(WINDOW)
    yield made
    made.clear()


@pytest.fixture
def screen(stack, store):
    made = SettingsScreen(WINDOW, stack.manager, store)
    stack.push(made)
    return made


def field(screen, name):
    return next(f for f in screen.form.fields if f.setting.name == name)


def press(screen, button):
    return screen.handle(
        pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
    )


def test_the_screen_shows_the_display_settings(screen):
    assert [f.setting.name for f in screen.form.fields] == list(DISPLAY)


def test_a_control_is_derived_from_the_setting(screen):
    assert type(field(screen, "WINDOW").control).__name__ == "UIDropDownMenu"
    assert type(field(screen, "VSYNC").control).__name__ == "UICheckBox"
    assert type(field(screen, "FPS").control).__name__ == "UIHorizontalSlider"


def test_controls_start_at_the_stored_values(screen, store):
    assert field(screen, "FPS").value == store["FPS"]
    assert field(screen, "WINDOW").value == store["WINDOW"]
    assert field(screen, "VSYNC").value == store["VSYNC"]


def test_building_the_form_announces_nothing(stack, store):
    """Populating a form is not the player editing it."""
    pygame.event.clear()
    stack.push(SettingsScreen(WINDOW, stack.manager, store))
    assert pygame.event.get() == []


def test_moving_a_control_does_not_touch_the_store(screen, store):
    field(screen, "FPS").control.set_current_value(144)
    assert store["FPS"] == config.FPS
    assert not screen.settings.path.exists()


def test_leaving_without_saving_discards(screen, store):
    field(screen, "FPS").control.set_current_value(144)
    assert press(screen, screen.back) == BACK
    assert store["FPS"] == config.FPS
    assert not store.path.exists()


def test_saving_writes_the_store_and_the_file(screen, store):
    field(screen, "FPS").control.set_current_value(144)
    press(screen, screen.save_button)

    assert store["FPS"] == 144
    assert json.loads(store.path.read_text())["FPS"] == 144


def test_saving_a_live_setting_reaches_config(screen, monkeypatch):
    monkeypatch.setattr(config, "FPS", 240)
    field(screen, "FPS").control.set_current_value(144)
    press(screen, screen.save_button)
    assert config.FPS == 144


def test_a_boot_setting_asks_before_it_is_written(screen, store):
    screen.draft.apply_at_startup(config)
    field(screen, "WINDOW").control.selected_option = ("1920 x 1080", "1920 x 1080")

    press(screen, screen.save_button)

    assert screen.confirming is not None
    assert not store.path.exists()


def test_confirming_the_restart_warning_writes_it(screen, store):
    screen.draft.apply_at_startup(config)
    field(screen, "WINDOW").control.selected_option = ("1920 x 1080", "1920 x 1080")
    press(screen, screen.save_button)

    screen.handle(pygame.event.Event(pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED))

    assert screen.confirming is None
    assert store["WINDOW"] == (1920, 1080)
    assert json.loads(store.path.read_text())["WINDOW"] == [1920, 1080]


def test_dismissing_the_restart_warning_writes_nothing(screen, store):
    screen.draft.apply_at_startup(config)
    field(screen, "WINDOW").control.selected_option = ("1920 x 1080", "1920 x 1080")
    press(screen, screen.save_button)

    screen.handle(
        pygame.event.Event(pygame_gui.UI_WINDOW_CLOSE, ui_element=screen.confirming)
    )

    assert screen.confirming is None
    assert not store.path.exists()


def test_a_boot_setting_left_alone_saves_without_asking(screen, store):
    screen.draft.apply_at_startup(config)
    field(screen, "FPS").control.set_current_value(144)

    press(screen, screen.save_button)

    assert screen.confirming is None
    assert store["FPS"] == 144


def test_the_dialog_swallows_escape_rather_than_leaving(screen):
    screen.draft.apply_at_startup(config)
    field(screen, "WINDOW").control.selected_option = ("1920 x 1080", "1920 x 1080")
    press(screen, screen.save_button)

    escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert screen.handle(escape) is None


def test_closing_the_screen_takes_the_dialog_with_it(stack, screen):
    screen.draft.apply_at_startup(config)
    field(screen, "WINDOW").control.selected_option = ("1920 x 1080", "1920 x 1080")
    press(screen, screen.save_button)
    dialog = screen.confirming

    stack.clear()

    assert screen.confirming is None
    assert dialog.alive() is False


def test_escape_leaves_the_screen(screen):
    assert (
        screen.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == BACK
    )


def test_the_hint_says_nothing_is_saved_until_it_is(screen):
    assert screen.hint.text == screen.UNSAVED
    field(screen, "FPS").control.set_current_value(144)
    press(screen, screen.save_button)
    assert screen.hint.text == screen.SAVED


def test_a_resolution_reads_back_as_the_tuple_it_came_from(screen):
    chosen = field(screen, "WINDOW")
    chosen.control.selected_option = ("2560 x 1440", "2560 x 1440")
    assert chosen.value == (2560, 1440)


def test_an_out_of_range_control_cannot_be_committed(screen):
    """The store validates whatever the form hands it, so a control that has
    somehow gone out of range is refused rather than written."""
    setting = screen.draft.setting("FPS")
    with pytest.raises(InvalidSettingError):
        screen.draft.set("FPS", setting.minimum - 1)


def test_the_dev_screen_saves_through_the_same_path(stack, store):
    dev = DevScreen(WINDOW, stack.manager, store)
    stack.push(dev)

    zombie_speed = next(f for f in dev.form.fields if f.setting.name == "ZOMBIE_SPEED")
    zombie_speed.control.set_current_value(500)
    dev.handle(
        pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=dev.save_button)
    )

    assert store["ZOMBIE_SPEED"] == 500
    assert json.loads(store.path.read_text())["ZOMBIE_SPEED"] == 500


def test_no_tunable_on_the_dev_screen_needs_a_restart(stack, store):
    """Which is why the dev screen never has to raise the dialog."""
    dev = DevScreen(WINDOW, stack.manager, store)
    stack.push(dev)
    assert all(f.setting.applies != "boot" for f in dev.form.fields)


def test_a_field_reports_whether_it_changed(screen):
    fps = field(screen, "FPS")
    assert fps.changed is False
    fps.control.set_current_value(144)
    assert fps.changed is True


def test_the_restart_warning_names_the_settings_it_is_about(stack):
    dialog = form.confirmation(WINDOW, stack.manager, ("WINDOW", "VSYNC"))
    assert "window" in dialog.confirmation_text.html_text
    assert "vsync" in dialog.confirmation_text.html_text
    assert "restart" in dialog.confirmation_text.html_text
    dialog.kill()
