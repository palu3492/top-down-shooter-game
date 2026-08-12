"""The pause menu and the screens it opens."""

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel

from shooter import config
from shooter.ui.screens import Screen

RESUME, SETTINGS, DEV, QUIT, BACK = "RESUME", "SETTINGS", "DEV", "QUIT", "BACK"

BUTTON_SIZE = (280, 54)
BUTTON_GAP = 14


class MenuScreen(Screen):
    """A screen that is a vertical column of buttons."""

    entries = ()

    def open(self):
        width, height = self.window
        column_height = len(self.entries) * (BUTTON_SIZE[1] + BUTTON_GAP)
        top = (height - column_height) // 2

        self.title_rect = pygame.Rect(0, top - 96, width, 52)
        self.elements.append(
            UILabel(
                self.title_rect, self.title, self.manager, object_id="#screen_title"
            )
        )
        self.actions = {}
        for index, (label, action) in enumerate(self.entries):
            rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            rect.centerx = width // 2
            rect.y = top + index * (BUTTON_SIZE[1] + BUTTON_GAP)
            button = UIButton(rect, label, self.manager)
            self.elements.append(button)
            self.actions[button] = action

    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            return self.actions.get(event.ui_element)
        return None


class PauseScreen(MenuScreen):
    title = "PAUSED"
    covers_game = False

    @property
    def entries(self):
        listed = [("RESUME", RESUME), ("SETTINGS", SETTINGS)]
        if config.DEV_TOOLS:
            listed.append(("DEV", DEV))
        listed.append(("QUIT", QUIT))
        return tuple(listed)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return RESUME
        return super().handle(event)


class StubScreen(MenuScreen):
    """A placeholder full screen. AT22 and AT24 replace these with real ones."""

    entries = (("BACK", BACK),)

    def open(self):
        super().open()
        hint_rect = pygame.Rect(0, self.title_rect.bottom + 6, self.window[0], 26)
        self.elements.append(
            UILabel(
                hint_rect, "nothing here yet", self.manager, object_id="#screen_hint"
            )
        )

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return BACK
        return super().handle(event)


class SettingsScreen(StubScreen):
    title = "SETTINGS"


class DevScreen(StubScreen):
    title = "DEV"
