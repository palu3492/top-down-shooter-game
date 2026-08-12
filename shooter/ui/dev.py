"""The dev screen: every widget, arranged by the grid, with nothing at stake.

This is where theming and spacing get argued out. It is reachable only while
`config.DEV_TOOLS` is on, and none of the controls here are wired to anything --
AT23 gives them a settings store to write to.
"""

import pygame
import pygame_gui

from shooter.ui import widgets
from shooter.ui.layout import Grid
from shooter.ui.menu import BACK
from shooter.ui.screens import Screen

PADDING = 40
TITLE_HEIGHT = 52
HINT_HEIGHT = 26
RULER_HEIGHT = 16
SPAN_HEIGHT = 32
SETTING_HEIGHT = 34
CAPTION_HEIGHT = 24
SELECTOR_HEIGHT = 150
BUTTON_HEIGHT = 54

HINT = "twelve columns, every rectangle below measured in them"
SPAN_DEMOS = ((6, 3, 3), (4, 4, 4), (2, 2, 2, 2, 2, 2))
NESTED_SPLITS = (2, 4)
NESTED_PADDING = 6
RESOLUTIONS = ("1280 x 720", "1600 x 900", "1920 x 1080", "2560 x 1440")
DIFFICULTIES = ("EASY", "NORMAL", "HARD")
ZOMBIE_SPEED_RANGE = (60, 900)


class DevScreen(Screen):
    title = "DEV"

    def open(self):
        grid = Grid(pygame.Rect((0, 0), self.window), padding=PADDING)

        self.add(widgets.title(grid.row(TITLE_HEIGHT).rest(), self.title, self.manager))
        self.add(widgets.hint(grid.row(HINT_HEIGHT).rest(), HINT, self.manager))

        self._build_ruler(grid)
        for spans in SPAN_DEMOS:
            self._build_span_demo(grid, spans)

        body = grid.row(grid.free_height - BUTTON_HEIGHT - grid.gutter)
        self._build_controls(body.cell(7))
        self._build_selector(body.rest())

        self.back = self.add(
            widgets.button(grid.rest().skip(4).cell(4), "BACK", self.manager)
        )

    def _build_ruler(self, grid):
        row = grid.row(RULER_HEIGHT)
        for _ in range(row.columns):
            self.add(widgets.panel(row.cell(1), self.manager))

    def _build_span_demo(self, grid, spans):
        row = grid.row(SPAN_HEIGHT)
        for span in spans:
            self.add(widgets.caption(row.cell(span), f"span {span}", self.manager))

    def _build_controls(self, area):
        grid = Grid(area)
        self._add_caption(grid, "CONTROLS")

        row = self._setting_row(grid, "vsync")
        self.add(widgets.checkbox(row.rest(), "", self.manager, checked=True))

        row = self._setting_row(grid, "difficulty")
        self.add(widgets.dropdown(row.rest(), DIFFICULTIES, self.manager))

        row = self._setting_row(grid, "zombie speed")
        self.add(widgets.slider(row.rest(), self.manager, 360, ZOMBIE_SPEED_RANGE))

    def _build_selector(self, area):
        grid = Grid(area)
        self._add_caption(grid, "RESOLUTION")
        self.add(
            widgets.selector(
                grid.row(SELECTOR_HEIGHT).rest(), RESOLUTIONS, self.manager
            )
        )
        self._add_caption(grid, "NESTED GRID")
        self._build_nested_demo(grid.rest().rest())

    def _build_nested_demo(self, area):
        halves = Grid(area, columns=len(NESTED_SPLITS)).rest()
        for columns in NESTED_SPLITS:
            row = Grid(halves.cell(1), columns=columns, padding=NESTED_PADDING).rest()
            for _ in range(columns):
                self.add(widgets.panel(row.cell(1), self.manager))

    def _add_caption(self, grid, text):
        return self.add(
            widgets.caption(grid.row(CAPTION_HEIGHT).rest(), text, self.manager)
        )

    def _setting_row(self, grid, label):
        row = grid.row(SETTING_HEIGHT)
        self.add(widgets.caption(row.cell(7), label, self.manager))
        return row

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return BACK
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element is self.back:
            return BACK
        return None
