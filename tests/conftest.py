import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

WINDOW = (1080, 720)


@pytest.fixture(scope="session", autouse=True)
def display():
    pygame.init()
    surface = pygame.display.set_mode(WINDOW)
    yield surface
    pygame.quit()


class FakeCash:
    def __init__(self):
        self.received = []

    def increase_cash(self, amount):
        self.received.append(amount)
