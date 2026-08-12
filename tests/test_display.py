"""Window setup.

SDL's dummy driver has no renderer, so SCALED cannot actually engage in CI.
These tests pin what *is* observable headlessly -- that the flags are requested
and the logical surface never changes size -- and the ticket records the manual
check for the scaling itself.
"""

import pygame
import pytest

from shooter import config, game


@pytest.fixture
def captured_mode(monkeypatch):
    calls = []
    real = pygame.display.set_mode

    def spy(size, flags=0, *args, **kwargs):
        calls.append({"size": size, "flags": flags, "kwargs": kwargs})
        return real(size, flags, *args, **kwargs)

    monkeypatch.setattr(pygame.display, "set_mode", spy)
    return calls


def run_briefly(monkeypatch, frames=8):
    counter = {"n": 0}
    real_flip = pygame.display.flip

    def flip():
        counter["n"] += 1
        if counter["n"] >= frames:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    game.game_loop()


def test_the_window_is_opened_scaled_but_not_resizable(monkeypatch, captured_mode):
    """AT17 asked for both flags. AT26 dropped RESIZABLE: a second `set_mode`
    with SCALED and RESIZABLE together aborts inside SDL, and AT25 made that
    second call something a player triggers from the settings screen.
    """
    run_briefly(monkeypatch)

    opening = captured_mode[0]
    assert opening["size"] == config.WINDOW
    assert opening["flags"] & pygame.SCALED
    assert not opening["flags"] & pygame.RESIZABLE


def test_vsync_is_requested(monkeypatch, captured_mode):
    run_briefly(monkeypatch)

    assert captured_mode[0]["kwargs"].get("vsync") == config.VSYNC


def test_fullscreen_does_not_reopen_the_window(monkeypatch, captured_mode):
    """The old toggle called set_mode again, which reset the surface to 1080x720."""
    real_flip = pygame.display.flip
    counter = {"n": 0}

    def flip():
        counter["n"] += 1
        if counter["n"] == 4:
            pygame.event.post(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSLASH)
            )
        if counter["n"] >= 12:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    game.game_loop()

    assert len(captured_mode) == 1


def test_the_logical_surface_never_changes_size(monkeypatch):
    sizes = set()
    real_flip = pygame.display.flip
    counter = {"n": 0}

    def flip():
        counter["n"] += 1
        sizes.add(pygame.display.get_surface().get_size())
        if counter["n"] == 4:
            pygame.event.post(pygame.event.Event(pygame.WINDOWRESIZED, x=1600, y=900))
        if counter["n"] >= 12:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    game.game_loop()

    assert sizes == {config.WINDOW}


def test_the_legacy_resize_event_is_not_used():
    import pathlib

    source = pathlib.Path("shooter/game.py").read_text()

    assert "VIDEORESIZE" not in source
    assert "WINDOWRESIZED" in source
