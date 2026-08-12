import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest


class RecordingCash:
    def __init__(self):
        self.received = []

    def increase_cash(self, amount):
        self.received.append(amount)


@pytest.fixture(scope="session")
def window():
    return (1080, 720)


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
def cash(make_cash):
    return make_cash()
