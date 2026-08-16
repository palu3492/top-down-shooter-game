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
CASH_MIN = 0
CASH_MAX = 10_000
CASH_ROW_HEIGHT = 34
FORM_GUTTER = 4
HALF_SPAN = 6
HINT = "twelve columns; every rectangle below is measured in them"
# Cheats are keys pressed during a game, so they cannot live on this form --
# but this is where someone comes looking for them.
CHEATS = "in a game:  [0] every weapon, loaded, on [1]-[5]"


class DevScreen(FormScreen):
    title = "DEV"

    def __init__(self, window, manager, settings=None, cash=None):
        super().__init__(window, manager, settings)
        self.cash = cash

    def open(self):
        grid = Grid(pygame.Rect((0, 0), self.window), padding=PADDING)
        self.add(widgets.title(grid.row(TITLE_HEIGHT).rest(), self.title, self.manager))
        # Both on one row: a second one costs 26 pixels the shortest window
        # this screen claims to support does not have.
        hints = grid.row(HINT_HEIGHT)
        self.hint = self.add(widgets.hint(hints.cell(HALF_SPAN), HINT, self.manager))
        self.cheats = self.add(widgets.hint(hints.rest(), CHEATS, self.manager))
        self._build_ruler(grid)

        body = grid.row(grid.free_height - BUTTON_HEIGHT - grid.gutter)
        body_grid = Grid(body.rest())
        self._build_cash(body_grid)
        forms = body_grid.rest().area
        columns = Grid(forms).row(forms.height, gutter=0)
        self.build_form(
            Grid(columns.cell(HALF_SPAN), gutter=FORM_GUTTER),
            LIVE_TUNABLES,
            title="LIVE",
        )
        self.build_form(
            Grid(columns.rest(), gutter=FORM_GUTTER),
            SPAWN_TUNABLES,
            title="NEW SPAWNS",
        )

        buttons = grid.row(BUTTON_HEIGHT)
        buttons.skip(2)
        self.save_button = self.add(
            widgets.button(buttons.cell(4), "SAVE", self.manager)
        )
        self.back = self.add(widgets.button(buttons.cell(4), "BACK", self.manager))

    def _build_cash(self, grid):
        row = grid.row(CASH_ROW_HEIGHT)
        current = self.cash.cash_amount if self.cash is not None else 0
        self.cash_caption = self.add(
            widgets.caption(row.cell(3), f"coins  current: {current}", self.manager)
        )
        self.cash_slider = self.add(
            widgets.slider(
                row.cell(7),
                self.manager,
                min(CASH_MAX, max(CASH_MIN, current)),
                (CASH_MIN, CASH_MAX),
                increment=100,
            )
        )
        self.cash_readout = self.add(
            widgets.caption(row.rest(), str(current), self.manager)
        )

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
        if (
            event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED
            and event.ui_element is self.cash_slider
        ):
            amount = int(self.cash_slider.get_current_value())
            if self.cash is not None:
                self.cash.cash_amount = amount
            self.cash_caption.set_text(f"coins  current: {amount}")
            self.cash_readout.set_text(str(amount))
            return None
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element is self.back:
                return BACK
            if event.ui_element is self.save_button:
                self.save()
        return None
