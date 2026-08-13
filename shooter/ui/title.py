"""The splash and the main menu -- what the game is before a game starts.

Both are painted on `menu_pixel.png`, baked by `tools/make_menu_art.py` from
`menu_1.jpg`, which had been sitting unused in the assets folder since 2019: a
sunset, a shooter, a zombie, and a deliberately blank signpost waiting for a
title.

It is stored at 135x90 and scaled with nearest-neighbour, which is what keeps
the pixels square instead of smearing them. An eighth of the 1080x720 render
surface exactly, so the default resolution gets whole blocks.

Reducing the palette is what makes this read as pixel art rather than as a
photograph shown too small -- simply pixelating the painting leaves soft blocks
that look like a low-resolution image, because they are one.
"""

from functools import cache

import pygame
import pygame_gui

from shooter import config
from shooter.assets import load_image
from shooter.scenes import Scene
from shooter.ui import menu, widgets
from shooter.ui.anchor import CENTRE, TOP, place
from shooter.ui.sky import Sky

ART = "Backgrounds/menu_pixel.png"
GAME_TITLE = "TOP DOWN SHOOTER"

MENU, START, CONTINUE = "MENU", "START", "CONTINUE"

FADE_IN = 0.7
HOLD = 1.3
SKIPPABLE_AFTER = 0.15

TITLE_SIZE = (760, 70)
TITLE_INSET = (0, 232)
SUBTITLE_INSET = (0, 300)
SUBTITLE = "press any key"


@cache
def backdrop(size):
    """The art blown up to the window with square pixels, as painted.

    Kept for the palette the art was baked with. Anything on screen goes
    through `Sky`, which is the same picture recoloured over the cycle.
    """
    return pygame.transform.scale(load_image(ART), tuple(size))


class TitleScene(Scene):
    """Shared backdrop for everything shown before a game exists.

    The sky drifts from dusk through night to dawn on a slow cycle, so the menu
    is not a still image while it is being read.
    """

    opaque = True

    def __init__(self, window, manager):
        super().__init__(window, manager)
        self.elapsed = 0.0
        self.sky = Sky(tuple(window))

    def tick(self, seconds):
        self.elapsed += seconds
        return None

    def draw_backdrop(self, surface):
        surface.blit(self.sky.at(self.elapsed), (0, 0))


class SplashScene(TitleScene):
    """The title card. Fades up, holds, then hands over to the menu."""

    title = "SPLASH"

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
        super().tick(seconds)
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
    FIRST_BUTTON_TOP = 306

    def __init__(self, window, manager, progress=None):
        super().__init__(window, manager)
        self.progress = progress

    @property
    def reached(self):
        return self.progress.reached if self.progress else None

    @property
    def entries(self):
        """CONTINUE only appears once there is something to come back to."""
        listed = []
        if self.progress is not None and self.progress.started:
            listed.append((f"CONTINUE  LEVEL {self.reached}", CONTINUE))
            listed.append(("NEW GAME", START))
        else:
            listed.append(("START GAME", START))
        listed.append(("SETTINGS", menu.SETTINGS))
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


PIXEL_SCALE = 4
INK = (240, 232, 200)
SHADOW = (20, 16, 12)


@cache
def pixel_text(message, size, colour, scale=PIXEL_SCALE):
    """Rendered small with antialiasing off, then blown up square.

    A bitmap look out of a vector font, so there is no pixel font to ship and
    the letters keep their blocks at any resolution.
    """
    small = pygame.font.Font(None, max(6, size // scale)).render(message, False, colour)
    return pygame.transform.scale(
        small, (small.get_width() * scale, small.get_height() * scale)
    )


def _title_text(surface, window, message, inset, size):
    """Drawn rather than laid out as a widget: it belongs to the picture."""
    text = pixel_text(message, size, INK)
    rect = place(text.get_size(), window, CENTRE, TOP, inset)
    surface.blit(pixel_text(message, size, SHADOW), (rect.left + 4, rect.top + 4))
    surface.blit(text, rect.topleft)
