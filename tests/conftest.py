import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from shooter import config, game, settings
from shooter.ui import title


class RecordingCash:
    def __init__(self):
        self.received = []

    def increase_cash(self, amount):
        self.received.append(amount)


@pytest.fixture(scope="session")
def window():
    return (1080, 720)


@pytest.fixture
def straight_to_game(monkeypatch):
    """Boot past the splash.

    game_loop starts at a title card now, so a test that wants a game running
    has to say so. Zeroing the timings makes the first frame's tick hand over
    to the menu; `route` then starts a game as though START had been clicked.
    """
    for name in ("FADE_IN", "HOLD", "SKIPPABLE_AFTER"):
        monkeypatch.setattr(title, name, 0.0)

    real_route = game.route

    def routed(action, scenes, window, settings, progress=None):
        keep = real_route(action, scenes, window, settings, progress)
        if action == title.MENU:
            keep = real_route(title.START, scenes, window, settings, progress) and keep
        return keep

    monkeypatch.setattr(game, "route", routed)


@pytest.fixture(autouse=True)
def _settings_isolated(tmp_path_factory, monkeypatch):
    """No test reads or writes the developer's own settings file.

    game_loop() applies settings onto the config module at startup, so the
    values it touches are put back afterwards too.
    """
    path = tmp_path_factory.mktemp("settings") / "settings.json"
    monkeypatch.setattr(settings, "settings_path", lambda: path)

    before = {s.name: getattr(config, s.name) for s in settings.CATALOGUE}
    yield path
    for name, value in before.items():
        setattr(config, name, value)


@pytest.fixture(autouse=True)
def _progress_isolated(_settings_isolated):
    """Progress is named from the settings path, so redirecting that redirects
    this -- but only if nothing imported the function by value. Asserting it
    here means a future refactor cannot quietly start writing to a real
    player's save file from the test suite."""
    from shooter.progress import progress_path

    assert progress_path().parent == _settings_isolated.parent


@pytest.fixture(autouse=True)
def _pygame_ready(window):
    """Bring pygame up, and back up after a test that shut it down.

    game_loop() calls pygame.quit() on its way out, so the shutdown tests leave
    the library uninitialised for whatever runs next.
    """
    if not pygame.display.get_init():
        pygame.init()
        pygame.display.set_mode(window)


@pytest.fixture
def display(_pygame_ready):
    return pygame.display.get_surface()


@pytest.fixture
def make_cash():
    return RecordingCash


@pytest.fixture
def cash_factory(make_cash):
    return make_cash


@pytest.fixture
def cash(make_cash):
    return make_cash()
