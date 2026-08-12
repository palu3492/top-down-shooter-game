"""Screens layered over the game, and the stack that owns them.

A stack rather than a single state name: pause opens settings, settings closes
back to pause. That is nesting, and a flat name has nowhere to record what
closing returns to.
"""

from pathlib import Path

import pygame
import pygame_gui

THEME = Path(__file__).with_name("theme.json")

VEIL = (0, 0, 0, 170)
BACKDROP = (22, 26, 17)


def build_manager(window):
    return pygame_gui.UIManager(window, str(THEME))


class Screen:
    """One layer of interface.

    `covers_game` decides whether the frame underneath still shows: the pause
    screen veils it, a full screen replaces it.
    """

    title = ""
    covers_game = True

    def __init__(self, window, manager):
        self.window = window
        self.manager = manager
        self.elements = []

    def open(self):
        raise NotImplementedError

    def close(self):
        for element in self.elements:
            element.kill()
        self.elements.clear()

    def handle(self, event):
        """Return an action name, or None to stay put."""
        return None

    def draw_backdrop(self, surface, frozen_frame):
        if self.covers_game:
            surface.fill(BACKDROP)
            return
        surface.blit(frozen_frame, (0, 0))
        veil = pygame.Surface(self.window, pygame.SRCALPHA)
        veil.fill(VEIL)
        surface.blit(veil, (0, 0))


class ScreenStack:
    """The screens currently open, innermost last."""

    def __init__(self, window):
        self.window = window
        self.manager = build_manager(window)
        self._screens = []

    def __bool__(self):
        return bool(self._screens)

    def __len__(self):
        return len(self._screens)

    @property
    def top(self):
        return self._screens[-1] if self._screens else None

    def push(self, screen):
        if self._screens:
            self._screens[-1].close()
        self._screens.append(screen)
        screen.open()
        self._sync_pointer()

    def pop(self):
        if not self._screens:
            return
        self._screens.pop().close()
        if self._screens:
            self._screens[-1].open()
        self._sync_pointer()

    def _sync_pointer(self):
        """Gameplay hides the system pointer and draws its own crosshair, so a
        menu has to ask for the real one back before anything is clickable."""
        pygame.mouse.set_visible(bool(self._screens))

    def clear(self):
        while self._screens:
            self.pop()

    def handle(self, event):
        self.manager.process_events(event)
        return self.top.handle(event) if self._screens else None

    def draw(self, surface, frozen_frame, dt):
        if not self._screens:
            return
        self.top.draw_backdrop(surface, frozen_frame)
        self.manager.update(dt)
        self.manager.draw_ui(surface)
