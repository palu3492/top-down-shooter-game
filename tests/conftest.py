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


@pytest.fixture(scope="session", autouse=True)
def display(window):
    pygame.init()
    surface = pygame.display.set_mode(window)
    yield surface
    pygame.quit()


@pytest.fixture
def make_cash():
    return RecordingCash


@pytest.fixture
def cash(make_cash):
    return make_cash()
