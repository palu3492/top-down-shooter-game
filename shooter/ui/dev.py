"""The dev screen: the tunables, and a ruler to check the grid against.

These are a debug affordance, not a difficulty feature -- that is why they are
here rather than on the settings screen. Each row says when its change lands, so
"new spawns" reads as a caveat rather than a control that does nothing.

`DEV_TOOLS` is deliberately absent. Turning it off from here would remove the
only way back to this screen.
"""

import pygame
import pygame_gui

from shooter.ui import widgets
from shooter.ui.form import FormScreen
from shooter.ui.layout import Grid
from shooter.ui.menu import BACK

LIVE_TUNABLES = (
    "PLAYER_SPEED",
    "PLAYER_HEALTH",
    "PLAYER_REGEN",
    "ZOMBIE_DAMAGE",
    "KILL_REWARD",
    "WAVE_BASE",
    "WAVE_INTERVAL_SECONDS",
)
SPAWN_TUNABLES = (
    "ZOMBIE_SPEED",
    "SPAWN_LEAD_SECONDS",
    "ZOMBIE_HEALTH",
    "RELOAD_SECONDS",
    "STARTING_GRENADES",
    "STARTING_STUN_GRENADES",
)

PADDING = 40
TITLE_HEIGHT = 52
HINT_HEIGHT = 26
RULER_HEIGHT = 14
BUTTON_HEIGHT = 54
HALF_SPAN = 6
HINT = "twelve columns; every rectangle below is measured in them"


class DevScreen(FormScreen):
    title = "DEV"

    def open(self):
        grid = Grid(pygame.Rect((0, 0), self.window), padding=PADDING)
        self.add(widgets.title(grid.row(TITLE_HEIGHT).rest(), self.title, self.manager))
        self.hint = self.add(
            widgets.hint(grid.row(HINT_HEIGHT).rest(), HINT, self.manager)
        )
        self._build_ruler(grid)

        body = grid.row(grid.free_height - BUTTON_HEIGHT - grid.gutter)
        self.build_form(Grid(body.cell(HALF_SPAN)), LIVE_TUNABLES, title="LIVE")
        self.build_form(Grid(body.rest()), SPAWN_TUNABLES, title="NEW SPAWNS")

        buttons = grid.row(BUTTON_HEIGHT)
        buttons.skip(2)
        self.save_button = self.add(
            widgets.button(buttons.cell(4), "SAVE", self.manager)
        )
        self.back = self.add(widgets.button(buttons.cell(4), "BACK", self.manager))

    def _build_ruler(self, grid):
        row = grid.row(RULER_HEIGHT)
        for _ in range(row.columns):
            self.add(widgets.panel(row.cell(1), self.manager))

    def handle(self, event):
        if self.handle_dialog(event):
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return BACK
        if self.form.handle(event):
            self.announce(HINT)
            return None
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element is self.back:
                return BACK
            if event.ui_element is self.save_button:
                self.save()
        return None
