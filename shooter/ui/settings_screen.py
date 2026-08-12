"""The settings the player owns.

Display only. The zombie tunables are a debug affordance rather than a
difficulty feature, so they live on the dev screen where "new spawns" reads as
a caveat instead of a broken control.
"""

import pygame
import pygame_gui

from shooter.ui import form, widgets
from shooter.ui.form import FormScreen
from shooter.ui.layout import Grid
from shooter.ui.menu import BACK

DISPLAY = ("WINDOW", "VSYNC", "FPS")

PADDING = 40
TITLE_HEIGHT = 52
HINT_HEIGHT = 26
BUTTON_HEIGHT = 54
FORM_SPAN = 10


class SettingsScreen(FormScreen):
    title = "SETTINGS"

    def open(self):
        grid = Grid(pygame.Rect((0, 0), self.window), padding=PADDING)
        self.add(widgets.title(grid.row(TITLE_HEIGHT).rest(), self.title, self.manager))
        self.hint = self.add(
            widgets.hint(grid.row(HINT_HEIGHT).rest(), self.UNSAVED, self.manager)
        )

        body = grid.row(form.height_for(DISPLAY))
        self.build_form(Grid(body.cell(FORM_SPAN)), DISPLAY)

        grid.skip(grid.free_height - BUTTON_HEIGHT)
        buttons = grid.row(BUTTON_HEIGHT)
        buttons.skip(2)
        self.save_button = self.add(
            widgets.button(buttons.cell(4), "SAVE", self.manager)
        )
        self.back = self.add(widgets.button(buttons.cell(4), "BACK", self.manager))

    def handle(self, event):
        if self.handle_dialog(event):
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return BACK
        if self.form.handle(event):
            self.announce(self.UNSAVED)
            return None
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element is self.back:
                return BACK
            if event.ui_element is self.save_button:
                self.save()
        return None
