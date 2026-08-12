"""The splash and the main menu -- what the game is before a game starts.

Both are painted on `menu_1.jpg`, which has been sitting unused in the assets
folder since 2019. It was drawn for a menu that never got written: a sunset, a
shooter, a zombie, and a deliberately blank signpost waiting for a title.

The art is a 2:1 banner and the window is 3:2, so it is scaled to the width and
sat on the ground line, with the sky above it continued in the colour sampled
from its own top edge. Cropping to fill would cut the shooter off the left.
"""

from functools import cache

import pygame
import pygame_gui

from shooter import config
from shooter.assets import load_image
from shooter.scenes import Scene
from shooter.ui import menu, widgets
from shooter.ui.anchor import CENTRE, TOP, place

ART = "Backgrounds/menu_1.jpg"
GAME_TITLE = "TOP DOWN SHOOTER"

MENU, START = "MENU", "START"

FADE_IN = 0.7
HOLD = 1.3
SKIPPABLE_AFTER = 0.15

TITLE_SIZE = (760, 70)
TITLE_INSET = (0, 232)
SUBTITLE_INSET = (0, 300)
SUBTITLE = "press any key"


@cache
def backdrop(size):
    """The art at window width, resting on the bottom, sky filled above it.

    Cached: this smoothscales a 4961x2481 image, which is a fifth of a second
    and unthinkable once a frame.
    """
    window = size
    art = load_image(ART)
    width = window[0]
    height = round(art.get_height() * width / art.get_width())
    scaled = pygame.transform.smoothscale(art, (width, height))

    surface = pygame.Surface(tuple(window))
    surface.fill(scaled.get_at((0, 0)))
    surface.blit(scaled, (0, window[1] - height))
    return surface


class TitleScene(Scene):
    """Shared backdrop for everything shown before a game exists."""

    opaque = True

    def draw_backdrop(self, surface):
        surface.blit(backdrop(tuple(self.window)), (0, 0))


class SplashScene(TitleScene):
    """The title card. Fades up, holds, then hands over to the menu."""

    title = "SPLASH"

    def __init__(self, window, manager):
        super().__init__(window, manager)
        self.elapsed = 0.0

    def open(self):
        """Painted rather than built: the fade has to reach the text too, and a
        widget cannot be faded without a surface of its own."""

    @property
    def finished(self):
        return self.elapsed >= FADE_IN + HOLD

    @property
    def brightness(self):
        return min(1.0, self.elapsed / FADE_IN) if FADE_IN else 1.0

    def tick(self, seconds):
        self.elapsed += seconds
        return MENU if self.finished else None

    def handle(self, event):
        if self.elapsed < SKIPPABLE_AFTER:
            return None
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            return MENU
        return None

    def draw(self, surface, alpha=0.0):
        self.draw_backdrop(surface)
        _title_text(surface, self.window, GAME_TITLE, TITLE_INSET, 64)
        _title_text(surface, self.window, SUBTITLE, SUBTITLE_INSET, 26)

        faded = 255 - int(255 * self.brightness)
        if faded:
            veil = pygame.Surface(tuple(self.window))
            veil.set_alpha(faded)
            surface.blit(veil, (0, 0))


class MainMenuScene(TitleScene):
    """Where a game is started from, and where ending one returns to."""

    title = GAME_TITLE

    BUTTON_SIZE = (300, 56)
    BUTTON_GAP = 16
    FIRST_BUTTON_TOP = 330

    @property
    def entries(self):
        listed = [("START GAME", START), ("SETTINGS", menu.SETTINGS)]
        if config.DEV_TOOLS:
            listed.append(("DEV", menu.DEV))
        listed.append(("QUIT", menu.QUIT))
        return tuple(listed)

    def open(self):
        self.actions = {}
        for index, (label, action) in enumerate(self.entries):
            rect = pygame.Rect(0, 0, *self.BUTTON_SIZE)
            rect.centerx = self.window[0] // 2
            rect.y = self.FIRST_BUTTON_TOP + index * (
                self.BUTTON_SIZE[1] + self.BUTTON_GAP
            )
            self.actions[self.add(widgets.button(rect, label, self.manager))] = action

    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            return self.actions.get(event.ui_element)
        return None

    def draw(self, surface, alpha=0.0):
        self.draw_backdrop(surface)
        _title_text(surface, self.window, GAME_TITLE, TITLE_INSET, 64)


def _title_text(surface, window, message, inset, size):
    """Drawn rather than laid out as a widget: it sits on the signpost, which
    is part of the picture rather than part of the interface."""
    font = pygame.font.Font(None, size)
    shadow = font.render(message, True, (0, 0, 0))
    text = font.render(message, True, (232, 226, 205))
    rect = place(text.get_size(), window, CENTRE, TOP, inset)
    surface.blit(shadow, (rect.left + 2, rect.top + 2))
    surface.blit(text, rect.topleft)
