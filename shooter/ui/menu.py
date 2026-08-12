"""The pause menu and the scenes it opens."""

import pygame
import pygame_gui

from shooter import config
from shooter.ui import widgets
from shooter.scenes import Scene

RESUME, SETTINGS, DEV, QUIT, BACK = "RESUME", "SETTINGS", "DEV", "QUIT", "BACK"
END_GAME = "END_GAME"

BUTTON_SIZE = (280, 54)
BUTTON_GAP = 14


class MenuScreen(Scene):
    """A screen that is a vertical column of buttons."""

    entries = ()

    def open(self):
        width, height = self.window
        column_height = len(self.entries) * (BUTTON_SIZE[1] + BUTTON_GAP)
        top = (height - column_height) // 2

        self.title_rect = pygame.Rect(0, top - 96, width, 52)
        self.add(widgets.title(self.title_rect, self.title, self.manager))

        self.actions = {}
        for index, (label, action) in enumerate(self.entries):
            rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            rect.centerx = width // 2
            rect.y = top + index * (BUTTON_SIZE[1] + BUTTON_GAP)
            self.actions[self.add(widgets.button(rect, label, self.manager))] = action

    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            return self.actions.get(event.ui_element)
        return None


class PauseScreen(MenuScreen):
    title = "PAUSED"
    opaque = False

    @property
    def entries(self):
        listed = [("RESUME", RESUME), ("SETTINGS", SETTINGS)]
        if config.DEV_TOOLS:
            listed.append(("DEV", DEV))
        listed.append(("END GAME", END_GAME))
        listed.append(("QUIT", QUIT))
        return tuple(listed)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return RESUME
        return super().handle(event)
